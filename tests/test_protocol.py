"""
tests/test_protocol.py

Overview
--------
Unit tests for the binary protocol implementation in src/protocol.py.

These tests verify that the protocol pack/unpack functions:
- Produce correctly structured binary messages.
- Can round-trip (pack -> unpack) without losing information.
- Correctly enforce validation rules (magic cookie + message type).
- Handle edge cases like overly long server names.

How to run:
-----------
    python -m tests.test_protocol
(or)
    python tests/test_protocol.py
"""

import unittest
import struct
from src import protocol
from src.consts import MAGIC_COOKIE, MSG_TYPE_OFFER


class TestProtocol(unittest.TestCase):
    """
    Tests for message encoding/decoding helpers in src/protocol.py.

    Focus:
    - Offer message: server advertisement (port + name)
    - Request message: client request (rounds + team name)
    - Payload messages: game decisions and server updates
    - Rejection of invalid packets (wrong magic / wrong type)
    """

    def test_offer(self):
        """
        Offer round-trip test (pack -> unpack).

        Verifies that packing an Offer with a given port and name,
        and then unpacking it, returns the same values.
        """
        port = 12345
        name = "Test Server"
        packed = protocol.pack_offer(port, name)
        unpacked = protocol.unpack_offer(packed)

        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked[0], port)
        self.assertEqual(unpacked[1], name)

    def test_offer_long_name(self):
        """
        Offer truncation behavior for long names.

        The Offer message contains a fixed-length name field (32 bytes).
        This test checks that:
        - unpacking still succeeds
        - the decoded name is truncated to 32 bytes (UTF-8)
        - the decoded name matches the prefix of the original long name
        """
        port = 12345
        name = "This name is definitely longer than thirty-two bytes"
        packed = protocol.pack_offer(port, name)
        unpacked = protocol.unpack_offer(packed)

        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked[0], port)
        self.assertEqual(len(unpacked[1].encode("utf-8")), 32)
        self.assertTrue(name.startswith(unpacked[1]))

    def test_request(self):
        """
        Request round-trip test (pack -> unpack).

        Verifies that packing a Request (rounds + team name)
        and then unpacking it returns the same values.
        """
        rounds = 5
        name = "Team Rocket"
        packed = protocol.pack_request(rounds, name)
        unpacked = protocol.unpack_request(packed)

        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked[0], rounds)
        self.assertEqual(unpacked[1], name)

    def test_payload_client(self):
        """
        Client payload round-trip test.

        Verifies that packing a client decision payload and then
        unpacking it returns the same decision string/value.
        """
        decision = "Hittt"
        packed = protocol.pack_payload_client(decision)
        unpacked = protocol.unpack_payload_client(packed)

        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked, decision)

    def test_payload_server(self):
        """
        Server payload round-trip test.

        Verifies that packing a server payload (result, rank, suit)
        and then unpacking it returns the same tuple.
        """
        result = 1
        rank = 13
        suit = 2
        packed = protocol.pack_payload_server(result, rank, suit)
        unpacked = protocol.unpack_payload_server(packed)

        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked, (result, rank, suit))

    def test_invalid_magic(self):
        """
        Validation test: invalid magic cookie must be rejected.

        Creates an Offer-shaped packet but with a wrong magic cookie,
        then ensures unpack_offer returns None.
        """
        fake_magic = 0xDEADBEEF
        data = struct.pack("!IBH32s", fake_magic, MSG_TYPE_OFFER, 1234, b"test")

        self.assertIsNone(protocol.unpack_offer(data))

    def test_invalid_type(self):
        """
        Validation test: invalid message type must be rejected.

        Creates an Offer-shaped packet but with an invalid type ID,
        then ensures unpack_offer returns None.
        """
        wrong_type = 0x99
        data = struct.pack("!IBH32s", MAGIC_COOKIE, wrong_type, 1234, b"test")

        self.assertIsNone(protocol.unpack_offer(data))


if __name__ == "__main__":
    unittest.main()
