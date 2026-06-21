"use strict";
const app = document.getElementById("app");
const ABCD = ["A", "B", "C", "D", "E", "F"];
const api = (p, opts) => fetch(p, opts).then((r) => r.json());
const post = (p, body) =>
  api(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])));
const bar = (frac) => `<div class="bar"><span style="width:${Math.round((frac || 0) * 100)}%"></span></div>`;
const paras = (text) => (text || "").split(/\n\n+/).map((p) => `<p>${esc(p)}</p>`).join("");

let COURSE = null; // cached course overview
let tutorMsgs = []; // AI tutor chat history (session-local)
let interviewMsgs = []; // mock-interview chat history
let examState = null; // current exam in progress
let masterState = null; // current Read & Master session
let LIB = null; // cached source library

function findContinue(course) {
  for (const m of course.modules) for (const t of m.topics) if (!t.done) return t.id;
  return course.modules[0]?.topics[0]?.id;
}

// ---------------------------------------------------------------- screens
async function routeHome() {
  COURSE = await api("/api/course");
  const c = COURSE;
  const s = await api("/api/stats");
  const cont = findContinue(c);
  let h = `<header class="hero">
    <h1>${esc(c.title)}</h1>
    <div class="stats"><span>⭐ Level ${s.level}</span><span>🔥 ${c.streak}-day streak</span><span>📚 ${c.total_done}/${c.total_topics}</span></div>
    <div class="xpbar"><span style="width:${Math.round(100 * s.xp_in_level / s.xp_per_level)}%"></span></div>
    <div class="xptext">${s.xp} XP · ${s.xp_per_level - s.xp_in_level} XP to Level ${s.level + 1}</div>
    ${cont ? `<a class="primary" href="#/lesson/${cont}">${c.total_done ? "Continue learning" : "Start learning"}</a>` : ""}
  </header><a class="primary" href="#/library" style="margin-top:10px">📚 Source Library — read your books</a><div class="units">`;
  for (const m of c.modules) {
    h += `<a class="card unit" href="#/unit/${m.id}">
      <div class="emoji">${m.emoji}</div>
      <div class="grow"><div class="t">${esc(m.title)}</div>
        <div class="sub">${m.done_count}/${m.lesson_count} lessons</div>
        ${bar(m.lesson_count ? m.done_count / m.lesson_count : 0)}</div>
      <div class="chev">›</div></a>`;
  }
  app.innerHTML = h + "</div>";
}

async function routeUnit(id) {
  if (!COURSE) COURSE = await api("/api/course");
  const m = COURSE.modules.find((x) => x.id === id);
  if (!m) return routeHome();
  let h = `<a class="back" href="#/">‹ All units</a>
    <h1>${m.emoji} ${esc(m.title)}</h1>
    <div class="crumb">${m.done_count}/${m.lesson_count} lessons complete</div>
    ${bar(m.lesson_count ? m.done_count / m.lesson_count : 0)}
    <div class="lessons">`;
  m.topics.forEach((t, i) => {
    h += `<a class="lrow ${t.done ? "done" : ""}" href="#/lesson/${t.id}">
      <div class="n">${t.done ? "✓" : i + 1}</div>
      <div class="lt">${esc(t.title)}</div>
      ${t.has_media ? '<div class="media-dot">📊</div>' : ""}</a>`;
  });
  app.innerHTML = h + `</div><a class="primary" href="#/exam/${id}" style="margin-top:8px">📝 Take the unit exam</a>`;
}

function flashcardHTML(id, q, a) {
  return `<div class="fc" data-id="${id}">
    <div class="q">${esc(q)}</div>
    <div class="a hidden">${esc(a)}</div>
    <div class="fc-actions"><button data-act="reveal">Show answer</button></div></div>`;
}
function quizHTML(id, q, choices, answer, explanation) {
  return `<div class="qz" data-id="${id}" data-answer="${esc(answer)}" data-expl="${esc(explanation || "")}">
    <div class="q">${esc(q)}</div>
    <div class="choices">${choices.map((ch, i) =>
      `<button data-act="choose" data-i="${i}">${ABCD[i]}. ${esc(ch)}</button>`).join("")}</div>
    <div class="explain hidden"></div></div>`;
}

