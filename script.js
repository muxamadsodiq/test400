'use strict';

let C = null;
let gameUsed    = false;
let timerResult = null;
let timerForm   = null;
let timerSuccess= null;

const RE_NL     = /\n/g;
const RE_BOLD   = /\*\*(.*?)\*\*/g;
const RE_QIZIL  = /\[qizil\](.*?)\[\/qizil\]/gi;
const RE_YASHIL = /\[yashil\](.*?)\[\/yashil\]/gi;
const RE_RED    = /\[red\](.*?)\[\/red\]/gi;
const RE_GREEN  = /\[green\](.*?)\[\/green\]/gi;

// ===== INIT =====
async function init() {
  try {
    const r = await fetch('/api/content');
    C = await r.json();
    applyFontSizes();
    startMessages();
  } catch (e) {
    console.error('Content load error:', e);
  }
}

function applyFontSizes() {
  const fs = C.font_sizes || {};
  setCSSVar('--fs-msg',      fs.message_text  || 16);
  setCSSVar('--fs-time',     fs.timestamp     || 11);
  setCSSVar('--fs-winner',   fs.winner_text   || 14);
  setCSSVar('--fs-wh',       fs.winners_header|| 18);
  setCSSVar('--fs-gtitle',   fs.game_title    || 18);
  setCSSVar('--fs-wptitle',  fs.win_popup_title||24);
  setCSSVar('--fs-wptext',   fs.win_popup_text|| 16);
  setCSSVar('--fs-ftitle',   fs.form_title    || 17);
  setCSSVar('--fs-fsub',     fs.form_subtitle || 13);
  setCSSVar('--fs-sbtn',     fs.submit_button || 18);
}

function setCSSVar(name, val) {
  document.documentElement.style.setProperty(name, val + 'px');
}

// ===== TEXT FORMAT =====
function fmt(text) {
  if (!text) return '';
  return text
    .replace(RE_NL,     '<br>')
    .replace(RE_BOLD,   '<strong>$1</strong>')
    .replace(RE_QIZIL,  '<span class="t-red">$1</span>')
    .replace(RE_YASHIL, '<span class="t-green">$1</span>')
    .replace(RE_RED,    '<span class="t-red">$1</span>')
    .replace(RE_GREEN,  '<span class="t-green">$1</span>');
}

// ===== TYPEWRITER =====
function typeWriter(el, html, speed, onDone) {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;

  // Collect all text nodes, clear their content
  const texts = [];
  const walker = document.createTreeWalker(tmp, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    texts.push({ node: n, full: n.textContent });
    n.textContent = '';
  }

  // Move parsed DOM into el (preserves formatting structure)
  el.innerHTML = '';
  while (tmp.firstChild) el.appendChild(tmp.firstChild);

  let ti = 0, ci = 0;
  function tick() {
    if (ti >= texts.length) { if (onDone) onDone(); return; }
    const { node, full } = texts[ti];
    if (ci < full.length) {
      node.textContent = full.slice(0, ++ci);
      setTimeout(tick, speed);
    } else { ti++; ci = 0; tick(); }
  }
  tick();
}

function getCurrentTime() {
  const d = new Date();
  return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
}

// ===== MESSAGES =====
function startMessages() {
  showMessage(0);
}

function showMessage(idx) {
  const msgs = C.messages || [];
  if (idx >= msgs.length) {
    setTimeout(showWinnersAndGame, 600);
    return;
  }
  const msg = msgs[idx];
  showTyping(msg.avatar || C.avatar_url || '');

  setTimeout(() => {
    hideTyping();
    renderMessage(msg, idx);
  }, msg.delay || 1800);
}

function showTyping(avatarSrc) {
  const row = document.getElementById('typingRow');
  const av  = document.getElementById('typingAvatar');
  if (avatarSrc) av.src = avatarSrc;
  av.style.display = avatarSrc ? 'block' : 'none';
  row.style.display = 'flex';
  scrollBottom();
}

