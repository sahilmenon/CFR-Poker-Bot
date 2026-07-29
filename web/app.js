/* UI controller: load exported strategies, render validation badges, and run the
 * play-against-the-bot loop for both games. All game logic lives in engine.js. */

const REPO_URL = "https://github.com/sahilmenon/CFR-Poker-Bot";
const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const DATA = {};       // game -> exported json
let game = KUHN;       // current engine
let state = null;
let humanSeat = 0;     // alternates each hand
let busy = false;      // block input while bot/animation runs
const totals = { kuhn: { hands: 0, net: 0 }, leduc: { hands: 0, net: 0 } };

/* ------------------------------- boot --------------------------------- */
async function boot() {
  const [kuhn, leduc] = await Promise.all([
    fetch("data/kuhn.json").then((r) => r.json()),
    fetch("data/leduc.json").then((r) => r.json()),
  ]);
  DATA.kuhn = kuhn;
  DATA.leduc = leduc;
  $("repo-link").href = REPO_URL;
  renderBadges();
  wireControls();
  selectGame("kuhn");
}

function renderBadges() {
  const k = DATA.kuhn.meta, l = DATA.leduc.meta;
  const badges = [
    { k: "Kuhn game value", v: k.value.toFixed(4), ok: Math.abs(k.value - k.value_truth) < 1e-3 },
    { k: "vs −1/18", v: "−0.0556" },
    { k: "King bet ÷ Jack bet", v: k.king_over_jack.toFixed(2), ok: Math.abs(k.king_over_jack - 3) < 0.2 },
    { k: "Kuhn exploitability", v: fmtExp(k.exploitability), ok: k.exploitability < 2e-3 },
    { k: "Leduc info sets", v: l.infosets, ok: l.infosets === 288 },
    { k: "Leduc exploitability", v: fmtExp(l.exploitability), ok: l.exploitability < 5e-3 },
  ];
  $("badges").innerHTML = badges.map((b) =>
    `<div class="badge"><div class="k">${b.k}</div><div class="v ${b.ok ? "ok" : ""}">${b.v}</div></div>`
  ).join("");
}

function fmtExp(x) {
  const e = Math.floor(Math.log10(x));
  const m = (x / Math.pow(10, e)).toFixed(1);
  return `${m}×10${supers(e)}`;
}
function supers(n) {
  const map = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
  return String(n).split("").map((c) => map[c] || c).join("");
}

/* ----------------------------- controls ------------------------------- */
function wireControls() {
  document.querySelectorAll(".tab").forEach((t) =>
    t.addEventListener("click", () => selectGame(t.dataset.game)));
  $("btn-next").addEventListener("click", () => { if (!busy) newHand(); });
  $("btn-reset").addEventListener("click", () => {
    totals[game.name] = { hands: 0, net: 0 };
    renderScore();
  });
}

function selectGame(name) {
  game = ENGINES[name];
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.game === name));
  $("seat-board").style.display = name === "leduc" ? "" : "none";
  $("log").innerHTML = "";
  renderScore();
  newHand();
}

/* ------------------------------- play --------------------------------- */
function newHand() {
  humanSeat = totals[game.name].hands % 2; // alternate seats
  state = game.initialState();
  $("log").innerHTML = "";
  log(`New hand. You are ${humanSeat === 0 ? "Player 1 (first to act)" : "Player 2"}.`, "deal");
  step();
}

async function step() {
  busy = true;
  clearActions();
  // resolve chance nodes (deal, board reveal)
  while (game.isChance(state)) {
    const hadBoard = game.boardLabel(state);
    state = game.sampleChance(state);
    if (!hadBoard && game.boardLabel(state)) log(`Board card revealed: ${game.boardLabel(state)}`, "deal");
    await sleep(150);
  }
  render();

  if (game.isTerminal(state)) { settle(); return; }

  if (game.currentPlayer(state) === humanSeat) {
    busy = false;
    offerHumanActions();
  } else {
    await sleep(650);
    botMove();
  }
}

function botMove() {
  const key = game.infosetKey(state);
  const dist = DATA[game.name].strategy[key] || {};
  const a = sampleAction(dist);
  log(`Bot: ${game.actionLabel(state, a)}`, "");
  state = game.applyAction(state, a);
  step();
}

function humanMove(a) {
  if (busy) return;
  log(`You: ${game.actionLabel(state, a)}`, "you");
  state = game.applyAction(state, a);
  step();
}

function sampleAction(dist) {
  const legal = game.legalActions(state);
  let r = Math.random(), acc = 0, last = legal[0];
  for (const a of legal) {
    const p = dist[game.actionNames[a]] || 0;
    acc += p;
    last = a;
    if (r <= acc) return a;
  }
  return last;
}

