/* Sorbo — las noticias en un sorbo. App web instalable (sin frameworks). */
"use strict";

const VERSION = "1.0.0";
const GOAL = 5;
const FIELD = {
  chile: "roast", negocios: "roast", startups: "roast",
  mundo: "olive", planeta: "olive", ciencia: "olive", salud: "olive",
  fintech: "leaf", ia: "leaf", tecnologia: "leaf",
  deportes: "caramel", cultura: "caramel",
};
const DEFAULT_INTERESTS = ["negocios", "fintech", "ia"];
const SUGGESTIONS = ["Banco Central", "Startups", "Inteligencia artificial", "Bitcoin", "Mercados", "Litio", "Fútbol", "Clima"];
const DAYS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

const $main = document.getElementById("main");
const $layer = document.getElementById("layer");
let ED = null;            // la edición del día
let tab = "hoy";
let homeFilter = "top";
let foryouEditing = false;
let searchQuery = "";
let installEvent = null;

/* ---------------------------------------------------------- guardado local */
const store = {
  get(k, d) { try { const v = localStorage.getItem("sorbo." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("sorbo." + k, JSON.stringify(v)); } catch { /* sin espacio o modo privado */ } },
};

/* ------------------------------------------------------------- utilidades */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const field = (cat) => FIELD[cat] || "roast";
const catName = (cat) => (ED && ED.categories[cat] ? ED.categories[cat].name : "Noticias");
const art = (id) => (ED && ED.articles[id]) || store.get("saved", []).find((a) => a.id === id);
const todayKey = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

function edition() {
  const h = new Date().getHours();
  return h < 12 ? "Edición de la mañana" : h < 20 ? "Edición de la tarde" : "Edición de la noche";
}
function today() { const d = new Date(); return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`; }
function ago(ts) {
  const m = Math.floor((Date.now() / 1000 - ts) / 60);
  if (m < 1) return "ahora";
  if (m < 60) return `hace ${m} min`;
  if (m < 1440) return `hace ${Math.floor(m / 60)} h`;
  return `hace ${Math.floor(m / 1440)} d`;
}
function titleSize(t, big) { const n = t.length; return n <= 60 ? big : n <= 95 ? big - 3 : n <= 130 ? big - 6 : big - 9; }
function meta(a, showCat = true) {
  const bits = [esc(a.source), ago(a.published)];
  if (a.lang === "en") bits.push("en inglés");
  return `<div class="meta">${showCat ? `<b>${esc(catName(a.category))}</b> · ` : ""}${bits.join(" · ")}</div>`;
}
function img(a, cls) {
  if (!a.image) return "";
  return `<img class="${cls}" src="${esc(a.image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">`;
}
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2400);
}
const icon = {
  back: '<svg viewBox="0 0 24 24"><path d="M15 5 8 12l7 7"/></svg>',
  close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  share: '<svg viewBox="0 0 24 24"><path d="M12 15V4M8 8l4-4 4 4"/><path d="M5 12v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></svg>',
  save: '<svg viewBox="0 0 24 24"><path d="M6 4h12v16l-6-4-6 4V4Z"/></svg>',
  saved: '<svg viewBox="0 0 24 24"><path d="M6 4h12v16l-6-4-6 4V4Z" fill="currentColor"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/></svg>',
  refresh: '<svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>',
};

/* ------------------------------------------------------- racha y lecturas */
function readLog() { return store.get("read", {}); }
function readToday() { return (readLog()[todayKey()] || []).length; }
function streak() {
  const log = readLog(); const d = new Date();
  if (!(log[todayKey(d)] || []).length) d.setDate(d.getDate() - 1);
  let n = 0;
  while ((log[todayKey(d)] || []).length) { n++; d.setDate(d.getDate() - 1); }
  return n;
}
function markRead(id) {
  const log = readLog(); const k = todayKey();
  const before = (log[k] || []).length;
  log[k] = log[k] || [];
  if (!log[k].includes(id)) log[k].push(id);
  const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - 30);
  for (const key of Object.keys(log)) if (key < todayKey(cutoff)) delete log[key];
  store.set("read", log);
  if (before < GOAL && log[k].length >= GOAL) toast(`Meta del día cumplida. Racha de ${streak()} días`);
}

/* --------------------------------------------------------------- datos */
async function loadEdition() {
  try {
    const res = await fetch(`data/edition.json?t=${Math.floor(Date.now() / 600000)}`, { cache: "no-cache" });
    if (!res.ok) throw new Error(res.status);
    ED = await res.json();
    store.set("edition_cache", ED);
  } catch (e) {
    ED = store.get("edition_cache", null);       // sin internet: la última edición
    if (ED) toast("Sin conexión: mostrando la última edición");
  }
}

/* ============================================================ PANTALLAS */
function render(keep = false) {
  document.querySelectorAll(".tabbar button").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  if (!ED) { $main.innerHTML = ED === null ? errorView() : skeleton(); return; }
  const views = { hoy: homeView, parati: foryouView, buscar: searchView, guardadas: savedView };
  $main.innerHTML = `<div class="view">${views[tab]()}</div>`;
  if (tab === "buscar") bindSearch();
  if (!keep) window.scrollTo(0, 0);
}

function skeleton() {
  const row = `<div class="row"><div class="x"><div class="sk" style="height:18px;margin-bottom:8px"></div><div class="sk" style="height:18px;width:70%;margin-bottom:10px"></div><div class="sk" style="height:12px;width:40%"></div></div><div class="sk" style="width:88px;height:88px;border-radius:12px"></div></div>`;
  return `${header()}<div class="sk" style="height:360px;border-radius:0;margin-top:14px"></div>
    <p class="soft" style="padding:16px 20px 4px;font-size:14px">Preparando tu edición…</p>${row}${row}`;
}
function errorView() {
  return `${header()}<div class="empty"><h2 class="serif">Sin conexión</h2>
    <p class="soft">No pudimos traer las noticias. Revisa tu internet e intenta de nuevo.</p><br>
    <button class="pill" data-act="reload">Reintentar</button></div>`;
}

function header() {
  return `<header class="top">
    <div><div class="wordmark">sorbo<i></i></div><div class="edition">${edition()} · ${today()}</div></div>
    <div class="top-actions">
      <button class="icon-btn soft" data-act="about" aria-label="Acerca de Sorbo">${icon.info}</button>
    </div></header>`;
}
function goalBar() {
  const done = readToday(), ok = done >= GOAL;
  const n = streak();
  return `<div class="goal"><div class="goal-row"><b>${ok ? "Meta del día cumplida" : `${done} de ${GOAL} leídas hoy`}</b>
    <button class="streak" data-act="streak">Racha de ${n} ${n === 1 ? "día" : "días"}</button></div>
    <div class="track ${ok ? "done" : ""}"><i style="width:${Math.min(100, (done / GOAL) * 100)}%"></i></div></div>`;
}
function installCard() {
  const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  if (standalone || store.get("install_hidden", false)) return "";
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const how = installEvent ? `<button class="pill" data-act="install">Instalar</button>`
    : `<span>${ios ? "En Safari toca <b>Compartir</b> y luego <b>Agregar a inicio</b>." : "En el menú del navegador elige <b>Instalar app</b> o <b>Agregar a pantalla de inicio</b>."}</span>`;
  return `<div class="install"><div style="flex:1"><b>Ten Sorbo como app.</b> ${installEvent ? "Queda en tu pantalla de inicio." : how}</div>
    ${installEvent ? how : ""}<button class="icon-btn soft" data-act="install-hide" aria-label="Ocultar">${icon.close}</button></div>`;
}

function row(a) {
  return `<button class="row" data-open="${a.id}"><div class="x"><h3>${esc(a.title)}</h3>${meta(a)}</div>${img(a, "thumb")}</button>`;
}
function hero(a, h = 380) {
  if (a.image) {
    return `<button class="hero photo" data-open="${a.id}" style="min-height:${h}px">${img(a, "")}
      <div class="txt"><h1 class="serif" style="font-size:${titleSize(a.title, 30)}px">${esc(a.title)}</h1>${meta(a)}</div></button>`;
  }
  return `<button class="hero flat f-${field(a.category)}" data-open="${a.id}" style="min-height:${h - 60}px">
    <div class="txt"><h1 class="serif" style="font-size:${titleSize(a.title, 36)}px">${esc(a.title)}</h1>${meta(a)}</div></button>`;
}
function chips(items, selected, act) {
  return `<div class="chips">${items.map(([k, label]) =>
    `<button class="chip ${k === selected ? "on" : ""}" data-act="${act}" data-k="${esc(k)}">${esc(label)}</button>`).join("")}</div>`;
}

/* ---------------------------------------------------------------- HOY */
function homeView() {
  const items = [["top", "Lo importante"], ...Object.entries(ED.categories).map(([k, c]) => [k, c.name])];
  let html = header() + installCard() + goalBar() + chips(items, homeFilter, "filter");
  if (homeFilter === "top") {
    const top = ED.top.map(art).filter(Boolean);
    if (!top.length) return html + `<div class="empty"><h2 class="serif">Aún no hay edición</h2><p class="soft">Vuelve en unos minutos.</p></div>`;
    html += hero(top[0]);
    html += `<button class="block espresso" data-act="espresso"><div><h2 class="serif">Tu espresso</h2><p>Las 5 del día en un minuto.</p></div><span class="pill">Empezar</span></button>`;
    html += `<div class="section"><h2 class="serif">Lo más importante</h2></div>` + top.slice(1, 6).map(row).join("");
    if (ED.fact || ED.quiz.length >= 2) html += `<div style="height:24px"></div>`;
    if (ED.fact) {
      const a = art(ED.fact.id);
      html += `<button class="fact" data-open="${ED.fact.id}"><div class="k">Dato del día<span data-act="share-fact" class="icon-btn" aria-label="Compartir dato">${icon.share}</span></div>
        <div class="n" style="${ED.fact.number.length > 12 ? "font-size:44px" : ""}">${esc(ED.fact.number)}</div><p>${esc(ED.fact.text)}</p>
        <small>${esc(a ? a.source : "")} · toca para leer la nota</small></button>`;
    }
    if (ED.quiz.length >= 2) {
      const score = store.get("quiz", {})[todayKey()];
      html += `<div class="quizbox"><h2 class="serif">Quiz del día</h2>
        <p>${score === undefined ? `${ED.quiz.length} preguntas sobre lo que pasó hoy. ¿Estás al día?` : `Hoy sacaste ${score} de ${ED.quiz.length}. Mañana hay uno nuevo.`}</p>
        <button class="pill" data-act="quiz">${score === undefined ? "Jugar" : "Jugar de nuevo"}</button></div>`;
    }
    const shown = new Set(ED.top.slice(0, 6));
    for (const cid of ["chile", "mundo", "negocios"]) {
      const arts = (ED.categories[cid]?.ids || []).filter((id) => !shown.has(id)).slice(0, 4).map(art).filter(Boolean);
      if (!arts.length) continue;
      html += `<div class="section"><h2 class="serif">${esc(catName(cid))}</h2><button class="link" data-act="filter" data-k="${cid}">Ver todo</button></div>`;
      html += arts.map(row).join("");
    }
  } else {
    const arts = (ED.categories[homeFilter]?.ids || []).map(art).filter(Boolean);
    if (!arts.length) return html + `<div class="empty"><h2 class="serif">Nada por ahora</h2><p class="soft">Vuelve en unos minutos.</p></div>`;
    html += hero(arts[0], 340) + `<div style="height:8px"></div>` + arts.slice(1).map(row).join("");
  }
  return html;
}

/* ------------------------------------------------------------- PARA TI */
function foryouView() {
  const interests = store.get("interests", null);
  if (!interests || foryouEditing) return pickerView("Armar mi revista");
  let html = `<div class="title"><div><h1 class="serif">Para ti</h1><p>Tu revista de hoy, con tus temas</p></div>
    <button class="link" data-act="edit-topics">Editar temas</button></div>`;
  for (const cid of interests) {
    const ids = ED.categories[cid]?.ids || [];
    if (!ids.length) continue;
    const f = field(cid);
    html += `<section class="mag f-${f}"><div class="mag-head"><h2 class="serif">${esc(catName(cid))}</h2><span>${ids.length} hoy</span></div>
      <div class="cards">${ids.slice(0, 10).map(art).filter(Boolean).map((a) => `
        <button class="card" data-open="${a.id}">${a.image ? img(a, "") : `<div class="noimg f-${f}">${esc(catName(cid))}</div>`}
          <h3>${esc(a.title)}</h3>${meta(a, false)}</button>`).join("")}</div></section>`;
  }
  return html;
}
function pickerView(button) {
  const sel = new Set(store.get("interests", null) || DEFAULT_INTERESTS);
  pickerView.sel = sel;
  return `<div class="title"><div><h1 class="serif">¿Qué te interesa?</h1><p>Elige tus temas y armamos tu revista diaria.</p></div></div>
    <div class="picker">${Object.entries(ED.categories).map(([k, c]) =>
      `<button class="topic ${sel.has(k) ? "on f-" + field(k) : ""}" data-act="topic" data-k="${k}"><small>${sel.has(k) ? "Elegido" : "Agregar"}</small><span>${esc(c.name)}</span></button>`).join("")}</div>
    <div style="padding:16px var(--pad)"><button class="pill wide" data-act="save-topics"><span>${button}</span><span>→</span></button></div>`;
}

/* -------------------------------------------------------------- BUSCAR */
function searchView() {
  return `<div class="title"><div><h1 class="serif">Buscar</h1><p>En todas las noticias de la edición</p></div></div>
    <label class="search">${icon.search}<input id="q" type="search" placeholder="Un tema, empresa o persona" value="${esc(searchQuery)}" enterkeyhint="search" autocomplete="off"></label>
    ${chips(SUGGESTIONS.map((s) => [s, s]), null, "suggest").replace('class="chips"', 'class="chips wrap"')}
    <div id="results">${searchResults()}</div>`;
}
function searchResults() {
  const q = norm(searchQuery.trim());
  if (!q) return "";
  const words = q.split(/\s+/);
  const hits = Object.values(ED.articles).filter((a) => { const t = norm(a.title + " " + a.summary); return words.every((w) => t.includes(w)); })
    .sort((a, b) => b.published - a.published).slice(0, 40);
  const gn = `https://news.google.com/search?q=${encodeURIComponent(searchQuery)}&hl=es-419&gl=CL&ceid=CL:es-419`;
  return (hits.length ? `<div class="section"><h2 class="serif">${hits.length} ${hits.length === 1 ? "resultado" : "resultados"}</h2></div>` + hits.map(row).join("")
    : `<div class="empty"><h2 class="serif">Sin resultados hoy</h2><p class="soft">No hay noticias sobre “${esc(searchQuery)}” en la edición de hoy.</p></div>`)
    + `<div style="padding:16px var(--pad)"><a class="pill tone wide" href="${gn}" target="_blank" rel="noopener"><span>Buscar en todo el mundo</span><span>↗</span></a></div>`;
}
function bindSearch() {
  const input = document.getElementById("q");
  input.addEventListener("input", () => { searchQuery = input.value; document.getElementById("results").innerHTML = searchResults(); });
}

/* ----------------------------------------------------------- GUARDADAS */
function savedView() {
  const saved = store.get("saved", []);
  return `<div class="title"><div><h1 class="serif">Guardadas</h1><p>${saved.length} ${saved.length === 1 ? "noticia" : "noticias"} para leer después</p></div></div>`
    + (saved.length ? saved.slice().reverse().map(row).join("")
      : `<div class="empty"><h2 class="serif">Tu lista está vacía</h2><p class="soft">Toca el marcador en cualquier noticia y quedará aquí para leerla con calma.</p></div>`);
}
function isSaved(id) { return store.get("saved", []).some((a) => a.id === id); }
function toggleSave(id) {
  let saved = store.get("saved", []);
  if (saved.some((a) => a.id === id)) { saved = saved.filter((a) => a.id !== id); toast("Quitada de guardadas"); }
  else { const a = art(id); if (a) saved.push(a); toast("Guardada para después"); }
  store.set("saved", saved.slice(-200));
}

/* ============================================================== CAPAS */
const stack = [];
function openLayer(html, cls = "overlay", onClose) {
  const el = document.createElement("div");
  el.className = cls; el.innerHTML = html;
  $layer.appendChild(el);
  stack.push({ el, onClose });
  history.pushState({ layer: stack.length }, "");
  document.body.style.overflow = "hidden";
  return el;
}
function closeLayer(fromHistory = false) {
  const top = stack.pop();
  if (!top) return;
  top.el.remove();
  if (!stack.length) document.body.style.overflow = "";
  if (top.onClose) top.onClose();
  if (!fromHistory) history.back();
}
addEventListener("popstate", () => { if (stack.length) closeLayer(true); });

/* ----------------------------------------------------------- la nota */
function openArticle(id) {
  const a = art(id);
  if (!a) return;
  markRead(id);
  const points = a.bullets && a.bullets.length ? a.bullets : (a.summary ? [a.summary] : []);
  const f = field(a.category);
  const head = a.image
    ? `${img(a, "photo")}<div class="head"><h1 class="serif" style="font-size:${titleSize(a.title, 30)}px">${esc(a.title)}</h1>${meta(a)}</div>`
    : `<div class="flathead f-${f}"><h1 class="serif" style="font-size:${titleSize(a.title, 34)}px">${esc(a.title)}</h1>${meta(a)}</div><div style="height:16px"></div>`;
  const translate = a.lang === "en"
    ? `<a class="pill tone wide" target="_blank" rel="noopener" href="https://translate.google.com/translate?sl=auto&tl=es&u=${encodeURIComponent(a.link)}"><span>Leerla traducida al español</span><span>↗</span></a>` : "";
  const el = openLayer(`<div class="wrap article">
    <div class="bar"><button class="icon-btn" data-act="close" aria-label="Volver">${icon.back}</button><span class="src">${esc(a.source)}</span>
      <button class="icon-btn" data-act="share" data-id="${a.id}" aria-label="Compartir">${icon.share}</button>
      <button class="icon-btn" data-act="save" data-id="${a.id}" aria-label="Guardar">${isSaved(a.id) ? icon.saved : icon.save}</button></div>
    ${head}
    ${points.length ? `<div class="short"><h2 class="serif">En corto</h2><ul>${points.map((p) => `<li>${esc(p)}</li>`).join("")}</ul></div>`
      : `<div class="short"><p class="soft">Este medio no comparte un resumen. Puedes leer la nota completa en su sitio.</p></div>`}
    <div class="actions">
      <a class="pill dark wide" href="${esc(a.link)}" target="_blank" rel="noopener"><span>Leer la nota completa en ${esc(a.source)}</span><span>↗</span></a>
      ${translate}
      <p class="note">Sorbo te muestra el resumen; la nota completa es de ${esc(a.source)}.</p>
    </div></div>`, "overlay", () => { if (!stack.length) render(true); });
  el.querySelector(".wrap").scrollTop = 0;
}
async function share(id) {
  const a = art(id); if (!a) return;
  const data = { title: a.title, text: `${a.title} — vía Sorbo`, url: a.link };
  try {
    if (navigator.share) await navigator.share(data);
    else { await navigator.clipboard.writeText(`${a.title}\n${a.link}\n\nVía Sorbo`); toast("Link copiado"); }
  } catch { /* cancelado */ }
}

/* ------------------------------------------------------- tu espresso */
function openEspresso() {
  const stories = ED.top.slice(0, 5).map(art).filter(Boolean);
  if (!stories.length) return;
  let i = 0;
  const el = openLayer(`<div class="wrap" id="esp"></div>`, "overlay", () => { if (!stack.length) render(true); });
  const paint = () => {
    const a = stories[i]; markRead(a.id);
    const f = field(a.category);
    el.className = `overlay f-${f}`;
    const text = a.bullets && a.bullets.length ? a.bullets.slice(0, 2).join(" ") : (a.summary || "").slice(0, 240);
    el.querySelector("#esp").innerHTML = `<div class="story">
      <div class="bars">${stories.map((_, j) => `<i class="${j <= i ? "on" : ""}"></i>`).join("")}
        <button class="icon-btn" data-act="close" aria-label="Cerrar">${icon.close}</button></div>
      ${a.image ? `<img class="img" src="${esc(a.image)}" alt="" referrerpolicy="no-referrer" onerror="this.remove()">` : ""}
      <div class="body" data-tap="1"><div class="k">${i + 1} de ${stories.length} · ${esc(catName(a.category))}</div>
        <h2 class="serif" style="font-size:${titleSize(a.title, a.image ? 32 : 40)}px">${esc(a.title)}</h2><p>${esc(text)}</p></div>
      <div class="foot"><span>${esc(a.source)} · ${ago(a.published)}</span><button class="pill light" data-open="${a.id}">Leer nota</button></div></div>`;
  };
  el.addEventListener("click", (e) => {
    if (e.target.closest("button, a")) return;
    const back = e.clientX < innerWidth / 3;
    if (back) { if (i > 0) { i--; paint(); } return; }
    if (i < stories.length - 1) { i++; paint(); } else { closeLayer(); toast("Listo, ya estás al día"); }
  });
  paint();
}

/* --------------------------------------------------------------- quiz */
function openQuiz() {
  const qs = ED.quiz; if (!qs.length) return;
  let i = 0, score = 0, answered = false;
  const el = openLayer(`<div class="wrap quiz" id="qz"></div>`, "overlay", () => { if (!stack.length) render(true); });
  const box = el.querySelector("#qz");
  const paint = () => {
    const q = qs[i]; answered = false;
    box.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><span class="serif" style="font-size:22px">Quiz del día</span>
      <button class="icon-btn" data-act="close" aria-label="Cerrar">${icon.close}</button></div>
      <p style="color:var(--on-dark-soft);font-weight:600;font-size:14px;margin-top:6px">Pregunta ${i + 1} de ${qs.length} · Completa el titular</p>
      <h2 class="serif q" style="font-size:${titleSize(q.question, 30)}px">${esc(q.question)}</h2>
      <div>${q.options.map((o) => `<button class="opt" data-opt="${esc(o)}">${esc(o)}</button>`).join("")}</div><div class="fb"></div>`;
  };
  const finish = () => {
    const log = store.get("quiz", {}); log[todayKey()] = score; store.set("quiz", log);
    const msg = score === qs.length ? "Puntaje perfecto. Hoy nadie te gana en conversación."
      : score ? "Bien. Mañana vas por el puntaje perfecto." : "Hoy no salió, pero ahora ya lo sabes.";
    box.innerHTML = `<div style="display:flex;flex-direction:column;justify-content:center;min-height:80vh">
      <p style="color:var(--on-dark-soft);font-weight:600">Tu resultado</p><div class="serif big">${score} de ${qs.length}</div>
      <p style="font-size:18px;margin-bottom:24px">${msg}</p><button class="pill wide" data-act="close"><span>Volver</span><span>→</span></button></div>`;
  };
  box.addEventListener("click", (e) => {
    const opt = e.target.closest(".opt");
    if (opt && !answered) {
      answered = true;
      const q = qs[i], ok = opt.dataset.opt === q.answer;
      if (ok) score++;
      box.querySelectorAll(".opt").forEach((b) => { if (b.dataset.opt === q.answer) b.classList.add("ok"); else if (b === opt) b.classList.add("bad"); });
      const a = art(q.id);
      box.querySelector(".fb").innerHTML = `<h3 class="serif">${ok ? "Correcto" : `Era “${esc(q.answer)}”`}</h3><p>${esc(a ? a.title : "")}</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap"><button class="pill tone" data-open="${q.id}">Ver noticia</button>
        <button class="pill" data-act="next">${i === qs.length - 1 ? "Ver resultado" : "Siguiente"}</button></div>`;
    }
    if (e.target.closest('[data-act="next"]')) { if (i < qs.length - 1) { i++; paint(); } else finish(); }
  });
  paint();
}

/* ---------------------------------------------------------- bienvenida */
function openOnboarding(step = 0) {
  const slides = [
    ["f-roast", null, "Las noticias más importantes del día, para leer mientras te tomas el café."],
    ["f-olive", "Tu espresso", "Las 5 noticias clave en un minuto. Una por pantalla, toca para pasar."],
    ["f-caramel", "En corto", "Cada nota parte con los puntos clave. La versión larga, solo si quieres."],
  ];
  const el = $layer.querySelector(".onb-layer") || openLayer(`<div class="wrap" id="onb"></div>`, "overlay onb-layer");
  if (step >= slides.length) {
    el.className = "overlay onb-layer"; el.style.background = "var(--crema)";
    el.querySelector("#onb").innerHTML = `<div style="padding-top:var(--safe-t)">${pickerView("Empezar a leer")}</div>`;
    return;
  }
  const [cls, title, text] = slides[step];
  el.className = `overlay onb-layer ${cls}`; el.style.background = "";
  el.querySelector("#onb").innerHTML = `<div class="onb">
    <div style="display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:14px">
      <span>${step + 1} de ${slides.length}</span><button data-act="onb" data-k="${slides.length}" style="padding:8px">Saltar</button></div>
    <div class="grow"></div>
    ${title ? `<h1 class="serif">${title}</h1>` : `<div class="wordmark">sorbo<i></i></div><div style="height:16px"></div>`}
    <p>${text}</p>
    <div class="foot"><div class="dots">${slides.map((_, j) => `<i class="${j === step ? "on" : ""}"></i>`).join("")}</div>
      <button class="pill ${cls === "f-caramel" ? "dark" : "light"}" data-act="onb" data-k="${step + 1}">${step === 0 ? "Empezar" : "Siguiente"}</button></div></div>`;
}

/* -------------------------------------------------------------- acerca */
function openAbout() {
  const when = ED ? new Date(ED.generated_at * 1000).toLocaleString("es-CL", { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" }) : "—";
  const el = openLayer(`<div class="panel" role="dialog" aria-label="Acerca de Sorbo">
    <div style="display:flex;justify-content:space-between;align-items:flex-end"><div class="wordmark">sorbo<i></i></div><span class="soft" style="font-size:13px">Versión ${VERSION}</span></div>
    <p style="margin-top:12px;font-size:16px">Las noticias en un sorbo. Como el diario que se compraba al paso, pero en tu bolsillo.</p>
    <h2 class="serif">Tus datos</h2><p class="soft">Sorbo no pide cuenta ni recopila datos personales. Tus temas, guardadas, racha y quiz se guardan solo en este teléfono.</p>
    <h2 class="serif">De dónde vienen las noticias</h2><p class="soft">Reunimos titulares y resúmenes públicos de medios de Chile y el mundo; cada nota lleva a su medio original. Edición actualizada: ${esc(when)}.</p>
    <p class="soft" style="margin-top:8px">Fuentes: ${esc((ED?.sources || []).join(", "))}.</p>
    <div style="margin-top:20px"><button class="pill wide" data-act="close"><span>Cerrar</span><span>→</span></button></div></div>`, "sheet");
  el.addEventListener("click", (e) => { if (e.target === el) closeLayer(); });
}

/* ============================================================ EVENTOS */
document.addEventListener("click", (e) => {
  const opener = e.target.closest("[data-open]");
  const actEl = e.target.closest("[data-act]");
  if (actEl && (!opener || opener.contains(actEl))) {
    const act = actEl.dataset.act, k = actEl.dataset.k;
    e.preventDefault(); e.stopPropagation();
    switch (act) {
      case "filter": homeFilter = k; render(); return;
      case "espresso": openEspresso(); return;
      case "quiz": openQuiz(); return;
      case "close": closeLayer(); return;
      case "share": share(actEl.dataset.id); return;
      case "save": toggleSave(actEl.dataset.id); actEl.innerHTML = isSaved(actEl.dataset.id) ? icon.saved : icon.save; return;
      case "share-fact": {
        const a = art(ED.fact.id); const text = `Dato del día: ${ED.fact.number}. ${ED.fact.text}`;
        if (navigator.share) navigator.share({ title: "Dato del día · Sorbo", text, url: a?.link }).catch(() => {});
        else navigator.clipboard.writeText(`${text}\n${a?.link || ""}`).then(() => toast("Dato copiado"));
        return;
      }
      case "streak": toast("Tu racha suma un día cada vez que lees al menos una noticia"); return;
      case "about": openAbout(); return;
      case "reload": location.reload(); return;
      case "install": installEvent?.prompt(); installEvent = null; return;
      case "install-hide": store.set("install_hidden", true); render(); return;
      case "edit-topics": foryouEditing = true; render(); return;
      case "topic": {
        const s = pickerView.sel; s.has(k) ? s.delete(k) : s.add(k);
        actEl.classList.toggle("on"); actEl.className = `topic ${s.has(k) ? "on f-" + field(k) : ""}`;
        actEl.querySelector("small").textContent = s.has(k) ? "Elegido" : "Agregar";
        return;
      }
      case "save-topics": {
        const s = pickerView.sel;
        if (!s.size) { toast("Elige al menos un tema"); return; }
        store.set("interests", Object.keys(ED.categories).filter((c) => s.has(c)));
        foryouEditing = false;
        if ($layer.querySelector(".onb-layer")) { store.set("onboarded", true); closeLayer(); tab = "hoy"; }
        render(); return;
      }
      case "suggest": searchQuery = k; render(); return;
      case "onb": openOnboarding(Number(k)); return;
    }
  }
  if (opener) { e.preventDefault(); openArticle(opener.dataset.open); }
});
document.querySelectorAll(".tabbar button").forEach((b) => b.addEventListener("click", () => {
  if (stack.length) return;
  tab = b.dataset.tab; foryouEditing = false; render();
}));
addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); installEvent = e; if (tab === "hoy" && !stack.length) render(); });
document.addEventListener("visibilitychange", async () => {
  // al volver a la app después de un rato, trae la edición nueva
  if (document.visibilityState === "visible" && ED && Date.now() / 1000 - ED.generated_at > 1800) { await loadEdition(); if (!stack.length) render(); }
});

/* ============================================================== INICIO */
(async function start() {
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
  ED = undefined; render();             // esqueleto mientras carga
  await loadEdition();
  render();
  if (ED && !store.get("onboarded", false)) openOnboarding(0);
})();