function hideTyping() {
  document.getElementById('typingRow').style.display = 'none';
}

function renderMessage(msg, idx) {
  const container = document.getElementById('messages');
  const block = document.createElement('div');
  block.className = 'msg-block';

  const avatarSrc = msg.avatar || C.avatar_url || '';
  const avatarTag = avatarSrc
    ? `<img class="avatar-circle msg-avatar" src="${avatarSrc}" alt="">`
    : `<div class="avatar-circle msg-avatar"></div>`;

  const imageTag = msg.image
    ? `<img class="msg-image" src="${msg.image}" alt="" onerror="this.style.display='none'">`
    : '';
  const imgPos = msg.image_position || 'bottom';

  block.innerHTML = `
    ${avatarTag}
    <div class="msg-right">
      <div class="msg-bubble">
        ${imgPos === 'top' ? imageTag : ''}
        <div class="msg-text" style="font-size:var(--fs-msg)"></div>
        ${imgPos === 'bottom' ? imageTag : ''}
        <div class="msg-time" style="font-size:var(--fs-time)">${getCurrentTime()}</div>
      </div>
    </div>`;

  // Top bo'lsa rasmni vaqtincha yashir
  if (imgPos === 'top' && msg.image) {
    const imgEl = block.querySelector('.msg-image');
    if (imgEl) imgEl.style.visibility = 'hidden';
  }

  container.appendChild(block);
  scrollBottom();

  const textEl = block.querySelector('.msg-text');
  const SPEED  = 28; // ms per character

  function startTypeWriter() {
    typeWriter(textEl, fmt(msg.text), SPEED, () => {
    scrollBottom();
    if (msg.qa) {
      const right  = block.querySelector('.msg-right');
      const qaWrap = document.createElement('div');
      qaWrap.className = 'qa-wrap';
      qaWrap.id = `qa-${idx}`;
      (msg.qa.answers || []).forEach((a, i) => {
        const btn = document.createElement('button');
        btn.className = 'qa-btn';
        btn.textContent = a;
        btn.onclick = () => onQA(idx, i, btn);
        qaWrap.appendChild(btn);
      });
      right.appendChild(qaWrap);
      scrollBottom();
    } else {
      setTimeout(() => showMessage(idx + 1), 500);
    }
  });
  }

  if (imgPos === 'top' && msg.image) {
    const imgEl = block.querySelector('.msg-image');
    if (imgEl) {
      const showAndType = () => {
        imgEl.style.visibility = 'visible';
        scrollBottom();
        startTypeWriter();
      };
      if (imgEl.complete && imgEl.naturalWidth > 0) {
        showAndType();
      } else {
        imgEl.onload  = showAndType;
        imgEl.onerror = () => { imgEl.style.visibility = 'visible'; startTypeWriter(); };
      }
    } else {
      startTypeWriter();
    }
  } else {
    startTypeWriter();
  }
}

window.onQA = function(msgIdx, ansIdx, btn) {
  const wrap = document.getElementById(`qa-${msgIdx}`);
  wrap.querySelectorAll('.qa-btn').forEach(b => { b.disabled = true; });
  btn.classList.add('selected');
  setTimeout(() => showMessage(msgIdx + 1), 700);
};

// ===== WINNERS + GAME =====
function showWinnersAndGame() {
  const ws = document.getElementById('winnersSection');
  ws.style.display = 'block';

  const hdr = document.getElementById('winnersHeader');
  hdr.style.fontSize = 'var(--fs-wh)';
  hdr.innerHTML = fmt(C.winners_header || '');

  const list = document.getElementById('winnersList');
  (C.winners || []).forEach(w => {
    const d = document.createElement('div');
    d.className = 'winner-item';
    d.style.fontSize = 'var(--fs-winner)';
    d.innerHTML = w.discount ? `<strong>${w.name}</strong> — ${w.discount}` : `<strong>${w.name}</strong>`;
    list.appendChild(d);
  });

  const gs = document.getElementById('gameSection');
  gs.style.display = 'block';

  const tb = document.getElementById('gameTitleBox');
  tb.style.fontSize = 'var(--fs-gtitle)';
  tb.innerHTML = fmt(C.game.title || '');

  renderGame();
  scrollBottom();
}

