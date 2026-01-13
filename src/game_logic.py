"""
src/game_logic.py

Overview
--------
Implements the core Blackjack domain model and rules.
This module is pure python and has no networking dependencies.

This module is responsible for:
- Defining the `Card` entity (Rank/Suit).
- Managing the `Deck` (shuffling, dealing).
- Managing the `Hand` (calculating value, handling soft/hard Aces).

How it fits in the system
-------------------------
- Used by `server.py` to run the game state (deal cards, check winners).
- Used by `client.py` to track the player's own hand locally for display and decision making/strategies.
- Dependencies: `src.consts` for rank/suit definitions.

Notes:
------
- Ace handling logic is encapsulated in `Hand.calculate_value`.
- This is the "source of truth" for game rules (deck composition, card values).
"""

import random
from typing import List, Optional
from src.consts import (
    RANK_ACE,
    RANK_JACK,
    RANK_QUEEN,
    RANK_KING,
    SUIT_HEARTS,
    SUIT_DIAMONDS,
    SUIT_CLUBS,
    SUIT_SPADES,
    RANK_MAP,
    SUIT_MAP,
)


class Card:
    """
    Represents a single playing card in the deck.

    Responsibilities
    ----------------
    - Stores rank and suit information.
    - calulates its own Blackjack point value.
    - String representation for UI.

    Key attributes
    --------------
    - self.rank: int (1-13)
    - self.suit: int (0-3)

    Notes:
        - Ace is stored as rank 1. Its ambiguous value (1 or 11) is handled by the Hand class,
          but `get_value()` here returns 11 by default.
    """

    def __init__(self, rank: int, suit: int):
        """
        Initialize a card with rank and suit.

        What it does
        ------------
        - Validates rank and suit ranges.
        - Sets instance attributes.

        Args:
            rank (int): 1-13 (1=Ace, 11=Jack, 12=Queen, 13=King).
            suit (int): 0-3 (Hearts, Diamonds, Clubs, Spades).

        Raises:
            ValueError: If rank or suit are out of valid range.

        Notes:
            - Input validation ensures data integrity before game starts.
        """
        if not (1 <= rank <= 13):
            raise ValueError(f"Invalid rank: {rank}")
        if not (0 <= suit <= 3):
            raise ValueError(f"Invalid suit: {suit}")

        self.rank = rank
        self.suit = suit

    def get_value(self) -> int:
        """
        Get the standard Blackjack value of the card.

        What it does
        ------------
        - Maps Face cards (J, Q, K) to 10.
        - Maps Ace to 11 (default).
        - Returns number cards as-is.

        Returns:
            int: The Blackjack value (2-11).

        Notes:
            - Ace logic to reduce 11 -> 1 is NOT here; it is in Hand.calculate_value().
        """
        if self.rank == RANK_ACE:
            return 11
        elif self.rank in (RANK_JACK, RANK_QUEEN, RANK_KING):
            return 10
        else:
            return self.rank

    def __repr__(self) -> str:
        """
        Returns a string representation of the card.

        What it does
        ------------
        - Formats card as 'Rank of Suit' using mapping constants.

        Returns:
            str: The string representation (e.g., "Ace of Spades").
        """
        return f"{RANK_MAP[self.rank]} of {SUIT_MAP[self.suit]}"

    def __eq__(self, other):
        """
        Checks equality with another card.

        What it does
        ------------
        - Compares rank and suit.

        Args:
            other (object): The object to compare with.

        Returns:
            bool: True if rank and suit match, False otherwise.
        """
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit


class Deck:
    """
    Represents a standard 52-card French deck.

    Responsibilities
    ----------------
    - Creating a fresh set of 52 unique cards.
    - Shuffling.
    - Dealing single cards.

    Key attributes
    --------------
    - self.cards: List[Card] - the stack of cards remaining in the deck.

    Notes:
        - Should be re-instantiated or reset for each new round to ensure fairness in this simplified implementation.
    """

    def __init__(self):
        """
        Initializes the deck and resets it.

        What it does
        ------------
        - Creates internal storage.
        - Calls reset() to populate and shuffle.
        """
        self.cards: List[Card] = []
        self.reset()

    def reset(self):
        """
        Refills the deck with 52 cards and shuffles.

        What it does
        ------------
        - Clears existing cards.
        - Generates 13 ranks for each of the 4 suits.
        - Calls shuffle().
        """
        self.cards = []
        for suit in [SUIT_HEARTS, SUIT_DIAMONDS, SUIT_CLUBS, SUIT_SPADES]:
            for rank in range(1, 14):
                self.cards.append(Card(rank, suit))
        self.shuffle()

    def shuffle(self):
        """
        Shuffles the current cards in the deck.

        What it does
        ------------
        - Uses random.shuffle to randomize list order in-place.
        """
        random.shuffle(self.cards)

    def deal_card(self) -> Optional[Card]:
        """
        Removes and returns the top card from the deck.

        What it does
        ------------
        - Pops the last element from the list (top of stack).

        Returns:
            Optional[Card]: The dealt card, or None if the deck is empty.

        Notes:
            - In a standard game with 1 deck, this could return None if > 52 cards needed (unlikely in 1v1).
        """
        if not self.cards:
            return None
        return self.cards.pop()


class Hand:
    """
    Represents a player's or dealer's hand of cards.

    Responsibilities
    ----------------
    - Storing cards received during a round.
    - Calculating the total score with dynamic Ace handling.

    Key attributes
    --------------
    - self.cards: List[Card]

    Notes:
        - The calculate_value() method is crucial for determining win/loss/bust conditions.
    """

    def __init__(self):
        """
        Initializes an empty hand.

        What it does
        ------------
        - Sets self.cards to empty list.
        """
        self.cards: List[Card] = []

    def add_card(self, card: Card):
        """
        Adds a card to the hand.

        Args:
            card (Card): The card to add.
        """
        self.cards.append(card)

    def calculate_value(self) -> int:
        """
        Calculates the best possible Blackjack score for the hand.

        What it does
        ------------
        - Sums up basic values of cards.
        - Identifies how many Aces are present.
        - If total > 21 and Aces are present, converts Aces from 11 to 1 until <= 21 or no Aces left.

        Returns:
            int: The total value of the hand (optimized for the player).

        Notes:
            - This handles "Soft" vs "Hard" hands automatically.
        """
        value = 0
        ace_count = 0

        for card in self.cards:
            val = card.get_value()
            value += val
            if card.rank == RANK_ACE:
                ace_count += 1

        # If we bust and have aces, count them as 1 instead of 11
        while value > 21 and ace_count > 0:
            value -= 10  # Change an Ace from 11 to 1
            ace_count -= 1

        return value

    def __repr__(self) -> str:
        """
        Returns a string representation of the hand.

        Returns:
            str: The string representation including cards and total value.
        """
        return f"Hand({', '.join(str(c) for c in self.cards)}) (Value: {self.calculate_value()})"
