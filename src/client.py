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
    MSG_TYPE_OFFER
)
from src.protocol import unpack_offer, pack_request

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
                # Note: Instructions say "Client asks the user for the number of rounds... then connects"
                # But also "Client started, listening for offer requests...".
                # The example flow:
                # 3. Client asks user for rounds.
                # 4. Client prints "listening for offer requests".
                # 5. Client gets offer.
                # 6. Client connects.
                
                # So we ask first.
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
            
            # TODO: Handle game loop
            print(f"Connected to server. Requested {num_rounds} rounds.")
            
            # Placeholder for game loop
            # For now, just close to test connection
            # tcp_socket.close() 
            
        except Exception as e:
            print(f"Failed to connect to server: {e}")
        finally:
            tcp_socket.close()

if __name__ == "__main__":
    client = Client()
    client.start()
