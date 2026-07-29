"""Leduc Hold'em: the standard mid-size benchmark for CFR.

Rules (2 players, each antes 1 chip):
  * Deck is 6 cards -- two suits x three ranks {J(0), Q(1), K(2)}.
  * Round 0: each player is dealt one private card, then a betting round.
  * A single public "board" card is revealed.
  * Round 1: a second betting round.
  * Showdown: a player who pairs the board wins; otherwise the higher private
    card wins; equal ranks split the pot.

Betting: fixed-limit. Raise size is 2 in round 0 and 4 in round 1; at most two
raises (a bet and a re-raise) per round. Player 0 acts first in both rounds.
Actions are FOLD(0), CALL(1) (== check when nothing to call), RAISE(2) (== bet).

This formulation has exactly 288 information sets, which we assert in the tests
as a structural sanity check. Because the private/board observations plus the
betting history uniquely tag every decision, the info-set key is just that
tuple rendered as a string.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import Game

FOLD, CALL, RAISE = 0, 1, 2
_ACT_CHR = {FOLD: "f", CALL: "c", RAISE: "r"}
_RANK_CHR = "JQK"

ANTE = 1
RAISE_SIZE = (2, 4)  # per round
MAX_RAISES = 2  # per round (a bet plus one re-raise)


@dataclass(frozen=True)
class LeducState:
    private: tuple      # () before deal, else (c0, c1) as physical card ids 0..5
    board: int          # -1 until revealed, else physical card id
    rnd: int            # 0 or 1
    history: tuple      # betting actions in the current round
    r0_history: tuple   # betting actions of round 0 (kept for the round-1 key)
    committed: tuple    # chips each player has put in the pot so far
    terminal: bool = False
    folder: int = -1    # which player folded, or -1


def _rank(card_id: int) -> int:
    return card_id // 2


class LeducPoker(Game):
    name = "leduc"
    num_actions = 3

    # Ordered deals of two distinct physical cards from a 6-card deck.
    _DEALS = [(i, j) for i in range(6) for j in range(6) if i != j]

    def initial_state(self):
        return LeducState(
            private=(), board=-1, rnd=0, history=(), r0_history=(), committed=(ANTE, ANTE)
        )

    # ---- chance / terminal ---------------------------------------------------
    def is_chance(self, state) -> bool:
        if len(state.private) == 0:
            return True  # deal private cards
        return state.rnd == 1 and state.board == -1  # reveal the board card

    def is_terminal(self, state) -> bool:
        return state.terminal

    def chance_outcomes(self, state):
        if len(state.private) == 0:
            p = 1.0 / len(self._DEALS)
            return [(k, p) for k in range(len(self._DEALS))]
        # Board card: any physical card not held privately.
        remaining = [c for c in range(6) if c not in state.private]
        p = 1.0 / len(remaining)
        return [(c, p) for c in remaining]

    # ---- player nodes --------------------------------------------------------
    def current_player(self, state) -> int:
        return len(state.history) % 2  # player 0 acts first each round

    def _num_raises(self, state) -> int:
        return sum(1 for a in state.history if a == RAISE)

    def is_facing_bet(self, state) -> bool:
        me = len(state.history) % 2
        return state.committed[1 - me] > state.committed[me]

    def legal_actions(self, state):
        me = len(state.history) % 2
        opp = 1 - me
        to_call = state.committed[opp] - state.committed[me]
        actions = []
        if to_call > 0:
            actions.append(FOLD)
        actions.append(CALL)
        if self._num_raises(state) < MAX_RAISES:
            actions.append(RAISE)
        return actions

    def apply_action(self, state, action):
        # Chance: deal private cards.
        if len(state.private) == 0:
            i, j = self._DEALS[action]
            return LeducState(
                private=(i, j), board=-1, rnd=0, history=(),
                r0_history=(), committed=(ANTE, ANTE),
            )
        # Chance: reveal the board card.
        if state.rnd == 1 and state.board == -1:
            return LeducState(
                private=state.private, board=action, rnd=1, history=(),
                r0_history=state.r0_history, committed=state.committed,
            )
        # Betting action.
        me = len(state.history) % 2
        opp = 1 - me
        size = RAISE_SIZE[state.rnd]
        committed = list(state.committed)
        to_call = committed[opp] - committed[me]
        new_history = state.history + (action,)

        if action == FOLD:
            return LeducState(
                private=state.private, board=state.board, rnd=state.rnd,
                history=new_history, r0_history=state.r0_history,
                committed=tuple(committed), terminal=True, folder=me,
            )

        if action == RAISE:
            committed[me] += to_call + size
            return LeducState(
                private=state.private, board=state.board, rnd=state.rnd,
                history=new_history, r0_history=state.r0_history,
                committed=tuple(committed),
            )

        # CALL (or check).
        committed[me] += to_call
        # The round closes on a call of a live bet, or on the second check.
        closes = to_call > 0 or (len(state.history) >= 1 and state.history[-1] == CALL)
        if not closes:
            return LeducState(
                private=state.private, board=state.board, rnd=state.rnd,
                history=new_history, r0_history=state.r0_history,
                committed=tuple(committed),
            )
        if state.rnd == 0:
            # Advance to the board-reveal chance node.
            return LeducState(
                private=state.private, board=-1, rnd=1, history=(),
                r0_history=new_history, committed=tuple(committed),
            )
        # Round 1 closed -> showdown.
        return LeducState(
            private=state.private, board=state.board, rnd=1,
            history=new_history, r0_history=state.r0_history,
            committed=tuple(committed), terminal=True,
        )

    # ---- observation / payoff ------------------------------------------------
    def infoset_key(self, state):
        player = len(state.history) % 2
        rank = _RANK_CHR[_rank(state.private[player])]
        cur = "".join(_ACT_CHR[a] for a in state.history)
        if state.rnd == 0:
            return f"{rank}|-|{cur}"
        board = _RANK_CHR[_rank(state.board)]
        r0 = "".join(_ACT_CHR[a] for a in state.r0_history)
        return f"{rank}|{board}|{r0}|{cur}"

    def terminal_utility(self, state) -> float:
        c0, c1 = state.committed
        if state.folder == 0:
            return -float(c0)
        if state.folder == 1:
            return float(c1)
        # Showdown (contributions are equal here).
        winner = self._showdown_winner(state)
        if winner == 0:
            return float(c1)
        if winner == 1:
            return -float(c0)
        return 0.0  # split

    @staticmethod
    def _showdown_winner(state) -> int:
        r0 = _rank(state.private[0])
        r1 = _rank(state.private[1])
        board = _rank(state.board)
        p0_pair = r0 == board
        p1_pair = r1 == board
        if p0_pair and not p1_pair:
            return 0
        if p1_pair and not p0_pair:
            return 1
        if r0 > r1:
            return 0
        if r1 > r0:
            return 1
        return -1  # tie
