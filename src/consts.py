"""
src/consts.py

Overview
--------
Central repository for all shared constants, configuration values, and protocol definitions.

This module defines:
- Networking parameters (ports, timeouts, buffer sizes).
- Protocol message types and magic cookies.
- Game logic constants (card suits, ranks, results).
- ANSI color codes for terminal output.

How it fits in the system
-------------------------
Imported by almost all other modules (`client`, `server`, `protocol`, `game_logic`) to ensure
consistent configuration and protocol adherence across the distributed system.

Notes:
------
- Changing values here (like MAGIC_COOKIE or port numbers) will break compatibility
  with non-updated clients/servers.
- Timings defined here (OFFER_INTERVAL, SOCKET_TIMEOUT) are critical for network stability.
"""

# Networking Constants
MAGIC_COOKIE = 0xABCDDCBA
CLIENT_UDP_PORT = 13122
BROADCAST_IP = "<broadcast>"
OFFER_INTERVAL = 1.0  # Seconds
BUFFER_SIZE = 1024
SOCKET_TIMEOUT = 10.0  # Short timeout for connection/protocol
SOCKET_TIMEOUT_DECISION = 60.0  # Long timeout for human decisions

# Message Types
MSG_TYPE_OFFER = 0x2
MSG_TYPE_REQUEST = 0x3
MSG_TYPE_PAYLOAD = 0x4

# Payload Constants
PAYLOAD_DECISION_HIT = "Hittt"
PAYLOAD_DECISION_STAND = "Stand"

# Game Result Codes
RESULT_CONTINUE = 0x0
RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3

# Card Suits
SUIT_HEARTS = 0
SUIT_DIAMONDS = 1
SUIT_CLUBS = 2
SUIT_SPADES = 3

SUIT_MAP = {
    SUIT_HEARTS: "Hearts",
    SUIT_DIAMONDS: "Diamonds",
    SUIT_CLUBS: "Clubs",
    SUIT_SPADES: "Spades",
}

# Card Ranks
RANK_ACE = 1
RANK_JACK = 11
RANK_QUEEN = 12
RANK_KING = 13

RANK_MAP = {
    1: "Ace",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "Jack",
    12: "Queen",
    13: "King",
}


# ANSI Colors
class Colors:
    """
    ANSI escape sequences for terminal output coloring.

    Responsibilities
    ----------------
    - Provides standard colors for console logging and UI elements.
    - Used to highlight errors, success messages, and headers.

    Key attributes
    --------------
    - HEADER: Purple/Magenta for section headers.
    - OKGREEN/OKBLUE: Success or info messages.
    - WARNING/FAIL: Alerts and error messages.

    Notes:
        - May not render correctly in all Windows terminals (e.g. cmd.exe without ANSI support enabled),
          though modern Windows Terminal and VS Code/Pycharm consoles support them.
    """

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
