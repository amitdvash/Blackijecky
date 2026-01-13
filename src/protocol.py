"""
src/protocol.py

Overview
--------
Implements the binary protocol for Blackijecky message exchange.
Handles low-level packing (serialization) and unpacking (deserialization) of messages
using Python's `struct` module.

This module is responsible for:
- Defining the precise byte structure of Offer, Request, and Payload messages.
- Ensuring network byte order (Big Endian) ! is used.
- Providing helper functions for robust socket reading (`recv_exact`).

How it fits in the system
-------------------------
- Used by `server.py` and `client.py` to communicate.
- Ensures both sides agree on the "language" (binary format) they speak.
- Defines the "wire format" which includes Magic Cookies, Type fields, and fixed-size buffers.

Notes:
------
- All structures are fixed-size for simplicity. Strings are padded with null bytes.
- STRICTLY uses Network Byte Order (`!`).
- The Magic Cookie provides a basic validity check for all messages.
"""

import struct
from typing import Tuple, Optional
from src.consts import MAGIC_COOKIE, MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD

# Struct formats (Network Byte Order !)
# Offer: Magic(4) | Type(1) | Port(2) | Name(32)
FMT_OFFER = "!IBH32s"
SIZE_OFFER = struct.calcsize(FMT_OFFER)

# Request: Magic(4) | Type(1) | NumRounds(1) | Name(32)
FMT_REQUEST = "!IBB32s"
SIZE_REQUEST = struct.calcsize(FMT_REQUEST)

# Payload Client: Magic(4) | Type(1) | Decision(5)
FMT_PAYLOAD_CLIENT = "!IB5s"
SIZE_PAYLOAD_CLIENT = struct.calcsize(FMT_PAYLOAD_CLIENT)

# Payload Server: Magic(4) | Type(1) | Result(1) | Rank(2) | Suit(1)
FMT_PAYLOAD_SERVER = "!IBBHB"
SIZE_PAYLOAD_SERVER = struct.calcsize(FMT_PAYLOAD_SERVER)


def _pad_string(text: str, length: int) -> bytes:
    """
    Encodes string to bytes, truncates or pads with null bytes.

    What it does
    ------------
    - Ensures string fits exactly into the fixed-size structure field.

    Args:
        text (str): The string to encode.
        length (int): The target length of the byte string.

    Returns:
        bytes: The encoded and padded/truncated byte string.
    """
    encoded = text.encode("utf-8")
    if len(encoded) > length:
        return encoded[:length]
    return encoded.ljust(length, b"\x00")


def _decode_string(data: bytes) -> str:
    """
    Decodes bytes to string, stripping null padding.

    What it does
    ------------
    - Recovers a clean python string from the fixed-size network buffer.

    Args:
        data (bytes): The byte string to decode.

    Returns:
        str: The decoded string.
    """
    return data.decode("utf-8").rstrip("\x00")


def pack_offer(server_port: int, server_name: str) -> bytes:
    """
    Packs an Offer message for UDP broadcast.

    What it does
    ------------
    - Serializes magic cookie, message type (0x02), server port, and name.

    Args:
        server_port (int): The TCP port the server is listening on.
        server_name (str): The name of the server (max 32 chars).

    Returns:
        bytes: The packed binary message ready for UDP broadcast.
    """
    name_bytes = _pad_string(server_name, 32)
    return struct.pack(FMT_OFFER, MAGIC_COOKIE, MSG_TYPE_OFFER, server_port, name_bytes)


def unpack_offer(data: bytes) -> Optional[Tuple[int, str]]:
    """
    Unpacks an Offer message.

    What it does
    ------------
    - Validates message size, magic cookie, and message type.
    - Extracts server port and name.

    Args:
        data (bytes): The binary data received (UDP).

    Returns:
        Optional[Tuple[int, str]]: A tuple containing (server_port, server_name), or None if invalid.

    Notes:
        - Used by Client to discover Server.
    """
    try:
        if len(data) != struct.calcsize(FMT_OFFER):
            return None

        magic, msg_type, port, name_bytes = struct.unpack(FMT_OFFER, data)

        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_OFFER:
            return None

        return port, _decode_string(name_bytes)
    except struct.error:
        return None


