"""Kuhn poker: the smallest interesting imperfect-information poker game.

Rules (2 players, each antes 1 chip):
  * Deck is 3 cards -- Jack(0), Queen(1), King(2). Each player gets one.
  * Player 0 acts first. Two actions: PASS (check/fold) or BET (bet/call).
  * Betting sequences and payoffs (net chips to player 0):
        pp     showdown for the antes           +/-1
        bp     P1 folds to P0's bet             +1
        bb     showdown for ante+bet            +/-2
        pbp    P0 folds to P1's bet             -1
        pbb    showdown for ante+bet            +/-2

There are exactly 12 information sets (3 cards x {"", "p", "b", "pb"}). The game
has a closed-form solution: value to player 0 is exactly -1/18, and the Nash
equilibria form a one-parameter alpha-family (bet the Jack with prob alpha, the
King with prob 3*alpha). We use those facts as ground-truth correctness checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import Game

PASS, BET = 0, 1
_RANK_CHR = "JQK"
_ACT_CHR = {PASS: "p", BET: "b"}

# Terminal betting histories (as action tuples).
_TERMINALS = {
    (PASS, PASS),
    (BET, PASS),
    (BET, BET),
    (PASS, BET, PASS),
    (PASS, BET, BET),
}


@dataclass(frozen=True)
class KuhnState:
    cards: tuple  # () before the deal, else (p0_card, p1_card)
    history: tuple = ()  # betting actions after the deal


class KuhnPoker(Game):
    name = "kuhn"
    num_actions = 2

    # Ordered deals of two distinct cards from {0,1,2}: 6 equally likely outcomes.
    _DEALS = [(i, j) for i in range(3) for j in range(3) if i != j]

    def initial_state(self):
        return KuhnState(cards=(), history=())

    def is_chance(self, state) -> bool:
        return len(state.cards) == 0

    def is_terminal(self, state) -> bool:
        return len(state.cards) == 2 and state.history in _TERMINALS

    def current_player(self, state) -> int:
        return len(state.history) % 2

    def legal_actions(self, state):
        return [PASS, BET]

    def is_facing_bet(self, state) -> bool:
        """True if the acting player must answer an outstanding bet (so PASS
        means fold rather than check)."""
        return len(state.history) > 0 and state.history[-1] == BET

    def chance_outcomes(self, state):
        p = 1.0 / len(self._DEALS)
        return [(k, p) for k in range(len(self._DEALS))]

    def apply_action(self, state, action):
        if len(state.cards) == 0:  # chance: deal
            return KuhnState(cards=self._DEALS[action], history=())
        return KuhnState(cards=state.cards, history=state.history + (action,))

    def infoset_key(self, state):
        player = len(state.history) % 2
        card = _RANK_CHR[state.cards[player]]
        hist = "".join(_ACT_CHR[a] for a in state.history)
        return f"{card}:{hist}"

    def terminal_utility(self, state) -> float:
        h = state.history
        p0, p1 = state.cards
        winner_sign = 1.0 if p0 > p1 else -1.0  # cards always distinct
        if h == (PASS, PASS):
            return winner_sign * 1.0
        if h == (BET, BET) or h == (PASS, BET, BET):
            return winner_sign * 2.0
        if h == (BET, PASS):
            return 1.0  # P1 folded, P0 wins P1's ante
        if h == (PASS, BET, PASS):
            return -1.0  # P0 folded, loses its ante
        raise ValueError(f"terminal_utility on non-terminal history {h!r}")
