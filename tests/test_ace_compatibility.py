import threading
import time
import socket
import sys
import os
import struct

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.consts import *
from src.protocol import *
from src.game_logic import Card, Deck
from src.server import Server
from src.client import Client

# --- Dumb Logic (Ace is ALWAYS 11) ---

class DumbHand:
    """A Hand that treats Ace as 11 always."""
    def __init__(self):
        self.cards = []

    def add_card(self, card):
        self.cards.append(card)

    def calculate_value(self):
        val = 0
        for card in self.cards:
            if card.rank == 1: # Ace
                val += 11
            elif card.rank >= 10: # Face
                val += 10
            else:
                val += card.rank
        return val

# --- Dumb Client Implementation ---
# (Minimal copy of Client that uses DumbHand)

class DumbClient(Client):
    def __init__(self, name, rounds):
        super().__init__(player_name=name, auto_rounds=rounds)
    
    def play_round(self, tcp_socket):
        """Same as Client.play_round but uses DumbHand."""
        cards_received = 0
        my_turn = True
        player_hand = DumbHand() # <--- The Change
        
        while True:
            try:
                data = recv_exact(tcp_socket, SIZE_PAYLOAD_SERVER)
            except:
                raise Exception("Server disconnected")
                
            payload = unpack_payload_server(data)
            if not payload: continue
            result, rank, suit = payload
            
            if rank != 0:
                card = Card(rank, suit)
                if cards_received < 2:
                    player_hand.add_card(card)
                elif cards_received == 2:
                    pass # Dealer card
                else:
                    if my_turn: player_hand.add_card(card)
                cards_received += 1

            if result != 0:
                return result
            
            if cards_received >= 3 and my_turn:
                val = player_hand.calculate_value()
                # Dumb Strategy: Stand on 17 (even if soft)
                # But since Ace is always 11, Soft 17 (A+6) is just 17.
                # The difference is A+A = 22 (Bust) instead of 12.
                print(f"[{self.player_name} (Dumb)] Hand Value: {val}")
                
                if val < 17:
                    tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_HIT))
                else:
                    tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_STAND))
                    my_turn = False

# --- Dumb Server Implementation ---
# (Minimal copy of Server that uses DumbHand)

class DumbServer(Server):
    def play_round(self, client_socket):
        """Same as Server.play_round but uses DumbHand."""
        deck = Deck()
        player_hand = DumbHand() # <--- The Change
        dealer_hand = DumbHand() # <--- The Change

        # Initial Deal
        c1 = deck.deal_card(); player_hand.add_card(c1); self.send_card(client_socket, c1, RESULT_CONTINUE)
        c2 = deck.deal_card(); player_hand.add_card(c2); self.send_card(client_socket, c2, RESULT_CONTINUE)
        d1 = deck.deal_card(); dealer_hand.add_card(d1); self.send_card(client_socket, d1, RESULT_CONTINUE)
        d2 = deck.deal_card(); dealer_hand.add_card(d2)

        # Player Turn
        player_busted = False
        while True:
            data = recv_exact(client_socket, SIZE_PAYLOAD_CLIENT)
            decision = unpack_payload_client(data)
            if decision == PAYLOAD_DECISION_HIT:
                new_card = deck.deal_card()
                player_hand.add_card(new_card)
                if player_hand.calculate_value() > 21:
                    self.send_card(client_socket, new_card, RESULT_LOSS)
                    player_busted = True
                    break
                else:
                    self.send_card(client_socket, new_card, RESULT_CONTINUE)
            elif decision == PAYLOAD_DECISION_STAND:
                break
        
        if player_busted: return

        # Dealer Turn
        self.send_card(client_socket, d2, RESULT_CONTINUE)
        while dealer_hand.calculate_value() < 17:
            new_card = deck.deal_card()
            dealer_hand.add_card(new_card)
            if dealer_hand.calculate_value() > 21:
                self.send_card(client_socket, new_card, RESULT_WIN)
                return
            else:
                self.send_card(client_socket, new_card, RESULT_CONTINUE)

        # Winner
        p_val = player_hand.calculate_value()
        d_val = dealer_hand.calculate_value()
        if p_val > d_val: res = RESULT_WIN
        elif d_val > p_val: res = RESULT_LOSS
        else: res = RESULT_TIE
        self.send_result(client_socket, res)

# --- Test Runner ---

def test_smart_server_dumb_client():
    print("\n>>> TEST 1: Smart Server (Yours) vs Dumb Client (Ace=11) <<<")
    server = Server()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(1)
    
    client = DumbClient("DumbClient", 2)
    client.start()
    print(">>> TEST 1 PASSED (Game finished without crash) <<<")

def test_dumb_server_smart_client():
    print("\n>>> TEST 2: Dumb Server (Ace=11) vs Smart Client (Yours) <<<")
    # We need to run this on a different port or restart logic, 
    # but for simplicity we'll just instantiate a new server object 
    # (it binds to a random port so it's fine)
    
    server = DumbServer()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(1)
    
    client = Client("SmartClient", 2)
    client.start()
    print(">>> TEST 2 PASSED (Game finished without crash) <<<")

if __name__ == "__main__":
    # Run sequentially
    try:
        test_smart_server_dumb_client()
        time.sleep(2)
        test_dumb_server_smart_client()
    except KeyboardInterrupt:
        pass
