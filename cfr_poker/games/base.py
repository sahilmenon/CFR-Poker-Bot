"""Abstract extensive-form game interface.

Every game is a two-player, zero-sum, imperfect-information extensive-form
game. Utilities are always reported from **player 0's** perspective; player 1's
utility is the negation (zero-sum).

The interface is deliberately small so that a single CFR solver and a single
best-response evaluator can run on *any* game that implements it. States are
opaque, immutable, hashable objects owned by the concrete game.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Hashable, Sequence


class Game(ABC):
    """A two-player zero-sum extensive-form game.

    Action ids are integers in ``range(num_actions)`` forming a *global* action
    space; ``legal_actions`` restricts which are available at a given state.
    Using a fixed global space lets solvers index regret/strategy arrays by
    action id without per-node bookkeeping.
    """

    name: str = "game"
    num_actions: int = 0

    @abstractmethod
    def initial_state(self):
        """Return the root state (a chance node that deals the cards)."""

    @abstractmethod
    def is_terminal(self, state) -> bool:
        ...

    @abstractmethod
    def is_chance(self, state) -> bool:
        """True at nodes where nature moves (dealing, revealing the board)."""

    @abstractmethod
    def current_player(self, state) -> int:
        """Acting player (0 or 1). Only defined at non-terminal, non-chance nodes."""

    @abstractmethod
    def legal_actions(self, state) -> Sequence[int]:
        ...

    @abstractmethod
    def chance_outcomes(self, state) -> Sequence[tuple[int, float]]:
        """List of ``(action_id, probability)`` for a chance node."""

    @abstractmethod
    def apply_action(self, state, action: int):
        """Return the successor state after ``action`` (player or chance)."""

    @abstractmethod
    def infoset_key(self, state) -> Hashable:
        """Information-set key for the acting player: everything they can observe."""

    @abstractmethod
    def terminal_utility(self, state) -> float:
        """Payoff to **player 0** at a terminal state (chips, zero-sum)."""