async function routeLesson(id) {
  const t = await api("/api/topic/" + id);
  if (t.error) return routeHome();
  const m = t.media || {};
  let h = `<a class="back" href="#/unit/${t.module}">‹ ${esc(t.module_title)}</a>
    <div class="lesson">
    <div class="crumb">${t.module_emoji} ${esc(t.module_title)} · Lesson ${t.lesson_index} of ${t.lesson_count}</div>
    <h1>${esc(t.title)}</h1><div class="src">${esc(t.source)}</div>`;
  if (m.image) h += `<figure><img src="${m.image}" alt="" loading="lazy">
    <figcaption>${esc(m.image_caption || "")}</figcaption></figure>`;
  h += `<p class="summary">${esc(t.summary)}</p>`;
  if (t.reading) h += `<h3>📖 Reading</h3><div class="reading">${paras(t.reading)}</div>`;
  if (t.key_points?.length)
    h += `<h3>Key points</h3><ul>${t.key_points.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>`;
  if (m.web_notes) h += `<div class="deepdive"><h3>🌐 Deep dive</h3><p>${esc(m.web_notes)}</p></div>`;
  if (t.case_study) {
    const cs = t.case_study;
    h += `<h3>📋 Case study — ${esc(cs.title)}</h3><div class="case"><p>${esc(cs.scenario)}</p>` +
      (cs.walkthrough?.length ? `<ol>${cs.walkthrough.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>` : "") +
      `</div>`;
  }
  if (t.critical_thinking?.length)
    h += `<h3>💡 Think it through</h3>` + t.critical_thinking.map((c) =>
      `<div class="ct"><div class="q">${esc(c.prompt)}</div>
       <div class="a hidden">${esc(c.model_answer)}</div>
       <textarea class="ct-input" placeholder="Reason it out here, then grade it or reveal the model answer…"></textarea>
       <div class="fc-actions"><button data-act="grade-ct">🤖 Grade my answer</button><button data-act="reveal-ct">Reveal model answer</button></div></div>`).join("");
  if (m.video?.embed)
    h += `<h3>🎥 Watch</h3><div class="video"><iframe src="${m.video.embed}" loading="lazy"
      allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>`;
  if (m.sources?.length)
    h += `<h3>Sources</h3><div class="sources">${m.sources.map((s) =>
      `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} ↗</a>`).join("")}</div>`;
  if (t.flashcards?.length) {
    h += `<h3>🧠 Key card</h3>${flashcardHTML(t.flashcards[0].id, t.flashcards[0].q, t.flashcards[0].a)}`;
    if (t.flashcards.length > 1)
      h += `<button class="back" data-act="morecards">+ ${t.flashcards.length - 1} more card${t.flashcards.length > 2 ? "s" : ""}</button>
        <div id="morecards" class="hidden">${t.flashcards.slice(1).map((c) => flashcardHTML(c.id, c.q, c.a)).join("")}</div>`;
  }
  if (t.quiz?.length)
    h += `<h3>❓ Quiz</h3>${t.quiz.map((q) => quizHTML(q.id, q.q, q.choices, q.answer, q.explanation)).join("")}`;
  h += `<a class="primary big" href="#/master/${t.id}" style="background:#a64d79">🎓 Read the source &amp; prove it</a>`;
  h += `<h3>🤖 Ask the tutor</h3>
    <div class="tutorbtns">
      <button data-act="tx" data-mode="simpler">Explain simpler</button>
      <button data-act="tx" data-mode="example">Another example</button>
      <button data-act="tx" data-mode="deeper">Go deeper</button>
      <button data-act="tpractice">Practice question</button>
    </div><div id="tutorout" class="tutorout"></div>`;
  const nextHref = t.next_id ? `#/lesson/${t.next_id}` : `#/unit/${t.module}`;
  h += `<button class="primary big ${t.done ? "done" : ""}" id="complete" data-next="${nextHref}">
    ${t.done ? "✓ Completed — next lesson ›" : "Mark complete & continue ›"}</button></div>`;
  app.innerHTML = h;
  window.scrollTo(0, 0);
}

async function routeReview() {
  const data = await api("/api/review");
  let h = `<h1>🔁 Review</h1><a class="primary" href="#/drill">🎯 Drill your weak areas</a>`;
  if (!data.items.length) {
    h += `<div class="empty">✅ All caught up!<br>Nothing due for review.<br><br>
      Complete lessons and answer quizzes — they'll come back here on a spaced schedule.</div>`;
    app.innerHTML = h;
    return;
  }
  h += `<div class="crumb">${data.due_count} item(s) due</div>`;
  for (const it of data.items) {
    h += `<div class="tag">${esc(it.topic_title)}</div>`;
    h += it.kind === "flashcard"
      ? flashcardHTML(it.item_id, it.q, it.a)
      : quizHTML(it.item_id, it.q, it.choices, it.answer, it.explanation);
  }
  app.innerHTML = h;
}

async function routeDrill() {
  const data = await api("/api/drill");
  let h = `<a class="back" href="#/review">‹ Review</a><h1>🎯 Weak-Area Drill</h1>`;
  if (!data.items.length) {
    h += `<div class="empty">No attempts to drill yet.<br>Answer some quizzes and flashcards first — this mode resurfaces the ones you miss most.</div>`;
    app.innerHTML = h; return;
  }
  h += `<div class="crumb">Your ${data.count} lowest-accuracy items — practice until they stick</div>`;
  for (const it of data.items) {
    h += `<div class="tag">${esc(it.topic_title)}</div>`;
    h += it.kind === "flashcard"
      ? flashcardHTML(it.item_id, it.q, it.a)
      : quizHTML(it.item_id, it.q, it.choices, it.answer, it.explanation);
  }
  app.innerHTML = h;
}

