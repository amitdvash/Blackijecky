"""
Binary protocol implementation for Blackijecky.
Handles packing and unpacking of messages using struct.
"""

import struct
from typing import Tuple, Optional
from src.consts import (
    MAGIC_COOKIE,
    MSG_TYPE_OFFER,
    MSG_TYPE_REQUEST,
    MSG_TYPE_PAYLOAD
)

# Struct formats (Network Byte Order !)
# Offer: Magic(4) | Type(1) | Port(2) | Name(32)
FMT_OFFER = '!IBH32s'
SIZE_OFFER = struct.calcsize(FMT_OFFER)

# Request: Magic(4) | Type(1) | NumRounds(1) | Name(32)
FMT_REQUEST = '!IBB32s'
SIZE_REQUEST = struct.calcsize(FMT_REQUEST)

# Payload Client: Magic(4) | Type(1) | Decision(5)
FMT_PAYLOAD_CLIENT = '!IB5s'
SIZE_PAYLOAD_CLIENT = struct.calcsize(FMT_PAYLOAD_CLIENT)

# Payload Server: Magic(4) | Type(1) | Result(1) | Rank(2) | Suit(1)
FMT_PAYLOAD_SERVER = '!IBBHB'
SIZE_PAYLOAD_SERVER = struct.calcsize(FMT_PAYLOAD_SERVER)



def _pad_string(text: str, length: int) -> bytes:
    """Encodes string to bytes, truncates or pads with null bytes."""
    encoded = text.encode('utf-8')
    if len(encoded) > length:
        return encoded[:length]
    return encoded.ljust(length, b'\x00')


def _decode_string(data: bytes) -> str:
    """Decodes bytes to string, stripping null padding."""
    return data.decode('utf-8').rstrip('\x00')


def pack_offer(server_port: int, server_name: str) -> bytes:
    """Packs an Offer message."""
    name_bytes = _pad_string(server_name, 32)
    return struct.pack(FMT_OFFER, MAGIC_COOKIE, MSG_TYPE_OFFER, server_port, name_bytes)


def unpack_offer(data: bytes) -> Optional[Tuple[int, str]]:
    """
    Unpacks an Offer message.
    Returns (server_port, server_name) or None if invalid.
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
    """Packs a Request message."""
    name_bytes = _pad_string(team_name, 32)
    return struct.pack(FMT_REQUEST, MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds, name_bytes)


def unpack_request(data: bytes) -> Optional[Tuple[int, str]]:
    """
    Unpacks a Request message.
    Returns (num_rounds, team_name) or None if invalid.
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
    """Packs a Client Payload message (Decision)."""
    # Decision should be "Hittt" or "Stand"
    decision_bytes = _pad_string(decision, 5) # "Hittt" is 5 chars, "Stand" is 5 chars
    return struct.pack(FMT_PAYLOAD_CLIENT, MAGIC_COOKIE, MSG_TYPE_PAYLOAD, decision_bytes)


def unpack_payload_client(data: bytes) -> Optional[str]:
    """
    Unpacks a Client Payload message.
    Returns decision string or None if invalid.
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
    """Packs a Server Payload message (Card + Result)."""
    return struct.pack(FMT_PAYLOAD_SERVER, MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result, rank, suit)


def unpack_payload_server(data: bytes) -> Optional[Tuple[int, int, int]]:
    """
    Unpacks a Server Payload message.
    Returns (result, rank, suit) or None if invalid.
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
    Helper to receive exactly 'size' bytes from a socket.
    Raises Exception if connection is closed before receiving all bytes.
    """
    buf = b''
    while len(buf) < size:
        data = sock.recv(size - len(buf))
        if not data:
            raise Exception("Connection closed")
        buf += data
    return buf