def pack_request(num_rounds: int, team_name: str) -> bytes:
    """
    Packs a Request message to initiate a game session.

    What it does
    ------------
    - Serializes magic cookie, message type (0x03), number of rounds, and team name.

    Args:
        num_rounds (int): The number of rounds to play.
        team_name (str): The name of the client team.

    Returns:
        bytes: The packed binary message.
    """
    name_bytes = _pad_string(team_name, 32)
    return struct.pack(
        FMT_REQUEST, MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds, name_bytes
    )


def unpack_request(data: bytes) -> Optional[Tuple[int, str]]:
    """
    Unpacks a Request message from a client.

    What it does
    ------------
    - Validates structure and magic cookie.
    - Extracts number of rounds and team name.

    Args:
        data (bytes): The binary data received.

    Returns:
        Optional[Tuple[int, str]]: A tuple containing (num_rounds, team_name), or None if invalid.
    """
    try:
        if len(data) != struct.calcsize(FMT_REQUEST):
            return None

        magic, msg_type, num_rounds, name_bytes = struct.unpack(FMT_REQUEST, data)

        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_REQUEST:
            return None

        return num_rounds, _decode_string(name_bytes)
    except struct.error:
        return None


def pack_payload_client(decision: str) -> bytes:
    """
    Packs a Client Payload message (Game Decision).

    What it does
    ------------
    - Serializes client's move (e.g. "Hittt" or "Stand") into payload format.

    Args:
        decision (str): The player's decision string.

    Returns:
        bytes: The packed binary message.
    """
    # Decision should be "Hittt" or "Stand"
    decision_bytes = _pad_string(decision, 5)  # "Hittt" is 5 chars, "Stand" is 5 chars
    return struct.pack(
        FMT_PAYLOAD_CLIENT, MAGIC_COOKIE, MSG_TYPE_PAYLOAD, decision_bytes
    )


def unpack_payload_client(data: bytes) -> Optional[str]:
    """
    Unpacks a Client Payload message (Game Decision).

    What it does
    ------------
    - Extracts the player's decision string.

    Args:
        data (bytes): The binary data received.

    Returns:
        Optional[str]: The decision string (e.g. "Hittt"), or None if invalid.
    """
    try:
        if len(data) != struct.calcsize(FMT_PAYLOAD_CLIENT):
            return None

        magic, msg_type, decision_bytes = struct.unpack(FMT_PAYLOAD_CLIENT, data)

        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None

        return _decode_string(decision_bytes)
    except struct.error:
        return None


def pack_payload_server(result: int, rank: int, suit: int) -> bytes:
    """
    Packs a Server Payload message (Game State Update).

    What it does
    ------------
    - Serializes the result of an action (Win/Loss/Continue) and the associated card (if any).

    Args:
        result (int): The game result code (0=Continue, 1=Tie, 2=Loss, 3=Win).
        rank (int): The card rank (1-13) or 0 if no card.
        suit (int): The card suit (0-3) or 0 if no card.

    Returns:
        bytes: The packed binary message.
    """
    return struct.pack(
        FMT_PAYLOAD_SERVER, MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result, rank, suit
    )


def unpack_payload_server(data: bytes) -> Optional[Tuple[int, int, int]]:
    """
    Unpacks a Server Payload message.

    What it does
    ------------
    - Extracts result code and card details from server response.

    Args:
        data (bytes): The binary data received.

    Returns:
        Optional[Tuple[int, int, int]]: A tuple containing (result, rank, suit), or None if invalid.
    """
    try:
        if len(data) != struct.calcsize(FMT_PAYLOAD_SERVER):
            return None

        magic, msg_type, result, rank, suit = struct.unpack(FMT_PAYLOAD_SERVER, data)

        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None

        return result, rank, suit
    except struct.error:
        return None


def recv_exact(sock, size: int) -> bytes:
    """
    Reliably receives exactly `size` bytes from a TCP socket.

    What it does
    ------------
    - Loops (blocks) until 'size' bytes are accumulated.
    - Prevents partial read errors common in TCP networking.

    Args:
        sock (socket.socket): The TCP socket.
        size (int): The exact number of bytes expected.

    Returns:
        bytes: The complete data buffer.

    Raises:
        Exception: If connection is closed (EOF) before receiving all bytes.

    Notes:
        - Critical for our fixed-size binary protocol.
    """
    buf = b""
    while len(buf) < size:
        data = sock.recv(size - len(buf))
        if not data:
            raise Exception("Connection closed")
        buf += data
    return buf