async function routeProgress() {
  const s = await api("/api/stats");
  let h = `<h1>📊 Progress</h1>
    <div class="levelcard">
      <div class="lvl">Lv<br>${s.level}</div>
      <div class="lvlinfo">
        <div class="xpbar dark"><span style="width:${Math.round(100 * s.xp_in_level / s.xp_per_level)}%"></span></div>
        <div class="xptext dark">${s.xp} XP · ${s.xp_per_level - s.xp_in_level} XP to Level ${s.level + 1}</div>
      </div>
    </div>
    <div class="statgrid">
      <div class="stat"><div class="v">${s.streak}</div><div class="l">day streak</div></div>
      <div class="stat"><div class="v">${s.total_done}/${s.total_topics}</div><div class="l">lessons</div></div>
      <div class="stat"><div class="v">${s.overall_accuracy == null ? "—" : s.overall_accuracy + "%"}</div><div class="l">accuracy</div></div>
    </div>
    <a class="primary" href="#/exams">📝 Exams &amp; Certificate ›</a>
    <h3>🏆 Achievements (${s.earned_count}/${s.achievements.length})</h3>
    <div class="badges">`;
  for (const a of s.achievements)
    h += `<div class="badge ${a.earned ? "earned" : "locked"}" title="${esc(a.desc)}">
      <div class="be">${a.emoji}</div><div class="bn">${esc(a.name)}</div></div>`;
  h += `</div><h3>Mastery by unit</h3>`;
  for (const m of s.modules)
    h += `<div class="mrow"><div class="top">
      <span>${m.emoji} ${esc(m.title)}</span>
      <span class="mlabel ${m.label.toLowerCase()}">${m.label} · ${m.mastery}%</span></div>
      ${bar(m.mastery / 100)}</div>`;
  app.innerHTML = h;
}

