import socket
import threading
import time
import struct
from src.server import Server
from src.protocol import unpack_offer, pack_request, unpack_payload_server, pack_payload_client, SIZE_PAYLOAD_SERVER
from src.consts import CLIENT_UDP_PORT, PAYLOAD_DECISION_STAND, PAYLOAD_DECISION_HIT

def recv_exact(sock, size):
    buf = b''
    while len(buf) < size:
        data = sock.recv(size - len(buf))
        if not data:
            raise Exception("Connection closed")
        buf += data
    return buf

def test_game_session():
    # Start Server
    server = Server()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    time.sleep(1)
    
    # Client Setup
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', CLIENT_UDP_PORT))
    
    print("Bot Client listening...")
    
    # Discovery
    data, addr = udp_socket.recvfrom(1024)
    server_ip = addr[0]
    result = unpack_offer(data)
    
    if result:
        server_port, server_name = result
        print(f"Found server: {server_name}")
        
        # Connect
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((server_ip, server_port))
        
        # Request 1 Round
        tcp_socket.sendall(pack_request(1, "BotTeam"))
        
        # Game Loop
        cards_received = 0
        my_turn = True
        
        while True:
            try:
                data = recv_exact(tcp_socket, SIZE_PAYLOAD_SERVER)
            except Exception:
                break
                
            payload = unpack_payload_server(data)
            if not payload: continue
            
            result, rank, suit = payload
            print(f"Recv: Res={result}, Card={rank}/{suit}")
            
            if rank != 0:
                cards_received += 1
                
            if result != 0:
                print(f"Game Over. Result: {result}")
                break
            
            # Strategy: Always Stand after initial deal
            if cards_received >= 3 and my_turn:
                print("Bot decides to STAND")
                tcp_socket.sendall(pack_payload_client(PAYLOAD_DECISION_STAND))
                my_turn = False

        tcp_socket.close()
        print("Test Passed!")
    
    server.running = False

if __name__ == "__main__":
    test_game_session()
