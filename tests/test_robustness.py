"""
tests/test_robustness.py

Overview
--------
Robustness / negative testing for the Blackjack client-server system.

This test file verifies that both the server and the client behave safely when
receiving invalid, malformed, or unexpected data.

The focus is not on correct gameplay, but on stability:
- The server should reject invalid requests and close connections gracefully.
- The client should not crash when connected to a misbehaving server.

How to run:
-----------
    python -m tests.test_robustness
(or)
    python tests/test_robustness.py

Notes:
------
- These tests rely on networking + timing, so they are not deterministic unit tests.
- PASS/FAIL is reported via printed messages (not via unittest assertions).
- The server is started once (daemon thread), then multiple negative tests are run.
"""

import socket
import threading
import time
import sys
import os
import struct

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.server import Server
from src.client import Client
from src.consts import MAGIC_COOKIE, MSG_TYPE_REQUEST
from src.protocol import pack_request, SIZE_REQUEST

SERVER_PORT = 0  # Will be set after server starts
SERVER_IP = "127.0.0.1"  # Will be set after server starts


def run_server():
    """
    Starts the real server and exposes its IP and TCP port.

    This allows the robustness tests to connect directly to a live server
    instance without relying on UDP discovery.
    """
    global SERVER_PORT, SERVER_IP
    server = Server()
    SERVER_PORT = server.tcp_port
    SERVER_IP = server.local_ip
    server.start()


def run_bad_server():
    """
    Runs a minimal TCP server that intentionally violates the protocol.

    The server accepts one connection, ignores the request, sends garbage data,
    and closes the connection. Used to test client robustness.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.listen(1)
    print(f"Bad Server listening on {port}")

    # We need to trick the client into connecting to us.
    # Since Client listens for UDP offers, we can't easily inject ourselves
    # without mocking the UDP part or modifying Client.
    # However, Client.connect_and_play takes IP/Port directly.
    # So we can just instantiate Client and call connect_and_play.

    conn, addr = s.accept()
    print(f"Bad Server accepted {addr}")

    # Receive request
    conn.recv(1024)

    # Send Garbage
    print("Bad Server sending garbage...")
    conn.sendall(b"\x00\x00\x00\x00" * 10)
    time.sleep(1)
    conn.close()
    return port


def test_client_robustness():
    """
    Tests that the client does not crash when connected to a bad server.

    A fake server sends invalid payload data. The client should handle this
    gracefully and exit without throwing an uncaught exception.
    """
    print("\n>>> TEST 4: Client Robustness against Bad Server <<<")

    # Start Bad Server in a thread
    bad_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bad_server_socket.bind(("127.0.0.1", 0))
    bad_port = bad_server_socket.getsockname()[1]
    bad_server_socket.listen(1)

    def bad_server_logic():
        try:
            conn, _ = bad_server_socket.accept()
            conn.recv(1024)  # Read request
            conn.sendall(b"GARBAGE_PAYLOAD_DATA")
            time.sleep(0.5)
            conn.close()
        except:
            pass

    t = threading.Thread(target=bad_server_logic, daemon=True)
    t.start()

    # Run Client
    # We bypass the UDP listening part and call connect_and_play directly
    client = Client("RobustClient", 1)
    print(f"Client connecting to Bad Server on port {bad_port}...")

    # This should not crash. It should print "Invalid payload" or error and exit.
    try:
        client.connect_and_play("127.0.0.1", bad_port, 1)
        print("PASS: Client handled bad server without crashing.")
    except Exception as e:
        print(f"FAIL: Client crashed with: {e}")

    bad_server_socket.close()


def test_invalid_request():
    """
    Tests sending completely invalid request data to the server.

    The server is expected to detect the invalid request and close the
    connection instead of continuing the protocol.
    """
    print("\n>>> TEST 1: Sending Invalid Request (Garbage Data) <<<")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))

        # Send garbage data (wrong size, wrong magic)
        garbage = b"\x00\x00\x00\x00" * 10
        sock.sendall(garbage)

        # Try to read response. Server should close connection.
        # recv should return empty bytes eventually
        sock.settimeout(2)
        try:
            data = sock.recv(1024)
            if not data:
                print("PASS: Server closed connection upon invalid request.")
            else:
                print("FAIL: Server sent data back (unexpected).")
        except socket.timeout:
            print("FAIL: Server kept connection open (timeout).")
        except (ConnectionResetError, OSError) as e:
            # On some systems (Windows), forceful close raises this
            print("PASS: Server closed connection forcefull upon invalid request.")

        sock.close()
    except Exception as e:
        print(f"Error in Test 1: {e}")


def test_wrong_magic_cookie():
    """
    Tests sending a request with an incorrect magic cookie.

    The server should validate the magic cookie and reject the request.
    """
    print("\n>>> TEST 2: Sending Request with Wrong Magic Cookie <<<")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))

        # Pack a request but corrupt the magic cookie
        # Format: !IBB32s -> Magic, Type, Rounds, Name
        # Real Magic is 0xabcddcba. We send 0xdeadbeef
        bad_packet = struct.pack(
            "!IBB32s", 0xDEADBEEF, 0x3, 1, b"BadClient".ljust(32, b"\x00")
        )
        sock.sendall(bad_packet)

        # Server should close connection
        sock.settimeout(2)
        try:
            data = sock.recv(1024)
            if not data:
                print("PASS: Server closed connection on wrong magic cookie.")
            else:
                print("FAIL: Server accepted wrong magic cookie.")
        except socket.timeout:
            print("FAIL: Server kept connection open.")

        sock.close()
    except Exception as e:
        print(f"Error in Test 2: {e}")


def test_invalid_game_packet():
    """
    Tests sending invalid data during the game decision phase.

    Instead of a valid HIT/STAND payload, garbage data is sent.
    The server should close the connection gracefully.
    """
    print("\n>>> TEST 3: Sending Garbage during Game Loop <<<")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))

        # 1. Send Valid Request
        req = pack_request(1, "BadGamer")
        sock.sendall(req)

        # 2. Receive Initial Cards (Server sends 3 packets: P1, P2, D1)
        # We just consume them
        sock.recv(1024)

        # 3. Now it's our turn. Send garbage instead of "Hittt" or "Stand"
        sock.sendall(b"GARBAGE_DATA_NOT_VALID")

        # Server should disconnect us
        sock.settimeout(2)
        try:
            # We might get some more cards if server was fast, but eventually it should close
            while True:
                data = sock.recv(1024)
                if not data:
                    print("PASS: Server closed connection on invalid game packet.")
                    break
        except socket.timeout:
            print("FAIL: Server kept connection open after garbage game packet.")
        except (ConnectionResetError, OSError) as e:
            print("PASS: Server closed connection forcefully on invalid game packet.")

        sock.close()
    except Exception as e:
        print(f"Error in Test 3: {e}")


if __name__ == "__main__":
    # Start Server
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1)  # Wait for server to bind

    test_invalid_request()
    test_wrong_magic_cookie()
    test_invalid_game_packet()
    test_client_robustness()

    print("\nDone.")
