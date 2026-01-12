"""
Shared constants for the Blackijecky application.
"""

# Networking Constants
MAGIC_COOKIE = 0xabcddcba
CLIENT_UDP_PORT = 13122
BROADCAST_IP = '<broadcast>'
OFFER_INTERVAL = 1.0  # Seconds
BUFFER_SIZE = 1024
SOCKET_TIMEOUT = 10.0 # Short timeout for connection/protocol
SOCKET_TIMEOUT_DECISION = 60.0 # Long timeout for human decisions

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
    SUIT_HEARTS: 'Hearts',
    SUIT_DIAMONDS: 'Diamonds',
    SUIT_CLUBS: 'Clubs',
    SUIT_SPADES: 'Spades'
}

# Card Ranks
RANK_ACE = 1
RANK_JACK = 11
RANK_QUEEN = 12
RANK_KING = 13

RANK_MAP = {
    1: 'Ace',
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
    11: 'Jack',
    12: 'Queen',
    13: 'King'
}

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