// ---------------------------------------------------------------- interactions
app.addEventListener("click", async (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const act = btn.dataset.act;

  if (act === "reveal") {
    const fc = btn.closest(".fc");
    fc.querySelector(".a").classList.remove("hidden");
    fc.querySelector(".fc-actions").innerHTML =
      `<button class="btn-good" data-act="grade" data-q="5">✅ Knew it</button>
       <button class="btn-bad" data-act="grade" data-q="2">❌ Missed it</button>`;
  } else if (act === "reveal-ct") {
    btn.closest(".ct").querySelector(".a").classList.remove("hidden");
    btn.remove();
  } else if (act === "morecards") {
    document.getElementById("morecards").classList.remove("hidden");
    btn.remove();
  } else if (act === "grade-ct") {
    const ct = btn.closest(".ct");
    const ua = ct.querySelector(".ct-input").value.trim();
    if (!ua) return;
    const label = btn.textContent; btn.disabled = true; btn.textContent = "Grading…";
    const r = await post("/api/tutor/grade", {
      prompt: ct.querySelector(".q").textContent,
      model_answer: ct.querySelector(".a").textContent,
      user_answer: ua,
    });
    let box = ct.querySelector(".ct-feedback");
    if (!box) { box = document.createElement("div"); box.className = "ct-feedback"; ct.appendChild(box); }
    box.textContent = r.feedback || r.answer || "(no response)";
    btn.disabled = false; btn.textContent = label;
  } else if (act === "tx") {
    const id = location.hash.split("/")[2];
    const out = document.getElementById("tutorout"); out.innerHTML = `<div class="tutorcard muted">Thinking…</div>`;
    const r = await post("/api/tutor/explain", { topic_id: id, mode: btn.dataset.mode });
    out.innerHTML = `<div class="tutorcard">${esc(r.answer || r.feedback)}</div>`;
  } else if (act === "tpractice") {
    const id = location.hash.split("/")[2];
    const out = document.getElementById("tutorout"); out.innerHTML = `<div class="tutorcard muted">Writing a question…</div>`;
    const r = await post("/api/tutor/practice", { topic_id: id });
    out.innerHTML = `<div class="ct"><div class="q"><b>Practice:</b> ${esc(r.question || r.feedback)}</div>
      <div class="a hidden">${esc(r.answer || "")}</div>
      <div class="fc-actions"><button data-act="reveal-ct">Reveal answer</button></div></div>`;
  } else if (act === "exchoose") {
    const exq = btn.closest(".exq");
    exq.querySelectorAll(".choices button").forEach((b) => b.classList.remove("chosen"));
    btn.classList.add("chosen");
    if (examState) examState.answers[exq.dataset.id] = ABCD[+btn.dataset.i];
  } else if (act === "exsubmit") {
    if (!examState) return;
    const answered = Object.keys(examState.answers).length;
    if (answered < examState.count && !confirm(`You answered ${answered} of ${examState.count}. Submit anyway?`)) return;
    btn.disabled = true; btn.textContent = "Grading…";
    const r = await post(`/api/exam/${examState.module}/submit`, { answers: examState.answers });
    const byId = {}; r.results.forEach((x) => (byId[x.item_id] = x));
    document.querySelectorAll(".exq").forEach((exq) => {
      const res = byId[exq.dataset.id]; if (!res) return;
      exq.querySelectorAll(".choices button").forEach((b) => {
        const L = ABCD[+b.dataset.i];
        if (L === res.answer) b.classList.add("correct");
        else if (b.classList.contains("chosen")) b.classList.add("wrong");
        b.disabled = true;
      });
      if (res.explanation) { const ed = document.createElement("div"); ed.className = "explain"; ed.textContent = res.explanation; exq.appendChild(ed); }
    });
    COURSE = null;
    const pct = r.total ? Math.round(100 * r.score / r.total) : 0;
    document.getElementById("exresult").innerHTML =
      `<div class="examscore ${r.passed ? "pass" : "fail"}">${r.passed ? "✅ PASSED" : "❌ Not yet"} — ${r.score}/${r.total} (${pct}%)${r.passed ? "" : ` · need ${r.pass_pct}%`}</div>
       <a class="primary" href="#/exams">Back to exams ›</a>`;
    document.getElementById("exresult").scrollIntoView({ behavior: "smooth" });
  } else if (act === "msubmit") {
    if (!masterState) return;
    const items = [];
    document.querySelectorAll(".mq").forEach((mq) => items.push({ question: mq.dataset.q, answer: mq.querySelector(".mq-input").value }));
    if (!items.some((it) => it.answer.trim())) return;
    const label = btn.textContent; btn.disabled = true; btn.textContent = "Grading… (a few seconds)";
    const r = await post(`/api/master/${masterState.tid}/grade`, { items });
    const byQ = {}; (r.results || []).forEach((x) => (byQ[x.question] = x));
    document.querySelectorAll(".mq").forEach((mq) => {
      const res = byQ[mq.dataset.q]; if (!res) return;
      let fb = mq.querySelector(".mq-fb"); if (!fb) { fb = document.createElement("div"); mq.appendChild(fb); }
      fb.className = "mq-fb " + (res.passed ? "pass" : "fail");
      fb.textContent = (res.passed ? "✅ PASS — " : "🔁 RETRY — ") + res.feedback;
    });
    COURSE = null;
    document.getElementById("mresult").innerHTML = r.mastered
      ? `<div class="examscore pass">🎓 Topic mastered!</div><a class="primary" href="#/lesson/${masterState.tid}">Back to lesson ›</a>`
      : `<div class="examscore fail">Not yet — revise the flagged answers and resubmit.</div>`;
    btn.disabled = false; btn.textContent = label;
    document.getElementById("mresult").scrollIntoView({ behavior: "smooth" });
  } else if (act === "grade") {
    const fc = btn.closest(".fc");
    await post("/api/answer", { item_id: fc.dataset.id, item_type: "flashcard", quality: +btn.dataset.q });
    fc.classList.add("graded");
    fc.querySelector(".fc-actions").innerHTML =
      `<span class="tag">${btn.dataset.q >= 3 ? "Got it — see you on the next review." : "Logged — we'll show this again soon."}</span>`;
  } else if (act === "choose") {
    const qz = btn.closest(".qz");
    if (qz.classList.contains("graded")) return;
    qz.classList.add("graded");
    const chosen = ABCD[+btn.dataset.i];
    const correct = qz.dataset.answer;
    const ok = chosen === correct;
    qz.querySelectorAll(".choices button").forEach((b) => {
      const L = ABCD[+b.dataset.i];
      if (L === correct) b.classList.add("correct");
      else if (b === btn) b.classList.add("wrong");
      b.disabled = true;
    });
    const ex = qz.querySelector(".explain");
    ex.innerHTML = `${ok ? "✅ Correct." : "❌ Answer: " + correct + "."} ${esc(qz.dataset.expl)}`;
    ex.classList.remove("hidden");
    await post("/api/answer", { item_id: qz.dataset.id, item_type: "quiz", quality: ok ? 5 : 2 });
  } else if (btn.id === "complete") {
    const id = location.hash.split("/")[2];
    await post(`/api/topic/${id}/complete`, {});
    COURSE = null; // invalidate cache so progress refreshes
    location.hash = btn.dataset.next;
  }
});

// ---------------------------------------------------------------- tools
function erf(x) {
  const t = 1 / (1 + 0.3275911 * Math.abs(x));
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return x >= 0 ? y : -y;
}
const normCdf = (z) => 0.5 * (1 + erf(z / Math.SQRT2));
const num = (id) => parseFloat(document.getElementById(id).value);

function computeCp() {
  const USL = num("cp_usl"), LSL = num("cp_lsl"), mu = num("cp_mean"), sd = num("cp_sigma");
  const out = document.getElementById("cp_out");
  if (!(sd > 0) || isNaN(USL) || isNaN(LSL) || isNaN(mu) || USL <= LSL) {
    out.innerHTML = '<span class="muted">Enter USL &gt; LSL and σ &gt; 0.</span>'; return;
  }
  const Cp = (USL - LSL) / (6 * sd);
  const zU = (USL - mu) / sd, zL = (mu - LSL) / sd;
  const Cpk = Math.min(zU, zL) / 3;
  const ppm = (normCdf(-zU) + normCdf(-zL)) * 1e6;
  const verdict = Cpk >= 1.67 ? ["excellent", "good"] : Cpk >= 1.33 ? ["meets common floor", "good"]
    : Cpk >= 1.0 ? ["marginal", "warn"] : ["not capable", "bad"];
  out.innerHTML =
    `<div class="rgrid">
       <div><b>Cp</b><span>${Cp.toFixed(2)}</span></div>
       <div><b>Cpk</b><span>${Cpk.toFixed(2)}</span></div>
       <div><b>Est. defects</b><span>${ppm < 1 ? ppm.toFixed(2) : Math.round(ppm).toLocaleString()} ppm</span></div>
       <div><b>Process σ (Z)</b><span>${(Math.min(zU, zL)).toFixed(2)}σ</span></div>
     </div>
     <div class="verdict ${verdict[1]}">Cpk ${Cpk.toFixed(2)} — ${verdict[0]}${Cpk < Cp - 0.05 ? " · process is off-center" : ""}</div>`;
}

