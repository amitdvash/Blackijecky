"""
Game logic for Blackijecky.
Handles Card, Deck, and Hand classes.
"""

import random
from typing import List, Optional
from src.consts import (
    RANK_ACE, RANK_JACK, RANK_QUEEN, RANK_KING,
    SUIT_HEARTS, SUIT_DIAMONDS, SUIT_CLUBS, SUIT_SPADES,
    RANK_MAP, SUIT_MAP
)

class Card:
    """Represents a single playing card."""
    
    def __init__(self, rank: int, suit: int):
        """
        Initialize a card with rank and suit.
        
        Args:
            rank (int): 1-13 (1=Ace, 11=Jack, 12=Queen, 13=King).
            suit (int): 0-3 (Hearts, Diamonds, Clubs, Spades).

        Raises:
            ValueError: If rank or suit are out of valid range.
        """
        if not (1 <= rank <= 13):
            raise ValueError(f"Invalid rank: {rank}")
        if not (0 <= suit <= 3):
            raise ValueError(f"Invalid suit: {suit}")
            
        self.rank = rank
        self.suit = suit

    def get_value(self) -> int:
        """
        Get the Blackjack value of the card.

        Ace returns 11 (logic to reduce to 1 is in Hand).
        Face cards return 10.
        Number cards return their rank.

        Returns:
            int: The Blackjack value of the card.
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

        Returns:
            str: The string representation (e.g., "Ace of Spades").
        """
        return f"{RANK_MAP[self.rank]} of {SUIT_MAP[self.suit]}"

    def __eq__(self, other):
        """
        Checks equality with another card.

        Args:
            other (object): The object to compare with.

        Returns:
            bool: True if rank and suit match, False otherwise.
        """
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit


class Deck:
    """Represents a standard 52-card deck."""
    
    def __init__(self):
        """Initializes the deck and resets it."""
        self.cards: List[Card] = []
        self.reset()

    def reset(self):
        """Refills the deck with 52 cards and shuffles."""
        self.cards = []
        for suit in [SUIT_HEARTS, SUIT_DIAMONDS, SUIT_CLUBS, SUIT_SPADES]:
            for rank in range(1, 14):
                self.cards.append(Card(rank, suit))
        self.shuffle()

    def shuffle(self):
        """Shuffles the current cards in the deck."""
        random.shuffle(self.cards)

    def deal_card(self) -> Optional[Card]:
        """
        Removes and returns the top card from the deck.

        Returns:
            Optional[Card]: The dealt card, or None if the deck is empty.
        """
        if not self.cards:
            return None
        return self.cards.pop()


class Hand:
    """Represents a player's or dealer's hand of cards."""
    
    def __init__(self):
        """Initializes an empty hand."""
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
        Calculates the total value of the hand.
        Handles Ace logic (11 or 1) to avoid busting if possible.

        Returns:
            int: The total value of the hand.
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
