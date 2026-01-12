"""
tests/test_manual_mode.py

Overview
--------
Unit tests for the Client "manual mode" decision flow.

These tests validate that when the Client is in manual_mode:
- It prompts the user for input ('h' for hit, 's' for stand).
- It sends the correct decision payloads to the server socket.
- It handles invalid inputs by retrying until a valid choice is given.

The tests mock:
- builtins.input() to simulate user typing.
- a TCP socket to simulate server payloads and capture what the client sends.

How to run:
-----------
    python -m tests.test_manual_mode
(or)
    python tests/test_manual_mode.py
"""

import unittest
from unittest.mock import MagicMock, patch
from src.client import Client
from src.protocol import pack_payload_server, unpack_payload_client
from src.consts import PAYLOAD_DECISION_HIT, PAYLOAD_DECISION_STAND, RESULT_WIN


class TestManualMode(unittest.TestCase):
    """
    Tests the client's manual decision-making during a round.

    Focus:
    - Correctly reading user input in manual mode.
    - Sending HIT / STAND payloads in response.
    - Retrying on invalid inputs.
    """

    def tearDown(self):
        """
        Cleanup hook after each test.

        Currently a no-op, but kept for future extensions
        (e.g., closing sockets, resetting global state).
        """
        pass

    @patch("builtins.input", side_effect=["h", "s"])
    def test_manual_hit_then_stand(self, mock_input):
        """
        Manual flow test: user chooses HIT first, then STAND.

        Setup:
        - Client is created in manual_mode=True.
        - A mock TCP socket is configured to return a fixed sequence of
          server payloads (cards + final result).

        Expectations:
        - play_round returns RESULT_WIN.
        - input() is called exactly twice.
        - exactly two decision payloads are sent to the server:
          1) Hit
          2) Stand
        """
        # Initialize Client in Manual Mode
        client = Client("TestPlayer")
        client.manual_mode = True
        try:
            # Mock Socket
            mock_socket = MagicMock()

            # Helper to pack server payload
            def p(result, rank, suit):
                return pack_payload_server(result, rank, suit)

            # Sequence of data for the client to receive:
            # 1. Card 1 (Player) - 10 Hearts
            # 2. Card 2 (Player) - 5 Diamonds (Value 15)
            # 3. Dealer Card 1 - 5 Clubs
            # --- Client sees 3 cards. It's their turn. Logic triggers. ---
            # --- Mock Input returns 'h' ---
            # --- Client sends HIT ---
            # 4. Card 3 (Player) - 2 Hearts (Value 17 - Safe)
            # --- Client sees response. Still their turn. Logic triggers. ---
            # --- Mock Input returns 's' ---
            # --- Client sends STAND ---
            # 5. Result Packet (WIN)

            data_sequence = [
                p(0, 10, 0),
                p(0, 5, 1),
                p(0, 5, 2),
                p(0, 2, 0),
                p(RESULT_WIN, 0, 0),
            ]

            # Configure the mock socket to return these packets in order
            mock_socket.recv.side_effect = data_sequence

            # Run play_round
            # It handles the loop. It should return RESULT_WIN (3)
            result = client.play_round(mock_socket)

            # 1. Verify the result
            self.assertEqual(result, RESULT_WIN)

            # 2. Verify Input was called exactly twice
            self.assertEqual(mock_input.call_count, 2)

            # 3. Verify exactly two packets were sent
            self.assertEqual(mock_socket.sendall.call_count, 2)

            call_args_list = mock_socket.sendall.call_args_list

            # Check first send (Hit)
            sent_data_1 = call_args_list[0][0][0]
            decision_1 = unpack_payload_client(sent_data_1)
            self.assertEqual(decision_1, "Hittt", "First packet should be Hit")

            # Check second send (Stand)
            sent_data_2 = call_args_list[1][0][0]
            decision_2 = unpack_payload_client(sent_data_2)
            self.assertEqual(decision_2, "Stand", "Second packet should be Stand")

            print("\nTest Manual Mode: Processed Hit/Stand correctly.")
        finally:
            client.udp_socket.close()

    @patch("builtins.input", side_effect=["x", "Invalid", "h", "s"])
    def test_manual_invalid_input_retry(self, mock_input):
        """
        Manual flow test: invalid inputs are retried until valid input is provided.

        Setup:
        - Client is created in manual_mode=True.
        - input() returns two invalid values first ("x", "Invalid"),
          then a valid HIT ("h"), then a valid STAND ("s").
        - Mock socket returns a normal card sequence + WIN at the end.

        Expectations:
        - input() is called 4 times total (2 invalid + 2 valid).
        - The round completes without crashing.
        """
        client = Client("TestPlayer")
        client.manual_mode = True
        try:
            mock_socket = MagicMock()

            # Same sequence as above
            data_sequence = [
                pack_payload_server(0, 10, 0),
                pack_payload_server(0, 5, 1),
                pack_payload_server(0, 5, 2),
                pack_payload_server(0, 2, 0),
                pack_payload_server(RESULT_WIN, 0, 0),
            ]
            mock_socket.recv.side_effect = data_sequence

            # Logic:
            # At first prompt: Input 'x' (Invalid), 'Invalid' (Invalid), 'h' (Valid Hit)
            # At second prompt: Input 's' (Valid Stand)

            client.play_round(mock_socket)

            # Verify call count: 3 bad inputs + 1 good (1st turn) + 1 good (2nd turn) = 5?
            # Wait: side_effect=['x', 'Invalid', 'h', 's']
            # 1. Loop 1: 'x' -> Invalid, continue
            # 2. Loop 1: 'Invalid' -> Invalid, continue
            # 3. Loop 1: 'h' -> Valid, break, send Hit
            # 4. Loop 2: 's' -> Valid, break, send Stand

            self.assertEqual(mock_input.call_count, 4)
            print("\nTest Manual Mode: Handled invalid inputs correctly.")
        finally:
            client.udp_socket.close()


if __name__ == "__main__":
    unittest.main()
