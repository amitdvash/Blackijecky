import threading
import time
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.server import Server
from src.client import Client

def run_server():
    """
    Starts the server in a separate thread.
    Used for multi-client simulation.
    """
    print("--- Starting Server Thread ---")
    server = Server()
    # We run it in a daemon thread so it dies when main script dies
    server.start()

def run_client(name, rounds):
    """
    Starts a client in a separate thread.

    Args:
        name (str): The name of the client.
        rounds (int): The number of rounds to play.
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
    
    # Let them play for a bit (e.g., 15 seconds)
    # Since clients loop forever, we just wait enough time for them to finish a game or two
    try:
        print("Simulation running for 20 seconds...")
        time.sleep(20)
    except KeyboardInterrupt:
        pass
    
    print("Simulation finished.")