function computeGrr() {
  const EV = num("grr_ev"), AV = num("grr_av"), PV = num("grr_pv");
  const out = document.getElementById("grr_out");
  if (!(EV >= 0) || !(AV >= 0) || !(PV > 0)) { out.innerHTML = '<span class="muted">Enter EV, AV, and PV (&gt;0).</span>'; return; }
  const GRR = Math.sqrt(EV * EV + AV * AV);
  const TV = Math.sqrt(GRR * GRR + PV * PV);
  const pGRR = 100 * GRR / TV;
  const ndc = Math.floor(1.41 * (PV / GRR));
  const v = pGRR < 10 ? ["acceptable", "good"] : pGRR <= 30 ? ["marginal (depends on application)", "warn"] : ["unacceptable", "bad"];
  const driver = AV > EV ? "Reproducibility (operators) dominates → standardize method/training." : "Repeatability (equipment) dominates → improve the gauge/fixture.";
  out.innerHTML =
    `<div class="rgrid">
       <div><b>%GR&amp;R</b><span>${pGRR.toFixed(1)}%</span></div>
       <div><b>ndc</b><span>${ndc}</span></div>
     </div>
     <div class="verdict ${v[1]}">%GR&amp;R ${pGRR.toFixed(1)}% — ${v[0]}${ndc < 5 ? " · ndc &lt; 5 (too coarse)" : ""}</div>
     <div class="muted small">${driver}</div>`;
}

// control-chart simulator
let simNoise = [];
const gauss = () => { let u = 0, v = 0; while (!u) u = Math.random(); while (!v) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
const genNoise = () => { simNoise = Array.from({ length: 25 }, gauss); };

function drawCC() {
  const cv = document.getElementById("ccsim"); if (!cv) return;
  const ctx = cv.getContext("2d"), W = cv.width, H = cv.height, pad = 28;
  const shift = num("cc_shift"), trend = num("cc_trend");
  const C = 50, s = 2, UCL = C + 3 * s, LCL = C - 3 * s;
  const pts = simNoise.map((n, i) => C + n * s + (i >= 15 ? shift * s : 0) + trend * i * 0.4);
  const yMin = LCL - 4, yMax = UCL + 4;
  const X = (i) => pad + (W - pad - 10) * i / (pts.length - 1);
  const Y = (v) => pad + (H - 2 * pad) * (1 - (v - yMin) / (yMax - yMin));
  ctx.clearRect(0, 0, W, H);
  // limit + center lines
  const line = (v, col, dash) => { ctx.strokeStyle = col; ctx.setLineDash(dash); ctx.beginPath();
    ctx.moveTo(pad, Y(v)); ctx.lineTo(W - 10, Y(v)); ctx.stroke(); ctx.setLineDash([]); };
  line(UCL, "#c00000", [5, 4]); line(LCL, "#c00000", [5, 4]); line(C, "#2e7d32", []);
  ctx.fillStyle = "#c00000"; ctx.font = "11px sans-serif";
  ctx.fillText("UCL", W - 34, Y(UCL) - 3); ctx.fillText("LCL", W - 34, Y(LCL) + 12);
  // series
  ctx.strokeStyle = "#1f4e79"; ctx.beginPath();
  pts.forEach((v, i) => { i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v)); }); ctx.stroke();
  let ooc = 0;
  pts.forEach((v, i) => { const bad = v > UCL || v < LCL; if (bad) ooc++;
    ctx.fillStyle = bad ? "#c00000" : "#1f4e79"; ctx.beginPath();
    ctx.arc(X(i), Y(v), bad ? 5 : 3.2, 0, 7); ctx.fill(); });
  // run of 8 on one side
  let run = 1, runHit = false;
  for (let i = 1; i < pts.length; i++) {
    run = (Math.sign(pts[i] - C) === Math.sign(pts[i - 1] - C)) ? run + 1 : 1;
    if (run >= 8) runHit = true;
  }
  const sig = [];
  if (ooc) sig.push(`${ooc} point(s) beyond limits`);
  if (runHit) sig.push("run of 8+ on one side (shift)");
  document.getElementById("cc_out").innerHTML = sig.length
    ? `<span class="verdict bad" style="display:inline-block">⚠ Out of control: ${sig.join(" · ")}</span>`
    : `<span class="verdict good" style="display:inline-block">✓ In control — only common-cause variation</span>`;
}

