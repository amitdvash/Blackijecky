"""
src/server.py

Overview
--------
The central server component of Blackijecky.

This module is responsible for:
- Broadcasting its presence via UDP (Service Discovery).
- Accepting incoming TCP connections from multi-clients.
- Managing the game flow (dealing cards, processing player moves, dealer logic).
- Enforcing game rules and determining winners.

How it fits in the system
-------------------------
- The "Host" of the distributed system.
- Uses `protocol.py` to communicate.
- Uses `game_logic.py` to manage state (Deck, Hand).
- Listen on a random/OS-assigned TCP port and advertises this port via UDP port 13122.

How to run:
-----------
python -m src.server
(or)
python src/server.py

Notes:
------
- Threading: Creates 1 thread per connected client (`handle_client`).
- Threading: Creates 1 background thread for UDP offers (`broadcast_offers`).
- Networking: Attempts to auto-detect the "real" LAN IP to bind correct interface.
- Concurrency: Can handle multiple games simultaneously (one thread/game per connection).
"""

import socket
import threading
import time
import struct
from src.consts import (
    CLIENT_UDP_PORT,
    BROADCAST_IP,
    OFFER_INTERVAL,
    MAGIC_COOKIE,
    MSG_TYPE_OFFER,
    RESULT_CONTINUE,
    RESULT_WIN,
    RESULT_LOSS,
    RESULT_TIE,
    PAYLOAD_DECISION_HIT,
    PAYLOAD_DECISION_STAND,
    Colors,
    SOCKET_TIMEOUT,
    SOCKET_TIMEOUT_DECISION,
)
from src.protocol import (
    pack_offer,
    unpack_request,
    pack_payload_server,
    unpack_payload_client,
    SIZE_REQUEST,
    SIZE_PAYLOAD_CLIENT,
    recv_exact,
)
from src.game_logic import Deck, Hand, Card

SERVER_NAME = "404_Loss_Not_Found_Server"


def get_local_ip():
    """
    Determines the best local IP address for LAN visibility.

    Why this exists
    ---------------
    If the server binds to 127.0.0.1, only the same machine can connect.
    For a real LAN game (multiple devices), we want the server's actual LAN IP
    (e.g., 192.168.x.x).

    How it works
    ------------
    - Creates a UDP socket and "connects" to an external address (8.8.8.8).
      No data is sent, but the OS chooses the outbound interface.
    - Reads the chosen local interface IP via getsockname().
    - Falls back to hostname resolution if needed.
    - Final fallback is 127.0.0.1.

    Returns:
        str: The IP address string to bind to (e.g., "192.168.1.5").
    """
    try:
        # Create a dummy socket to connect to an external address
        # This forces the OS to choose the interface used for internet/LAN access
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS, but port 80 or anything works
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback to standard method if internet is not available
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"


