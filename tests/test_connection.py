import socket
import threading
import time
import struct
from src.server import Server
from src.protocol import unpack_offer, pack_request
from src.consts import CLIENT_UDP_PORT

def test_server_connection():
    """
    Tests the basic connection flow between client and server.
    Verifies UDP discovery and TCP connection establishment.
    """
    # Start Server in a separate thread
    server = Server()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    time.sleep(1) # Wait for server to start
    
    # Client Logic Simulation
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    udp_socket.bind(('', CLIENT_UDP_PORT))
    
    print("Test Client listening...")
    
    # Receive Offer
    data, addr = udp_socket.recvfrom(1024)
    server_ip = addr[0]
    result = unpack_offer(data)
    
    if result:
        server_port, server_name = result
        print(f"Received offer from {server_name} at {server_ip}:{server_port}")
        
        # Connect TCP
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((server_ip, server_port))
        print("Connected to server TCP!")
        
        # Send Request
        req = pack_request(3, "TestTeam")
        tcp_socket.sendall(req)
        print("Sent request.")
        
        tcp_socket.close()
        print("Test Passed!")
    else:
        print("Invalid offer received.")

    server.running = False

if __name__ == "__main__":
    test_server_connection()