function routeTools() {
  app.innerHTML = `<h1>🧰 QE Tools</h1>
    <div class="toolcard"><h3>Process Capability (Cp / Cpk)</h3>
      <div class="inrow">
        <label>LSL<input id="cp_lsl" type="number" value="9.6" step="0.1"></label>
        <label>USL<input id="cp_usl" type="number" value="10.4" step="0.1"></label>
        <label>Mean<input id="cp_mean" type="number" value="10.08" step="0.01"></label>
        <label>σ<input id="cp_sigma" type="number" value="0.1" step="0.01"></label>
      </div><div id="cp_out" class="toolout"></div></div>

    <div class="toolcard"><h3>Gauge R&amp;R</h3>
      <div class="muted small">Enter the standard deviations (equipment, appraiser, part).</div>
      <div class="inrow">
        <label>EV (repeat.)<input id="grr_ev" type="number" value="0.9" step="0.1"></label>
        <label>AV (reprod.)<input id="grr_av" type="number" value="0.6" step="0.1"></label>
        <label>PV (part)<input id="grr_pv" type="number" value="5.0" step="0.1"></label>
      </div><div id="grr_out" class="toolout"></div></div>

    <div class="toolcard"><h3>Control-Chart Simulator</h3>
      <div class="muted small">Drag the sliders to inject a shift or trend after point 15 and watch the rules trip.</div>
      <canvas id="ccsim" width="600" height="220" class="ccsim"></canvas>
      <div class="inrow">
        <label>Mean shift (σ)<input id="cc_shift" type="range" min="0" max="4" step="0.1" value="0"></label>
        <label>Trend slope<input id="cc_trend" type="range" min="0" max="0.8" step="0.05" value="0"></label>
      </div>
      <button class="primary" id="cc_new">🎲 New data</button>
      <div id="cc_out" class="toolout"></div></div>`;
  ["cp_usl", "cp_lsl", "cp_mean", "cp_sigma"].forEach((id) => document.getElementById(id).addEventListener("input", computeCp));
  ["grr_ev", "grr_av", "grr_pv"].forEach((id) => document.getElementById(id).addEventListener("input", computeGrr));
  ["cc_shift", "cc_trend"].forEach((id) => document.getElementById(id).addEventListener("input", drawCC));
  document.getElementById("cc_new").addEventListener("click", () => { genNoise(); drawCC(); });
  computeCp(); computeGrr(); genNoise(); drawCC();
}

// ---------------------------------------------------------------- AI tutor chat
function renderChat() {
  const c = document.getElementById("chat"); if (!c) return;
  c.innerHTML = tutorMsgs.map((m) =>
    `<div class="msg ${m.role}"><div class="bubble">${esc(m.text)}${
      m.sources && m.sources.length ? `<div class="src2">📚 ${m.sources.map((s) => esc(s.book) + " p" + s.page).join(" · ")}</div>` : ""}</div></div>`).join("");
  c.scrollTop = c.scrollHeight;
}
async function routeTutor() {
  const st = await api("/api/tutor/status");
  let h = `<h1>🤖 AI Tutor</h1>`;
  h += st.enabled
    ? `<div class="crumb">Ask anything about quality engineering — grounded in your books.</div>`
    : `<div class="empty">🔑 The AI Tutor needs your Anthropic API key.<br>Add <b>ANTHROPIC_API_KEY</b> to <code>~/qe-trainer/.env</code> and restart the server, then ask me anything.</div>`;
  h += `<a class="primary" href="#/interview">🎤 QE Mock Interview ›</a>
    <div id="chat" class="chat"></div>
    <div class="askbar">
      <input id="askq" placeholder="e.g. When do I use a u-chart vs a c-chart?" ${st.enabled ? "" : "disabled"}>
      <button class="primary" id="asksend" ${st.enabled ? "" : "disabled"}>Ask</button>
    </div>`;
  app.innerHTML = h;
  renderChat();
  const send = async () => {
    const inp = document.getElementById("askq"); const q = inp.value.trim(); if (!q) return;
    tutorMsgs.push({ role: "you", text: q });
    tutorMsgs.push({ role: "tutor", text: "…" });
    inp.value = ""; renderChat();
    const r = await post("/api/tutor/ask", { question: q });
    tutorMsgs[tutorMsgs.length - 1] = { role: "tutor", text: r.answer || r.feedback, sources: r.sources };
    renderChat();
  };
  document.getElementById("asksend")?.addEventListener("click", send);
  document.getElementById("askq")?.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
}

