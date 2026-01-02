import unittest
import struct
from src import protocol
from src.consts import MAGIC_COOKIE, MSG_TYPE_OFFER

class TestProtocol(unittest.TestCase):

    def test_offer(self):
        port = 12345
        name = "Test Server"
        packed = protocol.pack_offer(port, name)
        unpacked = protocol.unpack_offer(packed)
        
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked[0], port)
        self.assertEqual(unpacked[1], name)

    def test_offer_long_name(self):
        port = 12345
        name = "This name is definitely longer than thirty-two bytes"
        packed = protocol.pack_offer(port, name)
        unpacked = protocol.unpack_offer(packed)
        
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked[0], port)
        self.assertEqual(len(unpacked[1].encode('utf-8')), 32)
        self.assertTrue(name.startswith(unpacked[1]))

    def test_request(self):
        rounds = 5
        name = "Team Rocket"
        packed = protocol.pack_request(rounds, name)
        unpacked = protocol.unpack_request(packed)
        
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked[0], rounds)
        self.assertEqual(unpacked[1], name)

    def test_payload_client(self):
        decision = "Hittt"
        packed = protocol.pack_payload_client(decision)
        unpacked = protocol.unpack_payload_client(packed)
        
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked, decision)

    def test_payload_server(self):
        result = 1
        rank = 13
        suit = 2
        packed = protocol.pack_payload_server(result, rank, suit)
        unpacked = protocol.unpack_payload_server(packed)
        
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked, (result, rank, suit))

    def test_invalid_magic(self):
        # Create a fake packet with wrong magic cookie
        # Offer: Magic(4) | Type(1) | Port(2) | Name(32)
        fake_magic = 0xdeadbeef
        data = struct.pack('!IBH32s', fake_magic, MSG_TYPE_OFFER, 1234, b'test')
        
        self.assertIsNone(protocol.unpack_offer(data))

    def test_invalid_type(self):
        # Create a fake packet with wrong type (e.g. Request type but trying to unpack as Offer)
        # Request structure is different, so let's just use Offer structure but wrong type ID
        wrong_type = 0x99
        data = struct.pack('!IBH32s', MAGIC_COOKIE, wrong_type, 1234, b'test')
        
        self.assertIsNone(protocol.unpack_offer(data))

if __name__ == '__main__':
    unittest.main()
