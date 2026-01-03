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
    Colors
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
        self.player_name = player_name
        self.auto_rounds = auto_rounds
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
        """Main client loop."""
        # 1. Get user input (Once)
        if self.auto_rounds is not None:
            num_rounds = self.auto_rounds
            print(f"{Colors.OKBLUE}[{self.player_name}] Auto-selecting {num_rounds} rounds{Colors.ENDC}")
        else:
            while True:
                try:
                    num_rounds = int(input("How many rounds do you want to play? "))
                    break
                except ValueError:
                    print("Please enter a valid number.")

        while True:
            try:
                print(f"{Colors.OKGREEN}[{self.player_name}] Client started, listening for offer requests...{Colors.ENDC}")
                
                # 2. Listen for UDP Offer
                server_ip, server_port = self.listen_for_offer()
                if not server_ip:
                    continue
                
                # 3. Connect via TCP
                self.connect_and_play(server_ip, server_port, num_rounds)
                
            except KeyboardInterrupt:
                print("\nClient stopping...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def listen_for_offer(self):
        """Waits for a valid UDP offer."""
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            result = unpack_offer(data)
            
            if result:
                server_port, server_name = result
                print(f"Received offer from {addr[0]}, attempting to connect...")
                return addr[0], server_port
            else:
                # Invalid packet, ignore
                pass

    def connect_and_play(self, server_ip, server_port, num_rounds):
        """Connects to server and handles the game session."""
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_socket.settimeout(15) # 15 seconds timeout for network operations
            tcp_socket.connect((server_ip, server_port))
            
            # 4. Send Request
            request_packet = pack_request(num_rounds, self.player_name)
            tcp_socket.sendall(request_packet)
            print(f"Connected to server. Requested {num_rounds} rounds.")
            
            wins = 0
            
            for i in range(1, num_rounds + 1):
                print(f"\n{Colors.HEADER}{'='*20} Round {i} {'='*20}{Colors.ENDC}")
                try:
                    result = self.play_round(tcp_socket)
                    if result == RESULT_WIN:
                        wins += 1
                        print(f"\n{Colors.OKGREEN}{'*'*10} You Won! {'*'*10}{Colors.ENDC}")
                    elif result == RESULT_LOSS:
                        print(f"\n{Colors.FAIL}{'!'*10} You Lost! {'!'*10}{Colors.ENDC}")
                    elif result == RESULT_TIE:
                        print(f"\n{Colors.WARNING}{'-'*10} It's a Tie! {'-'*10}{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error during round {i}: {e}{Colors.ENDC}")
                    break
            
            print(f"\n{Colors.HEADER}{'='*50}{Colors.ENDC}")
            print(f"{Colors.BOLD}Finished playing {num_rounds} rounds, win rate: {wins/num_rounds:.2f}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*50}{Colors.ENDC}\n")
            
        except socket.timeout:
            print("Connection timed out.")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
        finally:
            tcp_socket.close()
            print("Disconnected from server.")

    def play_round(self, tcp_socket):
        """Handles a single round of the game."""
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
                
                if current_value < 17:
                    print(f"{Colors.BOLD}-> Client decides to HIT{Colors.ENDC}")
                    tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_HIT))
                else:
                    print(f"{Colors.BOLD}-> Client decides to STAND{Colors.ENDC}")
                    tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_STAND))
                    my_turn = False

if __name__ == "__main__":
    client = Client()
    client.start()