// ---------------------------------------------------------------- read & master
async function routeMaster(tid) {
  const m = await api("/api/master/" + tid);
  if (m.error && !m.passages) return routeHome();
  masterState = { tid };
  let h = `<a class="back" href="#/lesson/${tid}">‹ Lesson</a>
    <h1>🎓 Master: ${esc(m.title)}</h1>
    <div class="crumb">${esc(m.source)}${m.mastered ? " · ✅ already mastered" : ""}</div>
    <h3>📖 Read the source</h3>`;
  h += (m.passages && m.passages.length)
    ? m.passages.map((p) => `<div class="passage"><div class="psrc">${esc(p.book)} · p${p.page}</div>${esc(p.text)}</div>`).join("")
    : `<div class="muted small">(No source passages indexed for this topic — use the lesson reading.)</div>`;
  if (m.need_key) {
    h += `<div class="empty">🔑 The open-ended mastery test needs the AI (Anthropic key). Reading is available; grading activates once the key is set.</div>`;
    app.innerHTML = h; window.scrollTo(0, 0); return;
  }
  h += `<h3>✍️ Prove it — in your own words</h3>
    <div class="crumb">Open-ended: explain your reasoning. Pass all to master this topic.</div>`;
  (m.questions || []).forEach((q, i) => {
    h += `<div class="mq" data-q="${esc(q)}"><div class="q">${i + 1}. ${esc(q)}</div>
      <textarea class="mq-input" placeholder="Your answer…"></textarea></div>`;
  });
  h += `<button class="primary big" data-act="msubmit">Submit for grading</button><div id="mresult"></div>`;
  app.innerHTML = h; window.scrollTo(0, 0);
}

// ---------------------------------------------------------------- exams + certificate
async function routeExam(module) {
  const ex = await api("/api/exam/" + module);
  if (ex.error) return routeHome();
  examState = { module, count: ex.questions.length, answers: {} };
  let h = `<a class="back" href="#/exams">‹ Exams</a>
    <h1>📝 ${ex.emoji} ${esc(ex.title)}</h1>
    <div class="crumb">${ex.questions.length} questions · pass at ${ex.pass_pct}%. Answer each, then submit.</div>`;
  ex.questions.forEach((q, i) => {
    h += `<div class="exq" data-id="${q.item_id}"><div class="q">${i + 1}. ${esc(q.q)}</div>
      <div class="choices">${q.choices.map((c, j) =>
        `<button data-act="exchoose" data-i="${j}">${ABCD[j]}. ${esc(c)}</button>`).join("")}</div></div>`;
  });
  h += `<button class="primary big" data-act="exsubmit">Submit exam</button><div id="exresult"></div>`;
  app.innerHTML = h; window.scrollTo(0, 0);
}

async function routeExams() {
  const e = await api("/api/exams");
  let h = `<h1>📝 Exams</h1>
    <div class="crumb">${e.passed_count}/${e.total_modules} unit exams passed${e.certificate_ready ? " — course complete! 🎉" : ""}</div>`;
  if (e.certificate_ready)
    h += `<a class="primary big done" href="#/certificate">🎓 View your Certificate</a>`;
  h += `<div class="lessons">`;
  for (const m of e.modules)
    h += `<a class="lrow ${m.passed ? "done" : ""}" href="#/exam/${m.id}">
      <div class="n">${m.passed ? "✓" : "📝"}</div>
      <div class="lt">${m.emoji} ${esc(m.title)}<div class="media-dot">${m.quiz_count} questions${m.best ? " · best " + m.best : ""}</div></div>
      <div class="chev">${m.passed ? "PASSED" : "Take ›"}</div></a>`;
  app.innerHTML = h + "</div>";
}

async function routeCertificate() {
  const e = await api("/api/exams");
  let h = `<a class="back" href="#/exams">‹ Exams</a>`;
  if (!e.certificate_ready) {
    h += `<div class="empty">🔒 Pass all ${e.total_modules} unit exams to unlock your certificate.<br>
      You've passed <b>${e.passed_count}</b> so far — keep going!</div>`;
    app.innerHTML = h; return;
  }
  const d = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  h += `<div class="cert">
    <div class="cert-emoji">🎓</div>
    <div class="cert-kicker">Certificate of Completion</div>
    <div class="cert-sub">This certifies that</div>
    <div class="cert-name">Jacob</div>
    <div class="cert-sub">has completed</div>
    <div class="cert-course">QE Academy</div>
    <div class="cert-body">Mastering all ${e.total_modules} units of Quality Engineering — SPC, Process
      Variation, Capability &amp; Validation, MSA, DOE, GD&amp;T, FMEA, APQP, and structured problem-solving.</div>
    <div class="cert-date">${d}</div>
  </div>
  <div class="crumb" style="text-align:center">Screenshot this to keep it. 🏆</div>`;
  app.innerHTML = h;
}

// ---------------------------------------------------------------- mock interview
function renderInterview() {
  const c = document.getElementById("chat"); if (!c) return;
  c.innerHTML = interviewMsgs.map((m) =>
    `<div class="msg ${m.role === "you" ? "you" : "tutor"}"><div class="bubble">${esc(m.text)}</div></div>`).join("");
  c.scrollTop = c.scrollHeight;
}
async function interviewTurn(userText) {
  if (userText) interviewMsgs.push({ role: "you", text: userText });
  interviewMsgs.push({ role: "interviewer", text: "…" });
  renderInterview();
  const r = await post("/api/interview", { history: interviewMsgs.filter((m) => m.text !== "…") });
  interviewMsgs[interviewMsgs.length - 1] = { role: "interviewer", text: r.reply };
  renderInterview();
}
async function routeInterview() {
  let h = `<a class="back" href="#/tutor">‹ Tutor</a><h1>🎤 Mock Interview</h1>
    <div class="crumb">A realistic QE interview — answer each question, get feedback + a harder follow-up.
    <a href="#" id="ivrestart">↺ restart</a></div>
    <div id="chat" class="chat"></div>
    <div class="askbar"><input id="ivq" placeholder="Type your answer…"><button class="primary" id="ivsend">Send</button></div>`;
  app.innerHTML = h;
  renderInterview();
  if (!interviewMsgs.length) await interviewTurn();
  const send = async () => { const inp = document.getElementById("ivq"); const v = inp.value.trim(); if (!v) return; inp.value = ""; await interviewTurn(v); };
  document.getElementById("ivsend").addEventListener("click", send);
  document.getElementById("ivq").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  document.getElementById("ivrestart").addEventListener("click", async (e) => { e.preventDefault(); interviewMsgs = []; renderInterview(); await interviewTurn(); });
}

