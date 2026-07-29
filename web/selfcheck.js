/* Node cross-check: the JS engine must produce the exact same information-set
 * keys as the Python solver, or the bot's strategy lookups silently break.
 * Enumerates each game's full tree in JS and compares the key set to the
 * exported strategy. Run: node web/selfcheck.js */

const fs = require("fs");
const path = require("path");
const { ENGINES } = require("./engine.js");

function chanceChildren(g, s) {
  if (g.name === "kuhn") {
    const out = [];
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++)
      if (i !== j) out.push({ cards: [i, j], history: [] });
    return out;
  }
  // leduc
  if (s.priv === null) {
    const out = [];
    for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++)
      if (i !== j) out.push({ priv: [i, j], board: -1, rnd: 0, history: [], r0: [],
                              committed: [1, 1], terminal: false, folder: -1 });
    return out;
  }
  return [0, 1, 2, 3, 4, 5].filter((c) => !s.priv.includes(c))
    .map((c) => ({ ...s, board: c, rnd: 1, history: [] }));
}

function walk(g, s, keys, terms) {
  if (g.isTerminal(s)) { terms.push(g.terminalUtility(s)); return; }
  if (g.isChance(s)) { for (const ns of chanceChildren(g, s)) walk(g, ns, keys, terms); return; }
  const key = g.infosetKey(s);
  const acts = g.legalActions(s);
  if (!keys.has(key)) keys.set(key, acts.map((a) => g.actionNames[a]).sort().join(","));
  for (const a of acts) walk(g, g.applyAction(s, a), keys, terms);
}

let failures = 0;
function check(name, expectedCount) {
  const g = ENGINES[name];
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, "data", `${name}.json`)));
  const strat = data.strategy;
  const keys = new Map();
  const terms = [];
  walk(g, g.initialState(), keys, terms);

  const jsKeys = new Set(keys.keys());
  const pyKeys = new Set(Object.keys(strat));
  const missingInPy = [...jsKeys].filter((k) => !pyKeys.has(k));
  const missingInJs = [...pyKeys].filter((k) => !jsKeys.has(k));

  // action-set agreement per key
  let actionMismatch = 0;
  for (const k of jsKeys) {
    if (!pyKeys.has(k)) continue;
    const py = Object.keys(strat[k]).sort().join(",");
    if (py !== keys.get(k)) actionMismatch++;
  }
  // probabilities sum to ~1
  let badSum = 0;
  for (const k of pyKeys) {
    const s = Object.values(strat[k]).reduce((a, b) => a + b, 0);
    if (Math.abs(s - 1) > 1e-3) badSum++;
  }

  const ok = jsKeys.size === expectedCount && missingInPy.length === 0
    && missingInJs.length === 0 && actionMismatch === 0 && badSum === 0;
  console.log(`${name}: JS keys=${jsKeys.size} (expect ${expectedCount}), ` +
    `py keys=${pyKeys.size}, terminals=${terms.length}, ` +
    `missing_in_py=${missingInPy.length}, missing_in_js=${missingInJs.length}, ` +
    `action_mismatch=${actionMismatch}, bad_prob_sum=${badSum}  ${ok ? "OK" : "FAIL"}`);
  if (missingInPy.length) console.log("   e.g. JS key not in strategy:", missingInPy.slice(0, 5));
  if (missingInJs.length) console.log("   e.g. strategy key not in JS:", missingInJs.slice(0, 5));
  if (!ok) failures++;
}

// End-to-end: self-play expected value in JS must match the Python export
// (validates applyAction + terminalUtility, not just the keys).
function ev(g, s, strat) {
  if (g.isTerminal(s)) return g.terminalUtility(s);
  if (g.isChance(s)) {
    const ch = chanceChildren(g, s);
    return ch.reduce((acc, ns) => acc + ev(g, ns, strat), 0) / ch.length;
  }
  const dist = strat[g.infosetKey(s)];
  let v = 0;
  for (const a of g.legalActions(s)) {
    const p = dist[g.actionNames[a]] || 0;
    if (p) v += p * ev(g, g.applyAction(s, a), strat);
  }
  return v;
}

for (const name of ["kuhn", "leduc"]) {
  const g = ENGINES[name];
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, "data", `${name}.json`)));
  const v = ev(g, g.initialState(), data.strategy);
  console.log(`${name}: JS self-play value to P0 = ${v.toFixed(6)}` +
    (name === "kuhn" ? "  (Python/-1/18 = -0.055556)" : "  (expect ~0)"));
}

check("kuhn", 12);
check("leduc", 288);
process.exit(failures ? 1 : 0);
