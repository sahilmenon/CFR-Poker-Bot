/* Client-side game engines for Kuhn poker and Leduc Hold'em.
 *
 * These mirror the Python implementations exactly -- crucially the information-set
 * key format -- so the exported CFR+ strategy (keyed by those same strings) can be
 * looked up to drive the bot. Utilities are from player 0's perspective.
 */

const RANKS = "JQK";

/* ----------------------------- Kuhn poker ------------------------------ */
const KUHN = {
  name: "kuhn",
  actionNames: { 0: "pass", 1: "bet" }, // PASS=0 (check/fold), BET=1 (bet/call)
  DECK: 3,
  TERMINALS: new Set(["pp", "bp", "bb", "pbp", "pbb"]),

  initialState() {
    return { cards: null, history: [] };
  },
  isChance(s) { return s.cards === null; },
  isTerminal(s) {
    return s.cards !== null && this.TERMINALS.has(this._hist(s));
  },
  currentPlayer(s) { return s.history.length % 2; },
  legalActions(_s) { return [0, 1]; },
  isFacingBet(s) {
    return s.history.length > 0 && s.history[s.history.length - 1] === 1;
  },

  sampleChance(s) {
    const deck = [0, 1, 2];
    const i = deck.splice(Math.floor(Math.random() * deck.length), 1)[0];
    const j = deck.splice(Math.floor(Math.random() * deck.length), 1)[0];
    return { cards: [i, j], history: [] };
  },
  applyAction(s, a) {
    return { cards: s.cards, history: s.history.concat([a]) };
  },

  _hist(s) { return s.history.map((x) => (x === 0 ? "p" : "b")).join(""); },
  infosetKey(s) {
    const p = s.history.length % 2;
    return `${RANKS[s.cards[p]]}:${this._hist(s)}`;
  },

  terminalUtility(s) {
    const h = this._hist(s);
    const [p0, p1] = s.cards;
    const sign = p0 > p1 ? 1 : -1;
    if (h === "pp") return sign * 1;
    if (h === "bb" || h === "pbb") return sign * 2;
    if (h === "bp") return 1; // P1 folds
    if (h === "pbp") return -1; // P0 folds
    throw new Error("non-terminal");
  },

  // UI helpers
  actionLabel(s, a) {
    if (a === 0) return this.isFacingBet(s) ? "Fold" : "Check";
    return this.isFacingBet(s) ? "Call" : "Bet";
  },
  privateLabel(card) { return RANKS[card]; },
  priv(s, seat) { return s.cards[seat]; },
  folder(s) {
    const h = this._hist(s);
    if (h === "bp") return 1;   // P1 folds to P0's bet
    if (h === "pbp") return 0;  // P0 folds to P1's bet
    return -1;
  },
  boardLabel(_s) { return null; },
  pot(s) {
    const c = [1, 1];
    if (s.cards) s.history.forEach((a, i) => { if (a === 1) c[i % 2] += 1; });
    return c[0] + c[1];
  },
};

/* --------------------------- Leduc Hold'em ----------------------------- */
const FOLD = 0, CALL = 1, RAISE = 2;
const LEDUC = {
  name: "leduc",
  actionNames: { 0: "fold", 1: "call", 2: "raise" },
  ACT_CHR: { 0: "f", 1: "c", 2: "r" },
  ANTE: 1,
  RAISE_SIZE: [2, 4],
  MAX_RAISES: 2,

  initialState() {
    return { priv: null, board: -1, rnd: 0, history: [], r0: [],
             committed: [1, 1], terminal: false, folder: -1 };
  },
  isChance(s) { return s.priv === null || (s.rnd === 1 && s.board === -1); },
  isTerminal(s) { return s.terminal; },
  currentPlayer(s) { return s.history.length % 2; },
  _numRaises(s) { return s.history.filter((a) => a === RAISE).length; },
  isFacingBet(s) {
    const me = s.history.length % 2;
    return s.committed[1 - me] > s.committed[me];
  },
  legalActions(s) {
    const me = s.history.length % 2;
    const toCall = s.committed[1 - me] - s.committed[me];
    const acts = [];
    if (toCall > 0) acts.push(FOLD);
    acts.push(CALL);
    if (this._numRaises(s) < this.MAX_RAISES) acts.push(RAISE);
    return acts;
  },

  sampleChance(s) {
    if (s.priv === null) {
      const deck = [0, 1, 2, 3, 4, 5];
      const i = deck.splice(Math.floor(Math.random() * deck.length), 1)[0];
      const j = deck.splice(Math.floor(Math.random() * deck.length), 1)[0];
      return { priv: [i, j], board: -1, rnd: 0, history: [], r0: [],
               committed: [1, 1], terminal: false, folder: -1 };
    }
    const remaining = [0, 1, 2, 3, 4, 5].filter((c) => !s.priv.includes(c));
    const b = remaining[Math.floor(Math.random() * remaining.length)];
    return { ...s, board: b, rnd: 1, history: [] };
  },

  applyAction(s, a) {
    const me = s.history.length % 2, opp = 1 - me;
    const size = this.RAISE_SIZE[s.rnd];
    const committed = s.committed.slice();
    const toCall = committed[opp] - committed[me];
    const history = s.history.concat([a]);
    if (a === FOLD) return { ...s, history, committed, terminal: true, folder: me };
    if (a === RAISE) {
      committed[me] += toCall + size;
      return { ...s, history, committed };
    }
    committed[me] += toCall; // CALL / check
    const closes = toCall > 0 || (s.history.length >= 1 && s.history[s.history.length - 1] === CALL);
    if (!closes) return { ...s, history, committed };
    if (s.rnd === 0) return { priv: s.priv, board: -1, rnd: 1, history: [], r0: history,
                              committed, terminal: false, folder: -1 };
    return { ...s, history, committed, terminal: true };
  },

  _hist(arr) { return arr.map((a) => this.ACT_CHR[a]).join(""); },
  infosetKey(s) {
    const p = s.history.length % 2;
    const rank = RANKS[s.priv[p] >> 1];
    const cur = this._hist(s.history);
    if (s.rnd === 0) return `${rank}|-|${cur}`;
    return `${rank}|${RANKS[s.board >> 1]}|${this._hist(s.r0)}|${cur}`;
  },

  _winner(s) {
    const r0 = s.priv[0] >> 1, r1 = s.priv[1] >> 1, b = s.board >> 1;
    const p0pair = r0 === b, p1pair = r1 === b;
    if (p0pair && !p1pair) return 0;
    if (p1pair && !p0pair) return 1;
    if (r0 > r1) return 0;
    if (r1 > r0) return 1;
    return -1;
  },
  terminalUtility(s) {
    const [c0, c1] = s.committed;
    if (s.folder === 0) return -c0;
    if (s.folder === 1) return c1;
    const w = this._winner(s);
    if (w === 0) return c1;
    if (w === 1) return -c0;
    return 0;
  },

  actionLabel(s, a) {
    if (a === FOLD) return "Fold";
    if (a === RAISE) return this.isFacingBet(s) ? "Raise" : "Bet";
    return this.isFacingBet(s) ? "Call" : "Check";
  },
  privateLabel(card) { return RANKS[card >> 1]; },
  priv(s, seat) { return s.priv[seat]; },
  folder(s) { return s.folder; },
  boardLabel(s) { return s.board >= 0 ? RANKS[s.board >> 1] : null; },
  pot(s) { return s.committed[0] + s.committed[1]; },
};

const ENGINES = { kuhn: KUHN, leduc: LEDUC };

// Allow importing under Node for cross-checking against the Python engine.
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ENGINES, KUHN, LEDUC };
}