// ===== GAME RENDER =====
function renderGame() {
  const area = document.getElementById('gameArea');
  const g = C.game;
  const type = g.type || 'matryoshka';

  if (type === 'matryoshka') renderMatryoshka(area, g);
  else if (type === 'baraban') renderBaraban(area, g);
  else if (type === 'doors')   renderDoors(area, g);
  else if (type === 'boxes')   renderBoxes(area, g);
}

// ---- Matryoshka SVG dolls ----
const DOLL_COLORS = [
  { body: '#2d6fa5', dark: '#1a4a7a', acc: '#60a0df', flower: '#f0d020' },
  { body: '#b03030', dark: '#7a1010', acc: '#df6060', flower: '#f8e020' },
  { body: '#d4a020', dark: '#9a6c00', acc: '#f0c840', flower: '#e05020' },
];

function dollSVG(colIdx, isOpen, prizeText) {
  const c = DOLL_COLORS[colIdx % DOLL_COLORS.length];
  const fl = (cx, cy, r) => {
    const pts = [0, 72, 144, 216, 288].map(a => {
      const rad = a * Math.PI / 180;
      return `<circle cx="${cx + Math.round(r * Math.cos(rad))}" cy="${cy + Math.round(r * Math.sin(rad))}" r="${r - 2}" fill="${c.flower}" opacity=".55"/>`;
    }).join('');
    return pts + `<circle cx="${cx}" cy="${cy}" r="${r - 4}" fill="white" opacity=".55"/>`;
  };

  return `<svg viewBox="0 0 100 170" xmlns="http://www.w3.org/2000/svg" class="doll-svg">
    <!-- head -->
    <ellipse cx="50" cy="40" rx="22" ry="26" fill="#f5c5a3"/>
    <ellipse cx="42" cy="37" rx="4" ry="5" fill="white"/>
    <ellipse cx="58" cy="37" rx="4" ry="5" fill="white"/>
    <circle cx="43" cy="38" r="2.5" fill="#333"/>
    <circle cx="57" cy="38" r="2.5" fill="#333"/>
    <path d="M44 49 Q50 55 56 49" stroke="#c04060" stroke-width="2" fill="none" stroke-linecap="round"/>
    <circle cx="38" cy="45" r="6" fill="#ffaaaa" opacity=".5"/>
    <circle cx="62" cy="45" r="6" fill="#ffaaaa" opacity=".5"/>
    <!-- scarf -->
    <path d="M28 57 Q50 50 72 57 L72 66 Q50 60 28 66Z" fill="${c.body}"/>
    ${isOpen ? `
      <!-- open body bottom -->
      <path d="M30 78 Q18 115 24 142 Q50 152 76 142 Q82 115 70 78 Q50 73 30 78Z" fill="${c.body}"/>
      <ellipse cx="50" cy="143" rx="26" ry="7" fill="${c.dark}"/>
      <!-- open top rim -->
      <path d="M30 78 Q50 73 70 78 Q50 68 30 78Z" fill="${c.dark}" opacity=".6"/>
    ` : `
      <!-- closed body -->
      <path d="M28 65 Q16 106 22 138 Q50 148 78 138 Q84 106 72 65 Q50 60 28 65Z" fill="${c.body}"/>
      <!-- flower -->
      ${fl(50, 103, 16)}
      <!-- stripe -->
      <line x1="28" y1="83" x2="72" y2="83" stroke="white" stroke-width="1.5" opacity=".3"/>
      <ellipse cx="50" cy="139" rx="26" ry="7" fill="${c.dark}"/>
    `}
  </svg>`;
}

