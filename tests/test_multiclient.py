"""
tests/test_multiclient.py

Overview
--------
Integration / smoke test for the Blackjack project.

This test runs a real server and two real clients ("Alice" and "Bob")
concurrently to verify that:
- The server can start and accept connections.
- Multiple clients can discover the server and connect simultaneously.
- Each client can request and play several rounds automatically.

This test focuses on concurrency and networking behavior, not on
deterministic game outcomes.

How to run:
-----------
    python -m tests.test_multiclient

Notes:
------
- This is NOT a strict pass/fail unit test.
- Output is validated manually via logs.
- The test is time-bounded using sleep().
"""

import threading
import time
import sys
import os

# Allow imports from project root when running as a module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.server import Server
from src.client import Client


def run_server():
    """
    Starts the Blackjack server.

    This function is intended to run in a background thread.
    It initializes the Server instance and starts its main loop
    (listening, broadcasting offers, accepting clients, etc.).
    """
    print("--- Starting Server Thread ---")
    server = Server()
    # We run it in a daemon thread so it dies when main script dies
    server.start()


def run_client(name, rounds):
    """
    Starts a single client in auto-play mode.

    Args:
        name (str): Player name (e.g., "Alice", "Bob").
        rounds (int): Number of rounds to request from the server.

    The client performs:
    discovery -> connection -> round requests -> automatic gameplay.
    """
    print(f"--- Starting Client {name} Thread ---")
    # Give server a moment to start
    time.sleep(1)
    client = Client(player_name=name, auto_rounds=rounds)
    client.start()


if __name__ == "__main__":
    # 1. Start Server
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. Start Client 1
    client1_thread = threading.Thread(target=run_client, args=("Alice", 2), daemon=True)
    client1_thread.start()

    # 3. Start Client 2
    client2_thread = threading.Thread(target=run_client, args=("Bob", 2), daemon=True)
    client2_thread.start()

    # Let simulation run for a limited time
    try:
        print("Simulation running for 20 seconds...")
        time.sleep(20)
    except KeyboardInterrupt:
        pass

    print("Simulation finished.")
