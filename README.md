# Blackijecky ♠️♥️♣️♦️

Blackijecky is a robust, multiplayer network implementation of the classic Blackjack card game, featuring auto-discovery and a custom binary protocol.

## Description
This project implements a complete Client-Server architecture for playing Blackjack over a network. It uses UDP broadcasting for server discovery and TCP for reliable game state management. The system supports multiple concurrent clients and allows players to choose between an interactive **Manual Mode** (CLI-based) or a logic-driven **Automated Mode** for testing strategies.

### Key Features
*   **Auto-Discovery:** Servers broadcast "Offer" messages via UDP; clients automatically detect and connect.
*   **Custom Binary Protocol:** Highly efficient, packed binary messages (using `struct`) for all game communication.
*   **Multiplayer Support:** Threaded server architecture handles multiple game sessions simultaneously.
*   **Dual Client Modes:** Play manually via the terminal or run automated bot simulations.
*   **Robust Game Logic:** Full Blackjack rules implementation including Ace handling (Soft/Hard values) and Dealer logic.
*   **Zero Dependencies:** Built entirely with the Python Standard Library.

## Table of Contents
- [Blackijecky ♠️♥️♣️♦️](#blackijecky-️️️️)
  - [Description](#description)
    - [Key Features](#key-features)
  - [Table of Contents](#table-of-contents)
  - [Quickstart](#quickstart)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Project](#running-the-project)
    - [1. Start the Server](#1-start-the-server)
    - [2. Start the Client](#2-start-the-client)
  - [Usage](#usage)
    - [Interactive Session Example](#interactive-session-example)
    - [Modes](#modes)
  - [Project Architecture](#project-architecture)
    - [Communication Flow](#communication-flow)
    - [Directory Structure](#directory-structure)
  - [Testing](#testing)
  - [Troubleshooting](#troubleshooting)
  - [Submitters](#submitters)

## Quickstart
Open two terminal windows:

**Terminal 1 (Server):**
```bash
python -m src.server
```

**Terminal 2 (Client):**
```bash
python -m src.client
# Follow the prompts to select Manual/Auto mode and number of rounds.
```

## Prerequisites
*   **Python 3.6+**

## Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Blackijecky.git
    cd Blackijecky
    ```
2.  **No external dependencies:**
    This project uses strictly the Python Standard Library (`socket`, `threading`, `struct`, `random`, `time`). No `pip install` is required.

## Configuration
All network and game constants are defined in [src/consts.py](src/consts.py).

| Constant | Value | Description |
| :--- | :--- | :--- |
| **UDP Port** | `13122` | Port used for server broadcasts and client listening. |
| **Magic Cookie** | `0xabcddcba` | 4-byte verification code at start of all messages. |
| **Broadcast IP** | `<broadcast>` | Server broadcasts to all local network devices. |
| **Decision Timeout** | `60.0s` | Time a player has to Hit or Stand. |

## Running the Project

### 1. Start the Server
The server must be running to broadcast offers. It prints its IP and waiting status.
```bash
python -m src.server
```

### 2. Start the Client
You can run as many clients as you want in separate terminals.
```bash
python -m src.client
```

## Usage

When you start the Client, you will be prompted to configure your session **before** looking for a server.

### Interactive Session Example
```text
Client started, listening for offer requests...
Do you want to play manually? (y/n) y
How many rounds do you want to play? 3
Enter bet amount per round ($): 100
```
*The client will then listen for the UDP broadcast, connect to the server, and start the game.*

### Modes
*   **Manual Mode (y):** You will be asked to type `h` (Hit) or `s` (Stand) during the game.
*   **Automated Mode (n):** The client uses a basic heuristic (Hit on <17, Stand on >=17) to play the specified number of rounds automatically.

## Project Architecture

### Communication Flow
The system uses unique message types for each phase:

1.  **Discovery (UDP)**
    *   **Server** works as a broadcaster: Sends `MSG_TYPE_OFFER` (Type 0x2) every 1 second.
    *   **Client** works as a listener: Binds to UDP port 13122 to receive offers.

2.  **Session (TCP)**
    *   Upon receiving an offer, Client opens a TCP connection to the port specified in the offer.
    *   **Client** sends `MSG_TYPE_REQUEST` (Type 0x3) with player name.
    *   **Server** spawns a dedicated thread for the client.

3.  **Gameplay (TCP)**
    *   **Server** sends `MSG_TYPE_PAYLOAD` (Type 0x4) with game results or card data.
    *   **Client** responds with `Hittt` (Hit) or `Stand` payloads.

### Directory Structure
```
Blackijecky/
├── src/
│   ├── server.py       # UDP Broadcaster & TCP Request Handler
│   ├── client.py       # UDP Listener & Game Loop implementation
│   ├── protocol.py     # Binary packet packing/unpacking (struct)
│   ├── game_logic.py   # Deck, Hand, and Card classes
│   └── consts.py       # Configuration & Constants
├── tests/              # Unit tests
└── README.md
```

## Testing
The project includes a comprehensive `unittest` suite.

**Run all tests:**
```bash
python -m unittest discover tests
```

**Run specific test modules:**
```bash
python -m unittest tests.test_protocol
python -m unittest tests.test_game
```

## Troubleshooting

| Issue | Possible Cause | Solution |
| :--- | :--- | :--- |
| **Client waiting endlessly** | Server not running or blocked firewall. | Ensure Server is running. Allow UDP port 13122 on firewall. |
| **Address in use error** | Server/Client already running. | Kill orphan python processes or wait for socket timeout. |
| **"Message format errors"** | Protocol mismatch. | Ensure both Client and Server use the same `src/protocol.py` logic. |

## Submitters
*   **Yali Katz**
*   **Amit Dvash**
