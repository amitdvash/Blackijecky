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
    PAYLOAD_DECISION_STAND
)
from src.protocol import (
    unpack_offer, 
    pack_request, 
    unpack_payload_server, 
    pack_payload_client,
    SIZE_PAYLOAD_SERVER
)

TEAM_NAME = "BlackijeckyClient"

class Client:
    def __init__(self):
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
        while True:
            try:
                # 1. Get user input
                try:
                    num_rounds = int(input("How many rounds do you want to play? "))
                except ValueError:
                    print("Please enter a valid number.")
                    continue

                print("Client started, listening for offer requests...")
                
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
            tcp_socket.connect((server_ip, server_port))
            
            # 4. Send Request
            request_packet = pack_request(num_rounds, TEAM_NAME)
            tcp_socket.sendall(request_packet)
            print(f"Connected to server. Requested {num_rounds} rounds.")
            
            wins = 0
            
            for i in range(1, num_rounds + 1):
                print(f"\n--- Round {i} ---")
                result = self.play_round(tcp_socket)
                if result == RESULT_WIN:
                    wins += 1
                    print("You Won!")
                elif result == RESULT_LOSS:
                    print("You Lost!")
                elif result == RESULT_TIE:
                    print("It's a Tie!")
            
            print(f"\nFinished playing {num_rounds} rounds, win rate: {wins/num_rounds:.2f}")
            
        except Exception as e:
            print(f"Failed to connect to server: {e}")
        finally:
            tcp_socket.close()

    def play_round(self, tcp_socket):
        """Handles a single round of the game."""
        cards_received = 0
        my_turn = True # Initially true, waiting for initial deal
        
        while True:
            # Read exactly one packet size
            try:
                data = self.recv_exact(tcp_socket, SIZE_PAYLOAD_SERVER)
            except Exception:
                raise Exception("Server disconnected")
                
            payload = unpack_payload_server(data)
            if not payload:
                print("Invalid payload received")
                continue
                
            result, rank, suit = payload
            
            # Display Card
            if rank != 0:
                card_str = f"{RANK_MAP.get(rank, rank)} of {SUIT_MAP.get(suit, suit)}"
                if cards_received < 2:
                    print(f"Player Card: {card_str}")
                elif cards_received == 2:
                    print(f"Dealer Card: {card_str}")
                else:
                    # After initial deal
                    if my_turn:
                        print(f"Player Dealt: {card_str}")
                    else:
                        print(f"Dealer Dealt: {card_str}")
                
                cards_received += 1

            # Check Result
            if result != 0:
                return result
            
            # Game Logic (Prompt User)
            # We prompt if:
            # 1. We just got the 3rd card (Initial deal complete: P1, P2, D1)
            # 2. We just got a card and it's still our turn (Hit response)
            
            if cards_received >= 3 and my_turn:
                while True:
                    choice = input("Action (Hit/Stand): ").strip().lower()
                    if choice in ['hit', 'h']:
                        tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_HIT))
                        break # Wait for next card
                    elif choice in ['stand', 's']:
                        tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_STAND))
                        my_turn = False
                        break # Wait for dealer cards / result
                    else:
                        print("Invalid input. Please enter 'Hit' or 'Stand'.")

    def recv_exact(self, sock, size):
        """Helper to receive exactly 'size' bytes."""
        buf = b''
        while len(buf) < size:
            data = sock.recv(size - len(buf))
            if not data:
                raise Exception("Connection closed")
            buf += data
        return buf

if __name__ == "__main__":
    client = Client()
    client.start()
