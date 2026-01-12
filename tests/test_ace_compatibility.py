"""
tests/test_ace_compatibility.py

Overview
--------
Compatibility / robustness test focused on Ace-handling differences.

This file validates that the client-server protocol and game flow remain stable
even if one side uses a different internal hand-value logic for Aces.

Scenario being tested
---------------------
- "Smart" implementation (normal project):
  Ace can be 1 or 11 depending on best non-busting value.

- "Dumb" implementation (in this test file):
  Ace is ALWAYS treated as 11, which can cause different decisions/outcomes.

Two compatibility checks are performed:
1) Smart Server (project Server) + Dumb Client (Ace always 11)
2) Dumb Server (Ace always 11) + Smart Client (project Client)

Goal
----
Not to validate who wins, but to verify that:
- The protocol still works (pack/unpack payloads).
- The game completes without crashes, deadlocks, or disconnect loops.

How to run:
-----------
    python -m tests.test_ace_compatibility
(or)
    python tests/test_ace_compatibility.py

Notes:
------
- Not a deterministic unit test (random cards + timing + networking).
- This is a compatibility/integration test.
- This file is intentionally time-bounded (no infinite run / no Ctrl+C needed).
"""

import threading
import time
import socket
import sys
import os
import struct

# Add project root so "src" imports work when running this file as a script/module.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.consts import *
from src.protocol import *
from src.game_logic import Card, Deck
from src.server import Server
from src.client import Client

# --- Dumb Logic (Ace is ALWAYS 11) ---


class DumbHand:
    """
    A simplified Hand implementation for testing.

    Difference vs real logic:
    - Ace (rank == 1) is ALWAYS worth 11.
    - This makes hands like A+A evaluate to 22 (bust) instead of 12.

    Purpose:
    - Used to intentionally create a mismatch between client/server hand logic
      to ensure the system stays stable and compatible.
    """

    def __init__(self):
        """Initializes an empty DumbHand."""
        self.cards = []

    def add_card(self, card):
        """
        Adds a card to the hand.

        Args:
            card (Card): The card to add.
        """
        self.cards.append(card)

    def calculate_value(self):
        """
        Client variant that uses DumbHand.

        Purpose:
        - Simulates a client that makes decisions based on a different Ace rule,
          while still speaking the same protocol and using the same networking flow.
        """
        val = 0
        for card in self.cards:
            if card.rank == 1:  # Ace
                val += 11
            elif card.rank >= 10:  # Face
                val += 10
            else:
                val += card.rank
        return val


# --- Dumb Client Implementation ---
# (Minimal copy of Client that uses DumbHand)


class DumbClient(Client):
    def __init__(self, name, rounds):
        """
        Initialize the dumb client.

        Args:
            name (str): Player name.
            rounds (int): Number of rounds to request/play.
        """
        super().__init__(player_name=name, auto_rounds=rounds)

    def play_round(self, tcp_socket):
        """
        Play a single round using DumbHand for player value decisions.

        Key behavior:
        - Receives server payloads (cards/results).
        - Tracks player's hand using DumbHand (Ace=11 always).
        - Uses a simple strategy:
            HIT while value < 17, else STAND.

        Args:
            tcp_socket (socket.socket): TCP socket connected to the server.

        Returns:
            int: Round result (RESULT_WIN / RESULT_LOSS / RESULT_TIE).
        """
        cards_received = 0
        my_turn = True
        player_hand = DumbHand()  # <--- The Change

        while True:
            try:
                data = recv_exact(tcp_socket, SIZE_PAYLOAD_SERVER)
            except:
                raise Exception("Server disconnected")

            payload = unpack_payload_server(data)
            if not payload:
                continue
            result, rank, suit = payload

            # Track received cards:
            # - first 2 cards are player's
            # - 3rd is dealer upcard
            # - subsequent cards may be player or dealer depending on turn
            if rank != 0:
                card = Card(rank, suit)
                if cards_received < 2:
                    player_hand.add_card(card)
                elif cards_received == 2:
                    pass  # dealer upcard
                else:
                    if my_turn:
                        player_hand.add_card(card)
                cards_received += 1

            # Non-zero result means game ended
            if result != 0:
                return result

            # After initial deal, make decisions during player's turn
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
    """
    Server variant that uses DumbHand for both player and dealer.

    Purpose:
    - Simulates a server with different Ace logic while maintaining the same
      protocol format, so the smart client must still handle the flow correctly.
    """

    def play_round(self, client_socket):
        """
        Play a single server-side round using DumbHand.

        Key behavior:
        - Deals cards using Deck.
        - Evaluates hands using DumbHand (Ace=11 always).
        - Communicates with client using the same payload protocol.

        Args:
            client_socket (socket.socket): The connected client's TCP socket.
        """
        deck = Deck()
        player_hand = DumbHand()  # <--- The Change
        dealer_hand = DumbHand()  # <--- The Change

        # Initial deal (send 3 cards to client, keep 4th dealer card hidden)
        c1 = deck.deal_card()
        player_hand.add_card(c1)
        self.send_card(client_socket, c1, RESULT_CONTINUE)
        c2 = deck.deal_card()
        player_hand.add_card(c2)
        self.send_card(client_socket, c2, RESULT_CONTINUE)
        d1 = deck.deal_card()
        dealer_hand.add_card(d1)
        self.send_card(client_socket, d1, RESULT_CONTINUE)
        d2 = deck.deal_card()
        dealer_hand.add_card(d2)

        # Player turn: receive HIT/STAND decisions from client
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

        if player_busted:
            return

        # Dealer turn: reveal hidden card then draw to 17+
        self.send_card(client_socket, d2, RESULT_CONTINUE)
        while dealer_hand.calculate_value() < 17:
            new_card = deck.deal_card()
            dealer_hand.add_card(new_card)
            if dealer_hand.calculate_value() > 21:
                self.send_card(client_socket, new_card, RESULT_WIN)
                return
            else:
                self.send_card(client_socket, new_card, RESULT_CONTINUE)

        # Decide winner and send final result
        p_val = player_hand.calculate_value()
        d_val = dealer_hand.calculate_value()
        if p_val > d_val:
            res = RESULT_WIN
        elif d_val > p_val:
            res = RESULT_LOSS
        else:
            res = RESULT_TIE
        self.send_result(client_socket, res)


# --- Test Runner ---


def test_smart_server_dumb_client():
    """
    Compatibility Test 1:
    Smart server (project Server) vs Dumb client (Ace=11 always).

    Goal:
    - Ensure that the dumb client can still complete games against the smart server
      without protocol errors or crashes.
    """
    print("\n>>> TEST 1: Smart Server (Yours) vs Dumb Client (Ace=11) <<<")
    server = Server()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(1)

    client = DumbClient("DumbClient", 2)
    client.start()
    print(">>> TEST 1 PASSED (Game finished without crash) <<<")


def test_dumb_server_smart_client():
    """
    Compatibility Test 2:
    Dumb server (Ace=11 always) vs Smart client (project Client).

    Goal:
    - Ensure the normal client can handle a server with different internal logic
      and still complete games without crashing.
    - This test is time-bounded; it should not run forever.
    """
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
        # Run sequentially
        test_smart_server_dumb_client()

        # Small gap to reduce port/OS cleanup collisions
        time.sleep(2)
        test_dumb_server_smart_client()
    except KeyboardInterrupt:
        pass