function renderMatryoshka(area, g) {
  const count = Math.max(2, Math.min(6, g.items || 3));
  area.style.flexDirection = 'row';

  for (let i = 0; i < count; i++) {
    const wrap = document.createElement('div');
    wrap.className = 'doll-wrap';
    wrap.innerHTML = dollSVG(i, false, g.win_value || '100%');

    const prize = document.createElement('div');
    prize.className = 'doll-prize';
    prize.textContent = g.win_value || '100%';
    wrap.appendChild(prize);

    wrap.addEventListener('click', () => onDollClick(wrap, g));
    area.appendChild(wrap);
  }
}

function onGameClick(selector, openFn, g, delay) {
  if (gameUsed) return;
  gameUsed = true;
  document.querySelectorAll(selector).forEach(el => { el.style.pointerEvents = 'none'; });
  openFn();
  playWinSound(g.win_sound_url);
  setTimeout(() => showWinModal(g), delay);
}

function onDollClick(wrap, g) {
  onGameClick('.doll-wrap', () => {
    document.querySelectorAll('.doll-wrap').forEach(d => {
      if (d !== wrap) d.style.opacity = '0.5';
    });
    const svgEl = wrap.querySelector('.doll-svg');
    if (svgEl) svgEl.outerHTML = dollSVG(
      Array.from(wrap.parentNode.children).indexOf(wrap),
      true, g.win_value || '100%'
    );
    wrap.classList.add('open');
  }, g, 1200);
}

// ---- Baraban (Wheel) ----
function renderBaraban(area, g) {
  area.style.flexDirection = 'column';
  area.style.alignItems = 'center';

  const canvas = document.createElement('canvas');
  canvas.className = 'wheel-canvas';
  canvas.width = 220;
  canvas.height = 220;

  function stripTags(t) {
    return (t || '').replace(/<[^>]+>/g, '').replace(/\[\/?[a-z]+\]/gi, '');
  }
  const winLabel = stripTags(g.win_value || '100%');
  const labels = [winLabel, '75%', winLabel, '90%', winLabel, '50%'];
  drawWheel(canvas, labels, 0);

  const btn = document.createElement('button');
  btn.className = 'spin-btn';
  btn.textContent = 'Aylantirish';

  const wrap = document.createElement('div');
  wrap.className = 'baraban-wrap';
  wrap.appendChild(canvas);
  wrap.appendChild(btn);
  area.appendChild(wrap);

  btn.addEventListener('click', () => {
    if (gameUsed) return;
    gameUsed = true;
    btn.disabled = true;
    spinWheel(canvas, labels, g);
  });
}

function drawWheel(canvas, labels, angle) {
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2, cy = canvas.height / 2, r = cx - 4;
  const slice = (2 * Math.PI) / labels.length;
  const colors = ['#e53935','#1e88e5','#43a047','#fb8c00','#8e24aa','#00897b'];
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  labels.forEach((lbl, i) => {
    const start = angle + i * slice;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, start, start + slice);
    ctx.closePath();
    ctx.fillStyle = colors[i % colors.length];
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(start + slice / 2);
    ctx.textAlign = 'right';
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 16px Arial';
    ctx.fillText(lbl, r - 10, 6);
    ctx.restore();
  });

  // Center circle
  ctx.beginPath();
  ctx.arc(cx, cy, 16, 0, 2 * Math.PI);
  ctx.fillStyle = '#fff';
  ctx.fill();

  // Arrow/pointer
  ctx.beginPath();
  ctx.moveTo(cx + r - 10, cy);
  ctx.lineTo(cx + r + 12, cy - 8);
  ctx.lineTo(cx + r + 12, cy + 8);
  ctx.closePath();
  ctx.fillStyle = '#333';
  ctx.fill();
}

