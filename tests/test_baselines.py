"""The solved strategy should beat every fixed baseline, and the Monte Carlo
estimate should agree with the exact expected value."""

import pytest

from cfr_poker.baselines import (
    BASELINES,
    exact_bb_per_100,
    monte_carlo_bb_per_100,
)
from cfr_poker.cfr import cfr_plus
from cfr_poker.evaluate import strategy_from_table
from cfr_poker.games import KuhnPoker


@pytest.fixture(scope="module")
def solved_kuhn():
    game = KuhnPoker()
    solver = cfr_plus(game)
    solver.iterate(3000)
    hero = strategy_from_table(game, solver.solution())
    return game, hero


@pytest.mark.parametrize("baseline", list(BASELINES))
def test_solved_strategy_beats_baseline(solved_kuhn, baseline):
    game, hero = solved_kuhn
    villain = BASELINES[baseline](game)
    assert exact_bb_per_100(game, hero, villain) > 0.0


def test_baselines_are_distinct(solved_kuhn):
    game, hero = solved_kuhn
    edges = {name: exact_bb_per_100(game, hero, BASELINES[name](game))
             for name in BASELINES}
    # call_station and always_raise are genuinely different opponents in Kuhn.
    assert edges["call_station"] != pytest.approx(edges["always_raise"], abs=1e-6)


def test_monte_carlo_agrees_with_exact(solved_kuhn):
    game, hero = solved_kuhn
    villain = BASELINES["random"](game)
    exact = exact_bb_per_100(game, hero, villain)
    mc, ci = monte_carlo_bb_per_100(game, hero, villain, hands=40_000, seed=7)
    assert abs(mc - exact) < 3 * ci + 1e-9  # within ~3 standard errors
