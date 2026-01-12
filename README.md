# Blackijecky

## Project Description
Blackijecky is a robust, multiplayer network implementation of the classic Blackjack card game. Built with Python, it utilizes a client-server architecture with UDP broadcasting for server discovery and TCP for reliable game state management.

## Submitters
*   **Yali Katz**
*   **Amit Dvash**

## Features
- **Auto-Discovery:** Servers broadcast their availability over UDP; clients automatically find and connect to the server.
- **Binary Protocol:** Custom, efficient binary protocol for all network communication (msg packing/unpacking).
- **Multiplayer Support:** The server handles multiple clients concurrently using threading.
- **Robust Game Logic:** Full implementation of Blackjack rules including Ace value adjustment (1 or 11) and dealer strategies.
- **Interactive & Auto Modes:** Clients can play manually via CLI or run an automated strategy for testing.

## Project Structure
```
Blackijecky/
├── src/
│   ├── server.py       # Main server application (UDP broadcast & TCP handling)
│   ├── client.py       # Main client application (UDP listening & Game loop)
│   ├── protocol.py     # Binary protocol definition (Byte packing/unpacking)
│   ├── game_logic.py   # Core logic: Card, Deck, and Hand classes
│   ├── consts.py       # Shared constants (Ports, Magic Cookies, Message Types)
│   └── __init__.py
├── tests/              # Test suite covering logic, connectivity, and protocol
│   ├── test_game.py
│   ├── test_protocol.py
│   ├── test_connection.py
│   └── ...
└── README.md
```

## Requirements
- **Python 3.x**
- **No external dependencies.** This project uses only the Python standard library (`socket`, `threading`, `struct`, `random`, etc.).

## How to Run

### 1. Start the Server
The server must be running first to broadcast its existence.
```bash
python -m src.server
```
*The server will begin broadcasting offers on UDP port 13122 and listen for TCP connections.*

### 2. Start the Client
Run the client in a separate terminal window. You can run multiple clients simultaneously.
```bash
python -m src.client
```
*The client will listen for the server's UDP broadcast, connect, and ask if you want to play manually or set a number of automated rounds.*

## Configuration
Key constants are defined in `src/consts.py`:
- **Broadcast Port:** `13122` (UDP)
- **Magic Cookie:** `0xabcddcba` (Protocol validation)
- **Timeouts:** Connection and decision timeouts are configurable.

## Architecture & Protocol
The system uses a two-phase connection process:
1.  **Discovery (UDP)**: The server broadcasts an **Offer** message containing its TCP listening port.
2.  **Game Session (TCP)**: The client connects to the specific TCP port to initiate a request.

**Message Types:**
*   **Offer (UDP):** Server announces existence.
*   **Request (TCP):** Client asks to start a game.
*   **Payload (TCP):** 
    *   **Server -> Client:** Packet containing Game Result (Win/Loss/Continue), Card Data (Rank/Suit).
    *   **Client -> Server:** Packet containing Game Decision (Hit/Stand).

## Game Rules
- **Objective:** Beat the dealer's hand without exceeding 21.
- **Card Values:** 
    - Number cards (2-10): Face value.
    - Face cards (Jack, Queen, King): 10.
    - Ace: 1 or 11 (automatically calculated to benefit the hand).
- **Dealer Logic:** The dealer **must hit** on any total less than 17 and **stands** on 17 or higher.
- **Winning:** High score wins. Ties are possible. Bust (over 21) results in an immediate loss.

## Testing
The project includes a comprehensive test suite in the `tests/` directory.

To run all tests (using `unittest`):
```bash
python -m unittest discover tests
```

### Test Files Overview:
- `test_game.py`: Validates card dealing, hand calculation, and deck shuffling.
- `test_protocol.py`: Checks correct packing/unpacking of binary messages.
- `test_connection.py`: Tests basic client-server socket establishment.
- `test_ace_compatibility.py`: specifically tests edge cases with Ace values (e.g. A, A, 9 -> 21).
- `test_robustness.py` & `test_manual_mode.py`: Verify system stability against bad inputs and different run modes.