function spinWheel(canvas, labels, g) {
  const totalAngle = (Math.PI * 2) * (5 + Math.random() * 5);
  // Always land on first label (win_value) — index 0
  const slice = (2 * Math.PI) / labels.length;
  const targetStop = 2 * Math.PI - slice * 0.5; // points to index 0
  const finalAngle = totalAngle + targetStop;

  let start = null;
  const duration = 4000;

  function step(ts) {
    if (!start) start = ts;
    const elapsed = ts - start;
    const t = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const angle = ease * finalAngle;

    drawWheel(canvas, labels, angle);

    if (t < 1) {
      requestAnimationFrame(step);
    } else {
      playWinSound(g.win_sound_url);
      setTimeout(() => showWinModal(g), 600);
    }
  }
  requestAnimationFrame(step);
}

// ---- Doors ----
function renderDoors(area, g) {
  area.style.flexDirection = 'row';
  area.style.alignItems = 'flex-end';

  const wrap = document.createElement('div');
  wrap.className = 'doors-wrap';

  const count = Math.max(2, Math.min(5, g.items || 3));
  for (let i = 0; i < count; i++) {
    const door = document.createElement('div');
    door.className = 'door-item';
    door.innerHTML = `
      <div class="door-face door-front">🚪<br>${i + 1}</div>
      <div class="door-face door-back" style="color:var(--red);font-size:18px">${g.win_value || '100%'}</div>`;
    door.addEventListener('click', () => onDoorClick(door, g));
    wrap.appendChild(door);
  }
  area.appendChild(wrap);
}

function onDoorClick(door, g) {
  onGameClick('.door-item', () => door.classList.add('open'), g, 1200);
}

// ---- Boxes ----
const BOX_COLORS = ['#e53935','#1e88e5','#43a047','#fb8c00','#8e24aa'];

function renderBoxes(area, g) {
  area.style.flexDirection = 'row';
  area.style.flexWrap = 'wrap';

  const wrap = document.createElement('div');
  wrap.className = 'boxes-wrap';

  const count = Math.max(2, Math.min(8, g.items || 4));
  for (let i = 0; i < count; i++) {
    const col = BOX_COLORS[i % BOX_COLORS.length];
    const box = document.createElement('div');
    box.className = 'box-item';
    box.innerHTML = `
      <div class="box-lid" style="background:${col};color:#fff;font-size:18px">🎀</div>
      <div class="box-body" style="background:${col}99;border:2px solid ${col}"></div>
      <div class="box-prize">${g.win_value || '100%'}</div>`;
    box.addEventListener('click', () => onBoxClick(box, g));
    wrap.appendChild(box);
  }
  area.appendChild(wrap);
}

function onBoxClick(box, g) {
  onGameClick('.box-item', () => box.classList.add('open'), g, 1000);
}

// ===== WIN MODAL =====
function playWinSound(url) {
  if (!url) return;
  const audio = document.getElementById('winAudio');
  audio.src = url;
  audio.play().catch(() => {});
}

function showWinModal(g) {
  const title = document.getElementById('winTitle');
  const text  = document.getElementById('winText');
  title.style.fontSize = 'var(--fs-wptitle)';
  text.style.fontSize  = 'var(--fs-wptext)';
  title.innerHTML = fmt(g.win_popup_title || 'Tabriklaymiz!');
  text.innerHTML  = fmt(g.win_popup_text  || '');
  document.getElementById('winOverlay').style.display = 'flex';
}

window.closeWinModal = function() {
  document.getElementById('winOverlay').style.display = 'none';
};

