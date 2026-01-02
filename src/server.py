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
    MSG_TYPE_OFFER
)
from src.protocol import pack_offer

SERVER_NAME = "BlackijeckyServer"

class Server:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind(('', 0))  # Bind to any available port
        self.tcp_port = self.tcp_socket.getsockname()[1]
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.running = True
        
        # Get local IP for display purposes (optional, but good for debugging)
        try:
            self.local_ip = socket.gethostbyname(socket.gethostname())
        except:
            self.local_ip = "127.0.0.1"

    def start(self):
        """Starts the server: UDP broadcast and TCP listener."""
        print(f"Server started, listening on IP address {self.local_ip}")
        
        # Start UDP Broadcast Thread
        broadcast_thread = threading.Thread(target=self.broadcast_offers, daemon=True)
        broadcast_thread.start()
        
        # Start TCP Listener
        self.listen_tcp()

    def broadcast_offers(self):
        """Sends UDP Offer packets every second."""
        packet = pack_offer(self.tcp_port, SERVER_NAME)
        print(f"Server started, listening on IP address {self.local_ip}") # Re-print as per example flow
        
        while self.running:
            try:
                self.udp_socket.sendto(packet, (BROADCAST_IP, CLIENT_UDP_PORT))
                # print(f"Broadcasted offer on port {CLIENT_UDP_PORT}") # Debug
                time.sleep(OFFER_INTERVAL)
            except Exception as e:
                print(f"Error broadcasting: {e}")

    def listen_tcp(self):
        """Listens for incoming TCP connections."""
        self.tcp_socket.listen()
        print(f"Listening for TCP connections on port {self.tcp_port}...")
        
        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                print(f"New connection from {addr}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")

    def handle_client(self, client_socket: socket.socket, addr):
        """Handles a single client connection."""
        try:
            # TODO: Implement handshake and game loop
            pass
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()

if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer stopping...")