function offerHumanActions() {
  const box = $("actions");
  box.innerHTML = "";
  const legal = game.legalActions(state);
  legal.forEach((a) => {
    const b = document.createElement("button");
    b.className = "btn" + (game.actionLabel(state, a).match(/Bet|Raise|Call/) ? " primary" : "");
    b.textContent = game.actionLabel(state, a);
    b.addEventListener("click", () => humanMove(a));
    box.appendChild(b);
  });
  showHint();
}

function showHint() {
  const hint = $("hint");
  if (!$("gto-toggle").checked) { hint.textContent = ""; return; }
  const dist = DATA[game.name].strategy[game.infosetKey(state)] || {};
  const parts = game.legalActions(state).map((a) => {
    const p = dist[game.actionNames[a]] || 0;
    return `${game.actionLabel(state, a)} ${Math.round(p * 100)}%`;
  });
  hint.innerHTML = `Equilibrium here: <b>${parts.join(" · ")}</b>`;
}

function clearActions() { $("actions").innerHTML = ""; $("hint").textContent = ""; }

/* ---------------------------- settlement ------------------------------ */
function settle() {
  const u0 = game.terminalUtility(state);              // to player 0
  const you = humanSeat === 0 ? u0 : -u0;              // to human
  const t = totals[game.name];
  t.hands += 1;
  t.net += you;

  render(true); // reveal bot card
  const botCard = game.privateLabel(game.priv(state, 1 - humanSeat));
  const youCard = game.privateLabel(game.priv(state, humanSeat));
  const folder = game.folder(state);
  const cls = you > 0 ? "win" : you < 0 ? "lose" : "";
  const amt = `${Math.abs(you)} chip${Math.abs(you) === 1 ? "" : "s"}`;
  let msg;
  if (folder === humanSeat) msg = `You folded. You lose ${amt}.`;
  else if (folder === 1 - humanSeat) msg = `Bot folded (you had ${youCard}). You win ${amt}.`;
  else {
    const verb = you > 0 ? "win" : you < 0 ? "lose" : "tie";
    msg = `Showdown: you ${youCard}, bot ${botCard}. You ${verb} ${amt}.`;
  }
  log(msg, cls);

  renderScore();
  busy = false;
  const box = $("actions");
  box.innerHTML = "";
  const b = document.createElement("button");
  b.className = "btn primary";
  b.textContent = "Next hand →";
  b.addEventListener("click", () => newHand());
  box.appendChild(b);
}

/* ----------------------------- rendering ------------------------------ */
function render(reveal = false) {
  const youSeat = humanSeat, botSeat = 1 - humanSeat;
  // your cards
  $("you-cards").innerHTML = card(game.privateLabel(game.priv(state, youSeat)));
  // bot cards (hidden until reveal)
  $("bot-cards").innerHTML = reveal
    ? card(game.privateLabel(game.priv(state, botSeat)))
    : `<div class="pcard back">?</div>`;
  // board
  const bl = game.boardLabel(state);
  $("board-cards").innerHTML = bl ? card(bl, "board") : `<div class="pcard back">?</div>`;
  // pot + turn highlight
  $("pot").innerHTML = `Pot <b>${game.pot(state)}</b>`;
  const turn = !game.isTerminal(state) && !game.isChance(state) ? game.currentPlayer(state) : -1;
  $("seat-you").classList.toggle("turn", turn === youSeat);
  $("seat-bot").classList.toggle("turn", turn === botSeat);
}

function card(label, extra = "") {
  return `<div class="pcard ${extra}">${label}</div>`;
}

function renderScore() {
  const t = totals[game.name];
  $("s-hands").textContent = t.hands;
  const net = $("s-net");
  net.textContent = (t.net >= 0 ? "+" : "") + t.net.toFixed(2);
  net.className = "val " + (t.net > 0 ? "pos" : t.net < 0 ? "neg" : "");
  const rate = $("s-rate");
  rate.textContent = t.hands ? (t.net / t.hands).toFixed(3) : "—";
  rate.className = "val " + (t.net > 0 ? "pos" : t.net < 0 ? "neg" : "");
  $("s-value").textContent = "0.000 (ceiling)";
  $("score-note").innerHTML =
    "Seats alternate, so the most you can average against a Nash strategy is " +
    "<b>break-even</b>, 0 chips per hand. A winning streak is variance; it drifts back " +
    "toward zero or below. An equilibrium can't be exploited.";
}

function log(msg, cls = "") {
  const el = document.createElement("div");
  el.className = "l " + cls;
  el.textContent = msg;
  const box = $("log");
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

$("gto-toggle") && document.addEventListener("change", (e) => {
  if (e.target.id === "gto-toggle" && !busy && state && !game.isTerminal(state)
      && !game.isChance(state) && game.currentPlayer(state) === humanSeat) showHint();
});

boot();
