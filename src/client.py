"""
Client application for Blackijecky.
Handles UDP listening and TCP connection to server.
"""

import socket
import struct
import sys
from src.consts import (
    CLIENT_UDP_PORT,
    MAGIC_COOKIE,
    MSG_TYPE_OFFER,
    RANK_MAP,
    SUIT_MAP,
    RESULT_WIN,
    RESULT_LOSS,
    RESULT_TIE,
    PAYLOAD_DECISION_HIT,
    PAYLOAD_DECISION_STAND,
    Colors,
    BUFFER_SIZE,
    SOCKET_TIMEOUT
)
from src.protocol import (
    unpack_offer, 
    pack_request, 
    unpack_payload_server, 
    pack_payload_client,
    SIZE_PAYLOAD_SERVER,
    recv_exact
)
from src.game_logic import Hand, Card

TEAM_NAME = "404_Win_Not_Found_Client"

class Client:
    def __init__(self, player_name=TEAM_NAME, auto_rounds=None):
        """
        Initializes the Client.
        Sets up the UDP socket for listening to offers.

        Args:
            player_name (str, optional): The name of the player/team. Defaults to TEAM_NAME.
            auto_rounds (int, optional): If set, automatically plays this many rounds without user input. Defaults to None.
        """
        self.player_name = player_name
        self.auto_rounds = auto_rounds
        self.manual_mode = False  # Default to False
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enable address reuse to allow multiple clients on same machine
        try:
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            # SO_REUSEPORT is not available on Windows, use SO_REUSEADDR
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
        self.udp_socket.bind(('', CLIENT_UDP_PORT))
        print("Client started, listening for offer requests...")

    def start(self):
        """
        Main client loop.
        Gets user input for rounds, listens for offers, and connects to the server.
        """
        while True:
            # 1. Get user input (Repeatedly)
            if self.auto_rounds is not None:
                num_rounds = self.auto_rounds
                print(f"{Colors.OKBLUE}[{self.player_name}] Auto-selecting {num_rounds} rounds{Colors.ENDC}")
            else:
                while True:
                    try:
                        mode_in = input("Do you want to play manually? (y/n) ").strip().lower()
                        if mode_in in ['y', 'yes', 'true']:
                            self.manual_mode = True
                            break
                        elif mode_in in ['n', 'no', 'false']:
                            self.manual_mode = False
                            break
                    except Exception:
                        pass
                        
                while True:
                    try:
                        user_in = input("How many rounds do you want to play? ")
                        num_rounds = int(user_in)
                        if num_rounds < 1 or num_rounds > 255:
                            print("Please enter a number between 1 and 255.")
                            continue
                        break
                    except ValueError:
                        print("Please enter a valid number.")

            # Inner Loop: Find server and play
            rounds_completed = False
            while not rounds_completed:
                try:
                    print(f"{Colors.OKGREEN}[{self.player_name}] Client started, listening for offer requests...{Colors.ENDC}")
                    
                    # 2. Listen for UDP Offer
                    server_ip, server_port = self.listen_for_offer()
                    if not server_ip:
                        continue
                    
                    # 3. Connect via TCP
                    rounds_completed = self.connect_and_play(server_ip, server_port, num_rounds)
                    
                    if not rounds_completed:
                        print(f"{Colors.WARNING}Session failed or disconnected. Searching for new server to play {num_rounds} rounds...{Colors.ENDC}")

                except KeyboardInterrupt:
                    print("\nClient stopping...")
                    return
                except Exception as e:
                    print(f"Error: {e}")

    def listen_for_offer(self):
        """
        Waits for a valid UDP offer.
        Blocks until a valid offer is received.

        Returns:
            tuple: A tuple containing (server_ip, server_port).
        """
        while True:
            data, addr = self.udp_socket.recvfrom(BUFFER_SIZE)
            result = unpack_offer(data)
            
            if result:
                server_port, server_name = result
                print(f"Received offer from {addr[0]}, attempting to connect...")
                return addr[0], server_port
            else:
                # Invalid packet, ignore
                pass

    def connect_and_play(self, server_ip, server_port, num_rounds):
        """
        Connects to server and handles the game session.
        Manages the TCP connection and plays the specified number of rounds.

        Args:
            server_ip (str): The IP address of the server.
            server_port (int): The TCP port of the server.
            num_rounds (int): The number of rounds to play.
        """
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_socket.settimeout(SOCKET_TIMEOUT) # Timeout for network operations
            tcp_socket.connect((server_ip, server_port))
            
            # 4. Send Request
            request_packet = pack_request(num_rounds, self.player_name)
            tcp_socket.sendall(request_packet)
            print(f"Connected to server. Requested {num_rounds} rounds.")
            
            wins = 0
            losses = 0
            ties = 0
            completed_all_rounds = True
            
            for i in range(1, num_rounds + 1):
                print(f"\n{Colors.HEADER}{'='*20} Round {i} {'='*20}{Colors.ENDC}")
                try:
                    result = self.play_round(tcp_socket)
                    if result == RESULT_WIN:
                        wins += 1
                        print(f"\n{Colors.OKGREEN}{'*'*10} You Won! {'*'*10}{Colors.ENDC}")
                    elif result == RESULT_LOSS:
                        losses += 1
                        print(f"\n{Colors.FAIL}{'!'*10} You Lost! {'!'*10}{Colors.ENDC}")
                    elif result == RESULT_TIE:
                        ties += 1
                        print(f"\n{Colors.WARNING}{'-'*10} It's a Tie! {'-'*10}{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error during round {i}: {e}{Colors.ENDC}")
                    completed_all_rounds = False
                    break
            
            print(f"\n{Colors.HEADER}{'='*50}{Colors.ENDC}")
            print(f"{Colors.BOLD}Game Statistics:{Colors.ENDC}")
            print(f"  Wins:   {wins}")
            print(f"  Losses: {losses}")
            print(f"  Ties:   {ties}")
            if num_rounds > 0:
                print(f"  Win Rate: {wins/num_rounds:.2%}")
            print(f"{Colors.HEADER}{'='*50}{Colors.ENDC}\n")
            
            return completed_all_rounds
            
        except socket.timeout:
            print("Connection timed out.")
            return False
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
        finally:
            tcp_socket.close()
            print("Disconnected from server.")

    def play_round(self, tcp_socket):
        """
        Handles a single round of the game.
        Receives cards, makes decisions (Hit/Stand), and returns the result.

        Args:
            tcp_socket (socket.socket): The TCP socket connected to the server.

        Returns:
            int: The result of the round (RESULT_WIN, RESULT_LOSS, RESULT_TIE).

        Raises:
            Exception: If server disconnects or sends invalid data.
        """
        cards_received = 0
        my_turn = True # Initially true, waiting for initial deal
        player_hand = Hand()
        
        while True:
            # Read exactly one packet size
            try:
                data = recv_exact(tcp_socket, SIZE_PAYLOAD_SERVER)
            except Exception:
                raise Exception("Server disconnected")
                
            payload = unpack_payload_server(data)
            if not payload:
                print("Invalid payload received")
                continue
                
            result, rank, suit = payload
            
            # Display Card
            if rank != 0:
                card = Card(rank, suit)
                card_str = str(card)
                
                if cards_received < 2:
                    print(f"{Colors.OKCYAN}Player Card: {card_str}{Colors.ENDC}")
                    player_hand.add_card(card)
                elif cards_received == 2:
                    print(f"{Colors.WARNING}Dealer Card: {card_str}{Colors.ENDC}")
                else:
                    # After initial deal
                    if my_turn:
                        print(f"{Colors.OKCYAN}Player Dealt: {card_str}{Colors.ENDC}")
                        player_hand.add_card(card)
                    else:
                        print(f"{Colors.WARNING}Dealer Dealt: {card_str}{Colors.ENDC}")
                
                cards_received += 1

            # Check Result
            if result != 0:
                return result
            
            # Game Logic (Automated Heuristic)
            # We decide if:
            # 1. We just got the 3rd card (Initial deal complete: P1, P2, D1)
            # 2. We just got a card and it's still our turn (Hit response)
            
            if cards_received >= 3 and my_turn:
                current_value = player_hand.calculate_value()
                print(f"{Colors.OKBLUE}Current Hand Value: {current_value}{Colors.ENDC}")
                
                decision = None
                
                if self.manual_mode:
                    print(f"{Colors.WARNING}Your turn!{Colors.ENDC}")
                    while decision not in [PAYLOAD_DECISION_HIT, PAYLOAD_DECISION_STAND]:
                        try:
                            # Use input but handle potential interrupts
                            user_input = input("Choose action (h)it or (s)tand: ").lower().strip()
                            if user_input in ['h', 'hit']:
                                decision = PAYLOAD_DECISION_HIT
                            elif user_input in ['s', 'stand']:
                                decision = PAYLOAD_DECISION_STAND
                            else:
                                print("Invalid input. Please enter 'h' or 's'.")
                        except EOFError:
                            # Handle case where input stream closes unexpectedly
                            decision = PAYLOAD_DECISION_STAND
                else:
                    if current_value < 17:
                        decision = PAYLOAD_DECISION_HIT
                    else:
                        decision = PAYLOAD_DECISION_STAND

                if decision == PAYLOAD_DECISION_HIT:
                    print(f"{Colors.BOLD}-> Client decides to HIT{Colors.ENDC}")
                    tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_HIT))
                else:
                    print(f"{Colors.BOLD}-> Client decides to STAND{Colors.ENDC}")
                    tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_STAND))
                    my_turn = False

if __name__ == "__main__":
    client = Client()
    client.start()
