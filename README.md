# Blackijecky

## Project Description
Blackijecky is a multiplayer Blackjack game designed with a client-server architecture. The server broadcasts its availability via UDP, and clients connect via TCP to play the game. The project implements a custom binary protocol for efficient communication and handles standard Blackjack rules including card dealing, hit/stand decisions, and win/loss/tie calculations.

## Submitters
*   **Yali Katz**
*   **Amit Dvash**

## Project Structure
The project is organized into the following modules:

*   `src/server.py`: The server application. It broadcasts offers on UDP port 13122 and handles incoming TCP connections from clients. It manages the game state for each client in a separate thread.
*   `src/client.py`: The client application. It listens for UDP offers, connects to the server, and allows the user to play the specified number of rounds.
*   `src/protocol.py`: Defines the binary protocol used for communication, including message packing and unpacking (Offer, Request, Payload).
*   `src/game_logic.py`: Contains the core game logic, including `Card`, `Deck`, and `Hand` classes.
*   `src/consts.py`: Shared constants such as ports, message types, and game parameters.

## How to Run

### Prerequisites
*   Python 3.x

### Running the Server
1.  Navigate to the project root directory.
2.  Run the server:
    ```bash
    python -m src.server
    ```
    The server will start broadcasting offers and listening for connections.

### Running the Client
1.  Navigate to the project root directory.
2.  Run the client:
    ```bash
    python -m src.client
    ```
3.  Follow the on-screen prompts to enter the number of rounds you wish to play.

## Protocol Details
The communication relies on a custom binary protocol:
*   **Offer Message:** Broadcasted by the server to announce its presence.
*   **Request Message:** Sent by the client to initiate a game session.
*   **Payload Message:** Used for exchanging game moves (Hit/Stand) and game state updates (cards dealt, game results).

## Testing
The project includes a suite of tests in the `tests/` directory to ensure reliability and correctness:
*   `test_game.py`: Tests the core game logic.
*   `test_protocol.py`: Validates the binary protocol packing and unpacking.
*   `test_connection.py`: Checks client-server connectivity.
*   `test_multiclient.py`: Verifies the server's ability to handle multiple clients simultaneously.
*   `test_robustness.py`: Tests the system's resilience against invalid inputs and connection issues.
*   `test_ace_compatibility.py`: Ensures correct handling of Ace values (1 vs 11) in various game scenarios.