// ===== RESULT MODAL =====
window.openResultModal = function() {
  document.getElementById('winOverlay').style.display = 'none';
  const r = C.result || {};
  const f = C.form   || {};

  // Image
  const img = document.getElementById('resultImg');
  if (r.image) { img.src = r.image; img.style.display = 'block'; }

  // Middle text + countdown above form
  const midEl = document.getElementById('resultMidText');
  midEl.textContent = r.middle_text || '';
  midEl.style.display = r.middle_text ? 'block' : 'none';

  if (r.countdown_seconds > 0) {
    const el = document.getElementById('resultCountdown');
    el.style.display = 'block';
    timerResult = startCountdown(el, r.countdown_seconds, timerResult);
  }

  document.getElementById('formTitle').style.fontSize = 'var(--fs-ftitle)';
  document.getElementById('formSubtitle').style.fontSize = 'var(--fs-fsub)';
  document.getElementById('submitBtn').style.fontSize = 'var(--fs-sbtn)';
  document.getElementById('formTitle').innerHTML = fmt(f.title || '');
  document.getElementById('formSubtitle').innerHTML = fmt(f.subtitle || '');
  document.getElementById('nameInput').placeholder = f.name_placeholder || 'Sizning ismingiz';
  document.getElementById('phonePre').textContent = f.phone_prefix || '+998';
  document.getElementById('submitBtn').textContent = f.button_text || 'uni olish';

  if (f.countdown_show && f.countdown_seconds > 0) {
    const el = document.getElementById('formCountdown');
    el.style.display = 'block';
    timerForm = startCountdown(el, f.countdown_seconds, timerForm);
  }

  document.getElementById('resultOverlay').style.display = 'flex';
};

function startCountdown(el, seconds, existingTimer) {
  clearInterval(existingTimer);
  let rem = seconds;
  let id;
  function tick() {
    const m = String(Math.floor(rem / 60)).padStart(2, '0');
    const s = String(rem % 60).padStart(2, '0');
    el.textContent = `${m}:${s}`;
    if (rem <= 0) clearInterval(id);
    else rem--;
  }
  tick();
  id = setInterval(tick, 1000);
  return id;
}

// ===== FORM SUBMIT =====
window.submitForm = async function(e) {
  e.preventDefault();
  const name  = document.getElementById('nameInput').value.trim();
  const phone = document.getElementById('phoneInput').value.trim();
  const btn   = document.getElementById('submitBtn');

  if (!name || !phone) return;

  btn.disabled = true;
  btn.textContent = 'Yuborilmoqda...';

  try {
    const resp = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone })
    });
    const data = await resp.json();
    if (data.success) {
      document.getElementById('resultOverlay').style.display = 'none';
      showSuccessModal();
    } else {
      btn.disabled = false;
      btn.textContent = C.form?.button_text || 'uni olish';
    }
  } catch {
    btn.disabled = false;
    btn.textContent = C.form?.button_text || 'uni olish';
  }
};

// ===== SUCCESS MODAL =====
function showSuccessModal() {
  const sm = C.success_modal || {};

  const titleEl  = document.getElementById('smTitle');
  const textEl   = document.getElementById('smText');
  const detailEl = document.getElementById('smDetail');
  const cdEl     = document.getElementById('smCountdown');

  titleEl.innerHTML  = fmt(sm.title  || 'Tabriklaymiz!');
  textEl.innerHTML   = fmt(sm.text   || "Ma'lumotlar qabul qilindi");
  detailEl.innerHTML = fmt(sm.detail || '');

  const mins = sm.countdown_minutes || 15;
  timerSuccess = startCountdown(cdEl, mins * 60, timerSuccess);

  document.getElementById('successOverlay').style.display = 'flex';
}

function scrollBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

// Phone input mask
document.addEventListener('DOMContentLoaded', () => {
  const phone = document.getElementById('phoneInput');
  if (!phone) return;
  phone.addEventListener('input', (e) => {
    let val = e.target.value.replace(/\D/g, '').slice(0, 9);
    let out = '';
    if (val.length > 0) out += val.slice(0, 2);
    if (val.length > 2) out += ' ' + val.slice(2, 5);
    if (val.length > 5) out += ' ' + val.slice(5, 7);
    if (val.length > 7) out += ' ' + val.slice(7, 9);
    e.target.value = out;
  });
  phone.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace') return;
  });
});

init();