// ---------------------------------------------------------------- source library
async function routeLibrary() {
  if (!LIB) LIB = await api("/api/library");
  let h = `<h1>📚 Source Library</h1><div class="crumb">Your actual QE books — read the source itself.</div><div class="lessons">`;
  for (const b of (LIB.books || []))
    h += `<a class="lrow" href="#/read/${b.id}"><div class="n">📖</div>
      <div class="lt">${esc(b.title)}<div class="media-dot">${esc(b.author)} · ${esc(b.units)}</div></div>
      <div class="chev">›</div></a>`;
  if (!LIB.books || !LIB.books.length) h += `<div class="empty">No books are embedded yet.</div>`;
  app.innerHTML = h + "</div>";
}
async function routeRead(id) {
  if (!LIB) LIB = await api("/api/library");
  const b = (LIB.books || []).find((x) => x.id === id);
  app.innerHTML = `<a class="back" href="#/library">‹ Library</a>
    <h1 class="readh">📖 ${esc(b ? b.title : id)}</h1>
    <a class="primary" href="/pdfs/${id}.pdf" target="_blank" rel="noopener">Open full-screen ↗</a>
    <iframe class="pdfframe" src="/pdfs/${id}.pdf" title="book"></iframe>
    <div class="crumb">On iPhone, tap “Open full-screen” for the best reading view.</div>`;
}

// ---------------------------------------------------------------- router
function setTab(name) {
  document.querySelectorAll("#tabbar a").forEach((a) =>
    a.classList.toggle("active", a.dataset.tab === name));
}
async function router() {
  const parts = (location.hash || "#/").slice(1).split("/").filter(Boolean); // e.g. ['unit','spc']
  app.innerHTML = `<div class="loading">Loading…</div>`;
  try {
    if (parts[0] === "unit") { setTab(""); await routeUnit(parts[1]); }
    else if (parts[0] === "lesson") { setTab(""); await routeLesson(parts[1]); }
    else if (parts[0] === "master") { setTab(""); await routeMaster(parts[1]); }
    else if (parts[0] === "library") { setTab("home"); await routeLibrary(); }
    else if (parts[0] === "read") { setTab("home"); await routeRead(parts[1]); }
    else if (parts[0] === "review") { setTab("review"); await routeReview(); }
    else if (parts[0] === "drill") { setTab("review"); await routeDrill(); }
    else if (parts[0] === "tools") { setTab("tools"); routeTools(); }
    else if (parts[0] === "tutor") { setTab("tutor"); await routeTutor(); }
    else if (parts[0] === "interview") { setTab("tutor"); await routeInterview(); }
    else if (parts[0] === "exam") { setTab("progress"); await routeExam(parts[1]); }
    else if (parts[0] === "exams") { setTab("progress"); await routeExams(); }
    else if (parts[0] === "certificate") { setTab("progress"); await routeCertificate(); }
    else if (parts[0] === "progress") { setTab("progress"); await routeProgress(); }
    else { setTab("home"); await routeHome(); }
  } catch (err) {
    app.innerHTML = `<div class="empty">Couldn't load.<br>${esc(err.message)}<br><br>
      <a class="back" href="#/">‹ Home</a></div>`;
  }
}
// ---------------------------------------------------------------- display prefs
function setupPrefs() {
  let p = {};
  try { p = JSON.parse(localStorage.getItem("qe-prefs") || "{}"); } catch (e) {}
  p.theme = p.theme || "light"; p.size = p.size || "md"; p.font = p.font || "sans";
  const apply = () => {
    const d = document.documentElement;
    d.dataset.theme = p.theme; d.dataset.size = p.size; d.dataset.font = p.font;
    document.querySelectorAll("#prefs .seg").forEach((seg) =>
      seg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.v === p[seg.dataset.pref])));
    localStorage.setItem("qe-prefs", JSON.stringify(p));
  };
  apply();
  document.getElementById("prefsbtn").addEventListener("click", () => document.getElementById("prefs").classList.toggle("hidden"));
  document.getElementById("prefsdone").addEventListener("click", () => document.getElementById("prefs").classList.add("hidden"));
  document.querySelectorAll("#prefs .seg button").forEach((b) =>
    b.addEventListener("click", () => { p[b.parentElement.dataset.pref] = b.dataset.v; apply(); }));
}
setupPrefs();

window.addEventListener("hashchange", router);
router();
