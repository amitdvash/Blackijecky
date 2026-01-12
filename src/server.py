"""
Server application for Blackijecky.
Handles UDP broadcasting and TCP connections.
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
    SOCKET_TIMEOUT_DECISION
)
from src.protocol import (
    pack_offer, 
    unpack_request, 
    pack_payload_server, 
    unpack_payload_client,
    SIZE_REQUEST,
    SIZE_PAYLOAD_CLIENT,
    recv_exact
)
from src.game_logic import Deck, Hand, Card

SERVER_NAME = "404_Loss_Not_Found_Server"

def get_local_ip():
    """
    Retrieves the local IP address associated with the default gateway.
    This helps in selecting the correct interface (e.g., Wi-Fi) instead of WSL or loopback.
    """
    try:
        # Create a dummy socket to connect to an external address
        # This forces the OS to choose the interface used for internet/LAN access
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))  # Google DNS, but port 80 or anything works
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback to standard method if internet is not available
        try:
             return socket.gethostbyname(socket.gethostname())
        except:
             return '127.0.0.1'

class Server:
    def __init__(self):
        """
        Initializes the Server.
        Sets up TCP and UDP sockets and retrieves the local IP address.
        """
        self.running = True
        self.local_ip = get_local_ip()

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.local_ip, 0))  # Bind to the specific interface
        self.tcp_port = self.tcp_socket.getsockname()[1]

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind((self.local_ip, 0)) # Bind to the specific interface to force broadcast source

    def start(self):
        """
        Starts the server: UDP broadcast and TCP listener.
        Runs the broadcast loop in a separate thread and listens for TCP connections in the main thread.
        """
        print(f"{Colors.OKGREEN}Server started, listening on IP address {self.local_ip}{Colors.ENDC}")
        
        # Start UDP Broadcast Thread
        broadcast_thread = threading.Thread(target=self.broadcast_offers, daemon=True)
        broadcast_thread.start()
        
        # Start TCP Listener
        self.listen_tcp()

    def broadcast_offers(self):
        """
        Sends UDP Offer packets every second.
        Runs in a loop until self.running is False.
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
        Listens for incoming TCP connections.
        Accepts connections and spawns a new thread for each client.
        """
        self.tcp_socket.listen()
        print(f"{Colors.OKBLUE}Listening for TCP connections on port {self.tcp_port}...{Colors.ENDC}")
        
        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                print(f"{Colors.OKCYAN}New connection from {addr}{Colors.ENDC}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.start()
            except Exception as e:
                print(f"{Colors.FAIL}Error accepting connection: {e}{Colors.ENDC}")

    def handle_client(self, client_socket: socket.socket, addr):
        """
        Handles a single client connection.
        Receives the request, and manages the game loop for the requested number of rounds.

        Args:
            client_socket (socket.socket): The client's TCP socket.
            addr (tuple): The client's address (IP, port).
        """
        try:
            client_socket.settimeout(SOCKET_TIMEOUT) # Timeout per client
            
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
            print(f"{Colors.OKCYAN}Client '{team_name}' connected. Requested {num_rounds} rounds.{Colors.ENDC}")

            # 2. Game Loop
            for round_num in range(1, num_rounds + 1):
                print(f"{Colors.HEADER}--- Starting Round {round_num} for {team_name} ---{Colors.ENDC}")
                try:
                    self.play_round(client_socket)
                    print(f"{Colors.HEADER}--- Round {round_num} completed for {team_name} ---{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error during round {round_num} with {team_name}: {e}{Colors.ENDC}")
                    break
            
            print(f"{Colors.OKBLUE}Finished all rounds for {team_name}. Closing connection.\n{Colors.ENDC}")

        except socket.timeout:
            print(f"{Colors.FAIL}Client {addr} timed out (inactive).{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}Error handling client {addr}: {e}{Colors.ENDC}")
        finally:
            client_socket.close()

    def play_round(self, client_socket: socket.socket):
        """
        Executes a single round of Blackjack.
        Deals cards, handles player turns, dealer turns, and determines the winner.

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
            return # Round over, Dealer wins

        # --- Dealer Turn ---
        # Reveal hidden card
        self.send_card(client_socket, hidden_card, RESULT_CONTINUE)
        
        while dealer_hand.calculate_value() < 17:
            new_card = deck.deal_card()
            dealer_hand.add_card(new_card)
            
            if dealer_hand.calculate_value() > 21:
                # Dealer Busts -> Player Wins
                self.send_card(client_socket, new_card, RESULT_WIN)
                return # Round over
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
        Helper to send a card payload.

        Args:
            sock (socket.socket): The socket to send to.
            card (Card): The card to send.
            result (int): The current game result status.
        """
        packet = pack_payload_server(result, card.rank, card.suit)
        sock.sendall(packet)

    def send_result(self, sock, result):
        """
        Helper to send a result payload without a card.

        Args:
            sock (socket.socket): The socket to send to.
            result (int): The final game result.
        """
        packet = pack_payload_server(result, 0, 0) # Rank 0, Suit 0
        sock.sendall(packet)

if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer stopping...")
