"""
tests/test_connection.py

Overview
--------
Integration / smoke test for the basic client-server connection flow.

This test verifies that:
- The server starts successfully in a background thread.
- A client can discover the server via UDP Offer broadcast.
- The client can establish a TCP connection to the offered port.
- The client can send a valid Request message after connecting.

This test checks connectivity + protocol handshake, not gameplay.

How to run:
-----------
    python -m tests.test_connection
(or)
    python tests/test_connection.py

Notes:
------
- This is not a deterministic unit test (depends on networking + timing).
- Success is typically verified by reaching "Test Passed!" without exceptions.
"""

import socket
import threading
import time
import struct
from src.server import Server
from src.protocol import unpack_offer, pack_request
from src.consts import CLIENT_UDP_PORT


def test_server_connection():
    """
    Runs a minimal end-to-end connection handshake.

    Flow:
    - Start the server in a daemon thread.
    - Create a UDP socket bound to CLIENT_UDP_PORT to receive server offers.
    - Wait for an Offer packet and unpack it to obtain server_ip and server_port.
    - Open a TCP connection to the server.
    - Send a Request packet (e.g., requesting 3 rounds) to validate request sending.

    Expected behavior:
    - The offer unpacks successfully.
    - TCP connection succeeds.
    - Request is sent without errors.
    """
    # Start Server in a separate thread
    server = Server()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    time.sleep(1)  # Allow server time to start broadcasting / listening

    # Client discovery socket (UDP)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    udp_socket.bind(("", CLIENT_UDP_PORT))

    print("Test Client listening...")

    # Receive Offer
    data, addr = udp_socket.recvfrom(1024)
    server_ip = addr[0]
    result = unpack_offer(data)

    if result:
        server_port, server_name = result
        print(f"Received offer from {server_name} at {server_ip}:{server_port}")

        # Connect via TCP
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((server_ip, server_port))
        print("Connected to server TCP!")

        # Send a Request (e.g., request 3 rounds for team "TestTeam")
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