class Server:
    """
    Blackjack game server.

    Responsibilities
    ----------------
    - Initialize and manage UDP/TCP sockets.
    - Broadcast UDP Offers periodically so clients can discover the server.
    - Accept TCP connections and spawn a thread per client.
    - For each client:
      - Receive and validate the initial Request (rounds, team name).
      - Run requested number of rounds sequentially using `play_round`.
      - Handle disconnects/timeouts without crashing the server.

    Key attributes
    --------------
    - self.running (bool): Global loop flag for offer broadcasting / TCP accept loop.
    - self.local_ip (str): Server bind IP (best LAN IP if possible).
    - self.tcp_socket (socket.socket): Listening TCP socket.
    - self.tcp_port (int): OS-assigned TCP port used for client sessions.
    - self.udp_socket (socket.socket): UDP socket used to broadcast Offers.
    """

    def __init__(self):
        """
        Initializes server sockets and bind addresses.

        What it does
        ------------
        - Resolves the local IP to bind (LAN-visible if possible).
        - Creates a TCP socket and binds to (local_ip, 0) so the OS assigns an available port.
        - Stores the chosen port in self.tcp_port.
        - Creates a UDP socket configured for broadcast and binds it to the same interface.

        Notes
        -----
        - Binding TCP to port 0 avoids hardcoding ports and prevents collisions.
        - The chosen TCP port is then advertised via UDP Offers.
        """
        self.running = True
        self.local_ip = get_local_ip()

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.local_ip, 0))  # Bind to the specific interface
        self.tcp_port = self.tcp_socket.getsockname()[1]

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(
            (self.local_ip, 0)
        )  # Bind to the specific interface to force broadcast source

    def start(self):
        """
        Starts the server runtime: UDP offers + TCP accept loop.

        Flow
        ----
        - Print server IP (debug/info).
        - Start a daemon thread to broadcast UDP offers (`broadcast_offers`).
        - Start listening for TCP clients in the main thread (`listen_tcp`).

        Notes
        -----
        - UDP offer broadcast runs continuously until self.running becomes False.
        - TCP accept loop runs continuously until self.running becomes False.
        """
        print(
            f"{Colors.OKGREEN}Server started, listening on IP address {self.local_ip}{Colors.ENDC}"
        )

        # Start UDP Broadcast Thread
        broadcast_thread = threading.Thread(target=self.broadcast_offers, daemon=True)
        broadcast_thread.start()

        # Start TCP Listener
        self.listen_tcp()

    def broadcast_offers(self):
        """
        Periodically broadcasts a UDP Offer so clients can discover the server.

        What it sends
        -------------
        - A binary Offer message created by `pack_offer(self.tcp_port, SERVER_NAME)`
        - Sent to (BROADCAST_IP, CLIENT_UDP_PORT)

        Why it matters
        --------------
        Clients do not know the server IP/port ahead of time. They listen on
        CLIENT_UDP_PORT, receive an Offer, unpack it, and then connect via TCP.

        Loop behavior
        -------------
        - Runs while self.running == True
        - Sleeps OFFER_INTERVAL between broadcasts

        Notes
        -----
        - This function is typically run in a daemon thread.
        """
        packet = pack_offer(self.tcp_port, SERVER_NAME)
        # print(f"Server started, listening on IP address {self.local_ip}") # Re-print as per example flow

        while self.running:
            try:
                self.udp_socket.sendto(packet, (BROADCAST_IP, CLIENT_UDP_PORT))
                # print(f"Broadcasted offer on port {CLIENT_UDP_PORT}") # Debug
                time.sleep(OFFER_INTERVAL)
            except Exception as e:
                print(f"Error broadcasting: {e}")

    def listen_tcp(self):
        """
        Accepts TCP connections and starts a thread per client.

        What it does
        ------------
        - Puts the TCP socket into listening mode.
        - In a loop:
          - accept() a new client connection
          - spawn a dedicated thread running `handle_client(client_socket, addr)`

        Concurrency model
        -----------------
        - Each client is isolated in its own thread.
        - Multiple clients can play simultaneously.

        Notes
        -----
        - If accept() throws while shutting down, it may be logged as an error.
        """
        self.tcp_socket.listen()
        print(
            f"{Colors.OKBLUE}Listening for TCP connections on port {self.tcp_port}...{Colors.ENDC}"
        )

        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                print(f"{Colors.OKCYAN}New connection from {addr}{Colors.ENDC}")
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, addr)
                )
                client_thread.start()
            except Exception as e:
                print(f"{Colors.FAIL}Error accepting connection: {e}{Colors.ENDC}")

    def handle_client(self, client_socket: socket.socket, addr):
        """
        Handles the full lifecycle of a single client connection.

        Flow
        ----
        1) Apply a general socket timeout (SOCKET_TIMEOUT) to avoid dead connections.
        2) Receive the initial Request message (fixed size SIZE_REQUEST) using recv_exact.
        3) Unpack and validate the Request using unpack_request:
           - Extract (num_rounds, team_name)
        4) For each round:
           - Call play_round(client_socket)
           - If an error occurs (disconnect/timeout/invalid data), stop this client session.
        5) Close the socket in finally.

        Args:
            client_socket (socket.socket): The connected TCP socket for this client.
            addr (tuple): Client address tuple (ip, port).

        Notes
        -----
        - This method runs in a dedicated thread created by listen_tcp().
        - Any exception should terminate only this client session, not the whole server.
        """
        try:
            client_socket.settimeout(SOCKET_TIMEOUT)  # Timeout per client

            # 1. Receive Request
            try:
                data = recv_exact(client_socket, SIZE_REQUEST)
            except Exception:
                print(f"Client {addr} disconnected before request.")
                return

            request = unpack_request(data)
            if not request:
                print(f"Invalid request from {addr}")
                return

            num_rounds, team_name = request
            print(
                f"{Colors.OKCYAN}Client '{team_name}' connected. Requested {num_rounds} rounds.{Colors.ENDC}"
            )

            # 2. Game Loop
            for round_num in range(1, num_rounds + 1):
                print(
                    f"{Colors.HEADER}--- Starting Round {round_num} for {team_name} ---{Colors.ENDC}"
                )
                try:
                    self.play_round(client_socket)
                    print(
                        f"{Colors.HEADER}--- Round {round_num} completed for {team_name} ---{Colors.ENDC}"
                    )
                except Exception as e:
                    print(
                        f"{Colors.FAIL}Error during round {round_num} with {team_name}: {e}{Colors.ENDC}"
                    )
                    break

            print(
                f"{Colors.OKBLUE}Finished all rounds for {team_name}. Closing connection.\n{Colors.ENDC}"
            )

        except socket.timeout:
            print(f"{Colors.FAIL}Client {addr} timed out (inactive).{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}Error handling client {addr}: {e}{Colors.ENDC}")
        finally:
            client_socket.close()

    def play_round(self, client_socket: socket.socket):
        """
        Runs a single Blackjack round with the connected client.

        Round protocol (high level)
        ---------------------------
        Server -> Client (initial deal):
        - Send Player card #1  (RESULT_CONTINUE)
        - Send Player card #2  (RESULT_CONTINUE)
        - Send Dealer upcard   (RESULT_CONTINUE)
        - Keep dealer hole card hidden (not sent yet)

        Player decision phase:
        - Wait for client payload messages: HIT or STAND
        - For HIT:
          - Deal a new player card, send it to client
          - If player busts (>21): send that card with RESULT_LOSS and end round
        - For STAND:
          - Move to dealer phase

        Dealer phase:
        - Reveal dealer hole card to client
        - Dealer draws until dealer value >= 17
        - If dealer busts: send bust card with RESULT_WIN and end round

        End of round:
        - Compare final hand values and send RESULT_WIN / RESULT_LOSS / RESULT_TIE
          using send_result() (no card attached).

        Args:
            client_socket (socket.socket): The client's TCP socket.

        """
        deck = Deck()
        player_hand = Hand()
        dealer_hand = Hand()

        # --- Initial Deal ---
        # Player Card 1
        card = deck.deal_card()
        player_hand.add_card(card)
        self.send_card(client_socket, card, RESULT_CONTINUE)

        # Player Card 2
        card = deck.deal_card()
        player_hand.add_card(card)
        self.send_card(client_socket, card, RESULT_CONTINUE)

        # Dealer Card 1 (Visible)
        card = deck.deal_card()
        dealer_hand.add_card(card)
        self.send_card(client_socket, card, RESULT_CONTINUE)

        # Dealer Card 2 (Hidden)
        hidden_card = deck.deal_card()
        dealer_hand.add_card(hidden_card)

        # Player Turn
        player_busted = False
        while True:
            # Wait for decision with extended timeout for manual players
            client_socket.settimeout(SOCKET_TIMEOUT_DECISION)
            try:
                data = recv_exact(client_socket, SIZE_PAYLOAD_CLIENT)
            except socket.timeout:
                print(f"{Colors.FAIL}Timeout waiting for player decision.{Colors.ENDC}")
                raise Exception("Player timed out while thinking.")
            except Exception:
                raise Exception("Client disconnected during game")

            # Reset to normal timeout after receiving decision
            client_socket.settimeout(SOCKET_TIMEOUT)

            decision = unpack_payload_client(data)

            if decision == PAYLOAD_DECISION_HIT:
                new_card = deck.deal_card()
                player_hand.add_card(new_card)

                if player_hand.calculate_value() > 21:
                    # Player Busts
                    self.send_card(client_socket, new_card, RESULT_LOSS)
                    player_busted = True
                    break
                else:
                    # Continue
                    self.send_card(client_socket, new_card, RESULT_CONTINUE)

            elif decision == PAYLOAD_DECISION_STAND:
                break
            else:
                print(f"Unknown decision: {decision}")
                break

        if player_busted:
            return  # Round over, Dealer wins

        # --- Dealer Turn ---
        # Reveal hidden card
        self.send_card(client_socket, hidden_card, RESULT_CONTINUE)

        while dealer_hand.calculate_value() < 17:
            new_card = deck.deal_card()
            dealer_hand.add_card(new_card)

            if dealer_hand.calculate_value() > 21:
                # Dealer Busts -> Player Wins
                self.send_card(client_socket, new_card, RESULT_WIN)
                return  # Round over
            else:
                self.send_card(client_socket, new_card, RESULT_CONTINUE)

        # --- Determine Winner ---
        p_val = player_hand.calculate_value()
        d_val = dealer_hand.calculate_value()

        if p_val > d_val:
            result = RESULT_WIN
        elif d_val > p_val:
            result = RESULT_LOSS
        else:
            result = RESULT_TIE

        # Send final result (with empty card)
        self.send_result(client_socket, result)

    def send_card(self, sock, card, result):
        """
        Sends one server-to-client payload frame containing a card + status.

        Purpose
        -------
        Encapsulates the low-level protocol step of:
        - Packing (result, rank, suit) into the binary server payload format
        - Sending it reliably over TCP using sendall()

        Args:
            sock (socket.socket): TCP socket to the client.
            card (Card): The card being revealed to the client (rank + suit).
            result (int): Current status flag:
                - RESULT_CONTINUE while the round is ongoing
                - RESULT_WIN / RESULT_LOSS if a bust ends the round immediately

        Notes
        -----
        - sendall() is used to ensure the full payload is transmitted.
        """
        packet = pack_payload_server(result, card.rank, card.suit)
        sock.sendall(packet)

    def send_result(self, sock, result):
        """
        Sends the final round result without attaching a card.

        When used
        ---------
        - At the end of a round after comparing hands (win/loss/tie).
        - The protocol represents "no card" as rank=0, suit=0.

        Args:
            sock (socket.socket): TCP socket to the client.
            result (int): Final result code (RESULT_WIN / RESULT_LOSS / RESULT_TIE).
        """
        packet = pack_payload_server(result, 0, 0)  # Rank 0, Suit 0
        sock.sendall(packet)


if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer stopping...")
