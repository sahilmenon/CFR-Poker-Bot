"""Ground-truth facts about Kuhn poker used to validate the solver.

Kuhn poker is solved in closed form:
  * The game value to player 0 is exactly -1/18.
  * The Nash equilibria form a one-parameter family indexed by alpha in [0, 1/3]:
    player 0 bets the Jack with probability alpha and the King with probability
    3*alpha (and never bets the Queen as the opener). A converged CFR average
    strategy must therefore satisfy king_bet ~= 3 * jack_bet with queen_bet ~= 0.
"""

from __future__ import annotations

from .games.kuhn import BET

KUHN_GAME_VALUE = -1.0 / 18.0  # to player 0


def kuhn_opening_bet_probs(avg_strategy: dict):
    """Return (jack_bet, queen_bet, king_bet) at player 0's opening decision."""
    jack_bet = float(avg_strategy["J:"][BET])
    queen_bet = float(avg_strategy["Q:"][BET])
    king_bet = float(avg_strategy["K:"][BET])
    return jack_bet, queen_bet, king_bet


def kuhn_alpha_consistency(avg_strategy: dict) -> dict:
    """Check the recovered opener strategy against the analytic alpha-family."""
    jack_bet, queen_bet, king_bet = kuhn_opening_bet_probs(avg_strategy)
    alpha = jack_bet
    return {
        "alpha": alpha,
        "jack_bet": jack_bet,
        "queen_bet": queen_bet,
        "king_bet": king_bet,
        "king_over_jack": (king_bet / jack_bet) if jack_bet > 1e-9 else float("nan"),
        "residual_king_eq_3alpha": abs(king_bet - 3.0 * jack_bet),
    }
