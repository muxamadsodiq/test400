"""
Telegram Bot + Flask server
Admin ID: 5724592490
"""

import asyncio
import json
import os
import threading
import logging
import requests as req_lib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# ───────── CONFIG ─────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "0"))

BASE_DIR    = Path(__file__).parent
CONTENT_FILE = BASE_DIR / "content.json"
UPLOADS_DIR  = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ───────── CONTENT HELPERS ─────────
_content_lock = threading.Lock()

def load():
    with _content_lock:
        with open(CONTENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save(data):
    with _content_lock:
        with open(CONTENT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# ───────── FLASK ─────────
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)

@app.route("/")
def index():
    return send_file(BASE_DIR / "index.html")

@app.route("/api/content")
def api_content():
    return jsonify(load())

@app.route("/api/submit", methods=["POST"])
def api_submit():
    data = request.get_json(silent=True) or {}
    name  = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    if not name or not phone:
        return jsonify({"error": "required"}), 400

    with _content_lock:
        with open(CONTENT_FILE, "r", encoding="utf-8") as f:
            c = json.load(f)
        c["submission_count"] = c.get("submission_count", 0) + 1
        count = c["submission_count"]
        with open(CONTENT_FILE, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=2)

    msg_id  = f"#A{str(count).zfill(5)}"
    message = f"{msg_id} Mijoz\n👤 Ism: {name}\n📞 Telefon: +998{phone}"

    group_id = c.get("form", {}).get("group_id", "")
    if group_id:
        try:
            req_lib.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": group_id, "text": message},
                timeout=10
            )
        except Exception as e:
            log.error("Group send error: %s", e)

    return jsonify({"success": True, "id": count})

@app.route("/uploads/<path:fn>")
def uploaded(fn):
    return send_from_directory(str(UPLOADS_DIR), fn)

@app.route("/<path:fn>")
def static_files(fn):
    return send_from_directory(str(BASE_DIR), fn)

def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

# ───────── BOT STATES ─────────
(
    ST_MAIN,
    ST_MSG_MENU, ST_MSG_ADD_TEXT, ST_MSG_ADD_TS, ST_MSG_ADD_IMG, ST_MSG_ADD_QA, ST_MSG_ADD_QA_ANS,
    ST_MSG_EDIT_SEL, ST_MSG_EDIT_TEXT,
    ST_MSG_DEL_SEL,
    ST_GAME_MENU, ST_GAME_TYPE, ST_GAME_TITLE, ST_GAME_WIN_VAL, ST_GAME_WIN_PTITLE, ST_GAME_WIN_PTEXT, ST_GAME_SOUND,
    ST_RESULT_MENU, ST_RESULT_IMG, ST_RESULT_CD, ST_RESULT_MID,
    ST_FORM_MENU, ST_FORM_TITLE, ST_FORM_SUB, ST_FORM_BTN, ST_FORM_GROUP,
    ST_WINNERS_MENU, ST_WIN_ADD_NAME, ST_WIN_ADD_DISC, ST_WIN_HDR, ST_WIN_DEL,
    ST_FONT_SEL, ST_FONT_VAL,
    ST_AVATAR,
    ST_MSG_DELAY,
) = range(35)

CANCEL_BTN = [[InlineKeyboardButton("◀ Orqaga", callback_data="back_main")]]

# ─── helpers ───
def kb(rows): return InlineKeyboardMarkup(rows)
def back_kb(): return kb(CANCEL_BTN)
async def answer(q, text=""):
    try: await q.answer(text)
    except Exception: pass

async def edit_or_send(update, text, markup=None, parse="Markdown"):
    q = update.callback_query
    if q:
        await q.edit_message_text(text, reply_markup=markup, parse_mode=parse)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=parse)

# ─── MAIN MENU ───
MAIN_KB = kb([
    [InlineKeyboardButton("💬 Xabarlar",         callback_data="menu_msg")],
    [InlineKeyboardButton("🎮 O'yin sozlash",     callback_data="menu_game")],
    [InlineKeyboardButton("🪟 Popup sozlash",     callback_data="menu_result")],
    [InlineKeyboardButton("📝 Forma sozlash",     callback_data="menu_form")],
    [InlineKeyboardButton("🏆 G'oliblar",         callback_data="menu_winners")],
    [InlineKeyboardButton("👤 Avatar rasm",       callback_data="menu_avatar")],
    [InlineKeyboardButton("🔤 Shrift o'lchamlari",callback_data="menu_fonts")],
])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("Assalomu alaykum!")
        return ConversationHandler.END
    await update.message.reply_text("🛠 *Admin Panel*\nNimani o'zgartirmoqchisiz?",
                                    reply_markup=MAIN_KB, parse_mode="Markdown")
    return ST_MAIN

async def back_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text(
        "🛠 *Admin Panel*\nNimani o'zgartirmoqchisiz?",
        reply_markup=MAIN_KB, parse_mode="Markdown"
    )
    return ST_MAIN

# ═══════════════════════════════════════════════
# MESSAGES
# ═══════════════════════════════════════════════
async def menu_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    msgs = c.get("messages", [])
    txt = "💬 *Xabarlar* — jami: {}\n\n".format(len(msgs))
    for i, m in enumerate(msgs, 1):
        preview = (m.get("text","") or "")[:40].replace("\n"," ")
        txt += f"{i}. {preview}...\n"
    row = [
        [InlineKeyboardButton("➕ Yangi xabar",  callback_data="msg_add")],
        [InlineKeyboardButton("✏️ Tahrirlash",   callback_data="msg_edit")],
        [InlineKeyboardButton("🗑 O'chirish",     callback_data="msg_del")],
        [InlineKeyboardButton("◀ Orqaga",         callback_data="back_main")],
    ]
    await update.callback_query.edit_message_text(txt, reply_markup=kb(row), parse_mode="Markdown")
    return ST_MSG_MENU

async def msg_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["new_msg"] = {}
    await update.callback_query.edit_message_text(
        "✍️ Yangi xabar matnini yozing:\n\n"
        "Formatlash:\n`**qalin**`\n`[qizil]qizil matn[/qizil]`\n`[yashil]yashil[/yashil]`",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return ST_MSG_ADD_TEXT

async def msg_add_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_msg"]["text"] = update.message.text
    ctx.user_data["new_msg"]["timestamp"] = ""  # real time shown automatically
    await update.message.reply_text(
        "⏱ Typing indicator ko'rinish vaqti (ms, masalan 2000). Standart: 2000:"
    )
    return ST_MSG_DELAY

async def msg_add_delay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        delay = int(update.message.text.strip())
    except ValueError:
        delay = 2000
    ctx.user_data["new_msg"]["delay"] = delay
    row = kb([
        [InlineKeyboardButton("📷 Rasm qo'shish", callback_data="msg_img_yes")],
        [InlineKeyboardButton("➡ O'tkazib yuborish", callback_data="msg_img_no")],
    ])
    await update.message.reply_text("Rasm qo'shasizmi?", reply_markup=row)
    return ST_MSG_ADD_IMG

async def msg_img_yes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text("📷 Rasmni yuboring (photo sifatida):")
    return ST_MSG_ADD_IMG

async def msg_img_no(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["new_msg"]["image"] = None
    return await ask_qa(update, ctx)

async def msg_got_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file  = await ctx.bot.get_file(photo.file_id)
    fname = f"img_{photo.file_id[-8:]}.jpg"
    fpath = UPLOADS_DIR / fname
    await file.download_to_drive(fpath)
    ctx.user_data["new_msg"]["image"] = f"/uploads/{fname}"
    return await ask_qa(update, ctx)

async def ask_qa(update, ctx):
    row = kb([
        [InlineKeyboardButton("✅ Ha, savol qo'shaman",  callback_data="qa_yes")],
        [InlineKeyboardButton("➡ Yo'q",                 callback_data="qa_no")],
    ])
    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_text("Bu xabarga savol-javob qo'shasizmi?", reply_markup=row)
    return ST_MSG_ADD_QA

async def qa_yes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text(
        "📝 Javob variantlarini yozing (har biri yangi qatorda, maksimum 4):"
    )
    return ST_MSG_ADD_QA_ANS

async def qa_no(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["new_msg"]["qa"] = None
    await save_new_msg(update, ctx)
    return ST_MSG_MENU

async def got_qa_answers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    answers_list = [a.strip() for a in update.message.text.split("\n") if a.strip()][:4]
    ctx.user_data["new_msg"]["qa"] = {"answers": answers_list}
    await save_new_msg(update, ctx)
    return ST_MSG_MENU

async def save_new_msg(update, ctx):
    c = load()
    msgs = c.setdefault("messages", [])
    new_id = max((m.get("id",0) for m in msgs), default=0) + 1
    nm = ctx.user_data.pop("new_msg", {})
    nm["id"] = new_id
    msgs.append(nm)
    save(c)
    txt = f"✅ Xabar #{new_id} saqlandi!"
    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_text(txt, reply_markup=MAIN_KB)

async def msg_edit_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    msgs = c.get("messages", [])
    if not msgs:
        await update.callback_query.edit_message_text("Xabarlar yo'q.", reply_markup=back_kb())
        return ST_MSG_MENU
    rows = [[InlineKeyboardButton(f"{i+1}. {m.get('text','')[:30]}...", callback_data=f"edit_msg_{m['id']}")]
             for i,m in enumerate(msgs)]
    rows.append([InlineKeyboardButton("◀ Orqaga", callback_data="menu_msg")])
    await update.callback_query.edit_message_text("✏️ Qaysi xabarni tahrirlaysiz?", reply_markup=kb(rows))
    return ST_MSG_EDIT_SEL

async def msg_edit_sel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    mid = int(update.callback_query.data.split("_")[-1])
    ctx.user_data["edit_msg_id"] = mid
    await update.callback_query.edit_message_text(
        "✍️ Yangi matnni yozing:", reply_markup=back_kb()
    )
    return ST_MSG_EDIT_TEXT

async def msg_edit_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mid  = ctx.user_data.pop("edit_msg_id", None)
    text = update.message.text
    c = load()
    for m in c.get("messages", []):
        if m.get("id") == mid:
            m["text"] = text
            break
    save(c)
    await update.message.reply_text("✅ Xabar yangilandi!", reply_markup=MAIN_KB)
    return ST_MAIN

async def msg_del_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    msgs = c.get("messages", [])
    if not msgs:
        await update.callback_query.edit_message_text("Xabarlar yo'q.", reply_markup=back_kb())
        return ST_MSG_MENU
    rows = [[InlineKeyboardButton(f"🗑 {i+1}. {m.get('text','')[:25]}...", callback_data=f"del_msg_{m['id']}")]
             for i,m in enumerate(msgs)]
    rows.append([InlineKeyboardButton("◀ Orqaga", callback_data="menu_msg")])
    await update.callback_query.edit_message_text("🗑 Qaysi xabarni o'chirasiz?", reply_markup=kb(rows))
    return ST_MSG_DEL_SEL

async def msg_del_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    mid = int(update.callback_query.data.split("_")[-1])
    c = load()
    c["messages"] = [m for m in c.get("messages",[]) if m.get("id") != mid]
    save(c)
    await update.callback_query.edit_message_text("✅ Xabar o'chirildi!", reply_markup=MAIN_KB)
    return ST_MAIN

# ═══════════════════════════════════════════════
# GAME
# ═══════════════════════════════════════════════
GAME_TYPES = {"matryoshka":"🪆 Matryoška","baraban":"🎰 Baraban","doors":"🚪 3 Eshik","boxes":"🎁 Qutichalar"}

async def menu_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c  = load()
    g  = c.get("game", {})
    txt = (f"🎮 *O'yin sozlamalari*\n\n"
           f"Tur: `{g.get('type','matryoshka')}`\n"
           f"Sarlavha: `{g.get('title','')[:40]}`\n"
           f"G'alaba qiymati: `{g.get('win_value','100%')}`\n"
           f"Elementlar soni: `{g.get('items',3)}`")
    row = [
        [InlineKeyboardButton("Tur tanlash",           callback_data="game_type")],
        [InlineKeyboardButton("Sarlavha",               callback_data="game_title")],
        [InlineKeyboardButton("G'alaba qiymati",        callback_data="game_win_val")],
        [InlineKeyboardButton("G'alaba popup sarlavha", callback_data="game_win_ptitle")],
        [InlineKeyboardButton("G'alaba popup matn",     callback_data="game_win_ptext")],
        [InlineKeyboardButton("Ovoz URL",               callback_data="game_sound")],
        [InlineKeyboardButton("◀ Orqaga",               callback_data="back_main")],
    ]
    await update.callback_query.edit_message_text(txt, reply_markup=kb(row), parse_mode="Markdown")
    return ST_GAME_MENU

async def game_type_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    row = [[InlineKeyboardButton(v, callback_data=f"gtype_{k}")] for k,v in GAME_TYPES.items()]
    row.append([InlineKeyboardButton("◀ Orqaga", callback_data="menu_game")])
    await update.callback_query.edit_message_text("O'yin turini tanlang:", reply_markup=kb(row))
    return ST_GAME_TYPE

async def game_type_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    gtype = update.callback_query.data.split("_",1)[1]
    c = load()
    c.setdefault("game",{})["type"] = gtype
    save(c)
    await update.callback_query.edit_message_text(f"✅ O'yin turi: {GAME_TYPES.get(gtype,gtype)}", reply_markup=MAIN_KB)
    return ST_MAIN

async def game_title_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text("O'yin sarlavhasini yozing (\\n = yangi qator):", reply_markup=back_kb())
    ctx.user_data["game_field"] = "title"
    return ST_GAME_TITLE

async def game_field_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    field = ctx.user_data.pop("game_field", "title")
    val   = update.message.text.replace("\\n", "\n")
    c = load()
    c.setdefault("game",{})[field] = val
    save(c)
    await update.message.reply_text(f"✅ Saqlandi!", reply_markup=MAIN_KB)
    return ST_MAIN

async def game_win_val_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["game_field"] = "win_value"
    await update.callback_query.edit_message_text("G'alaba qiymatini yozing (masalan: 100%):", reply_markup=back_kb())
    return ST_GAME_WIN_VAL

async def game_win_ptitle_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["game_field"] = "win_popup_title"
    await update.callback_query.edit_message_text("G'alaba popup sarlavhasini yozing:", reply_markup=back_kb())
    return ST_GAME_WIN_PTITLE

async def game_win_ptext_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["game_field"] = "win_popup_text"
    await update.callback_query.edit_message_text(
        "G'alaba popup matnini yozing:\n(Formatlash: **qalin**, [qizil]...[/qizil])", reply_markup=back_kb()
    )
    return ST_GAME_WIN_PTEXT

async def game_sound_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["game_field"] = "win_sound_url"
    await update.callback_query.edit_message_text("Ovoz fayl URL manzilini yozing:", reply_markup=back_kb())
    return ST_GAME_SOUND

# ═══════════════════════════════════════════════
# RESULT POPUP
# ═══════════════════════════════════════════════
async def menu_result(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    r = c.get("result", {})
    txt = (f"🪟 *Popup sozlamalari*\n\n"
           f"Rasm: `{('bor' if r.get('image') else 'yoq')}`\n"
           f"Sanash vaqti: `{r.get('countdown_seconds',600)}` sek\n"
           f"O'rtadagi matn: `{r.get('middle_text','')[:30]}`")
    row = [
        [InlineKeyboardButton("Rasm",         callback_data="res_img")],
        [InlineKeyboardButton("Sanash vaqti", callback_data="res_cd")],
        [InlineKeyboardButton("O'rtadagi matn", callback_data="res_mid")],
        [InlineKeyboardButton("◀ Orqaga",     callback_data="back_main")],
    ]
    await update.callback_query.edit_message_text(txt, reply_markup=kb(row), parse_mode="Markdown")
    return ST_RESULT_MENU

async def res_img_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text("📷 Rasmni yuboring:", reply_markup=back_kb())
    return ST_RESULT_IMG

async def res_got_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file  = await ctx.bot.get_file(photo.file_id)
    fname = f"res_{photo.file_id[-8:]}.jpg"
    fpath = UPLOADS_DIR / fname
    await file.download_to_drive(fpath)
    c = load()
    c.setdefault("result",{})["image"] = f"/uploads/{fname}"
    save(c)
    await update.message.reply_text("✅ Rasm saqlandi!", reply_markup=MAIN_KB)
    return ST_MAIN

async def res_cd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text("Sanash vaqtini sekundlarda yozing:", reply_markup=back_kb())
    return ST_RESULT_CD

async def res_cd_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try: val = int(update.message.text.strip())
    except ValueError: val = 600
    c = load()
    c.setdefault("result",{})["countdown_seconds"] = val
    c.setdefault("form",{})["countdown_seconds"]   = val
    save(c)
    await update.message.reply_text(f"✅ Sanash vaqti: {val} sek", reply_markup=MAIN_KB)
    return ST_MAIN

async def res_mid_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text("O'rtadagi matnni yozing:", reply_markup=back_kb())
    ctx.user_data["res_field"] = "mid"
    return ST_RESULT_MID

async def res_mid_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    c = load()
    c.setdefault("result",{})["middle_text"] = update.message.text
    save(c)
    await update.message.reply_text("✅ Saqlandi!", reply_markup=MAIN_KB)
    return ST_MAIN

# ═══════════════════════════════════════════════
# FORM
# ═══════════════════════════════════════════════
async def menu_form(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    f = c.get("form", {})
    txt = (f"📝 *Forma sozlamalari*\n\n"
           f"Sarlavha: `{str(f.get('title',''))[:30]}`\n"
           f"Tugma: `{f.get('button_text','uni olish')}`\n"
           f"Guruh ID: `{f.get('group_id','—')}`")
    row = [
        [InlineKeyboardButton("Sarlavha",       callback_data="form_title")],
        [InlineKeyboardButton("Alt matn",       callback_data="form_sub")],
        [InlineKeyboardButton("Tugma matni",    callback_data="form_btn")],
        [InlineKeyboardButton("Guruh ID",       callback_data="form_group")],
        [InlineKeyboardButton("◀ Orqaga",       callback_data="back_main")],
    ]
    await update.callback_query.edit_message_text(txt, reply_markup=kb(row), parse_mode="Markdown")
    return ST_FORM_MENU

async def form_field_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE, field, prompt):
    await answer(update.callback_query)
    ctx.user_data["form_field"] = field
    await update.callback_query.edit_message_text(prompt, reply_markup=back_kb())

async def form_title_ask(update, ctx):
    await form_field_ask(update, ctx, "title", "Forma sarlavhasini yozing (\\n = yangi qator):")
    return ST_FORM_TITLE

async def form_sub_ask(update, ctx):
    await form_field_ask(update, ctx, "subtitle", "Forma alt matnini yozing:")
    return ST_FORM_SUB

async def form_btn_ask(update, ctx):
    await form_field_ask(update, ctx, "button_text", "Tugma matnini yozing:")
    return ST_FORM_BTN

async def form_group_ask(update, ctx):
    await form_field_ask(update, ctx, "group_id",
        "Guruh/kanal ID sini yozing:\n(Bot shu guruhning admini bo'lishi kerak)")
    return ST_FORM_GROUP

async def form_field_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    field = ctx.user_data.pop("form_field", "title")
    val   = update.message.text.replace("\\n", "\n")
    c = load()
    c.setdefault("form",{})[field] = val
    save(c)
    await update.message.reply_text("✅ Saqlandi!", reply_markup=MAIN_KB)
    return ST_MAIN

# ═══════════════════════════════════════════════
# WINNERS
# ═══════════════════════════════════════════════
async def menu_winners(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    ws = c.get("winners", [])
    txt = "🏆 *G'oliblar ro'yxati*\n\n"
    for i, w in enumerate(ws, 1):
        txt += f"{i}. {w['name']} — {w['discount']}\n"
    row = [
        [InlineKeyboardButton("➕ Qo'shish",       callback_data="win_add")],
        [InlineKeyboardButton("🗑 O'chirish",       callback_data="win_del")],
        [InlineKeyboardButton("📝 Sarlavha matni",  callback_data="win_hdr")],
        [InlineKeyboardButton("◀ Orqaga",           callback_data="back_main")],
    ]
    await update.callback_query.edit_message_text(txt, reply_markup=kb(row), parse_mode="Markdown")
    return ST_WINNERS_MENU

async def win_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    ctx.user_data["new_winner"] = {}
    await update.callback_query.edit_message_text("Isim yozing (masalan: Saidbek X.):", reply_markup=back_kb())
    return ST_WIN_ADD_NAME

async def win_add_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_winner"]["name"] = update.message.text.strip()
    await update.message.reply_text("Chegirma foizini yozing (masalan: 90%):")
    return ST_WIN_ADD_DISC

async def win_add_disc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_winner"]["discount"] = update.message.text.strip()
    c = load()
    c.setdefault("winners", []).append(ctx.user_data.pop("new_winner"))
    save(c)
    await update.message.reply_text("✅ G'olib qo'shildi!", reply_markup=MAIN_KB)
    return ST_MAIN

async def win_del_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    ws = c.get("winners", [])
    rows = [[InlineKeyboardButton(f"🗑 {w['name']} ({w['discount']})", callback_data=f"wdel_{i}")]
             for i, w in enumerate(ws)]
    rows.append([InlineKeyboardButton("◀ Orqaga", callback_data="menu_winners")])
    await update.callback_query.edit_message_text("Kimni o'chirasiz?", reply_markup=kb(rows))
    return ST_WIN_DEL

async def win_del_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    idx = int(update.callback_query.data.split("_")[1])
    c = load()
    ws = c.get("winners", [])
    if 0 <= idx < len(ws):
        ws.pop(idx)
        save(c)
    await update.callback_query.edit_message_text("✅ O'chirildi!", reply_markup=MAIN_KB)
    return ST_MAIN

async def win_hdr_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text(
        "G'oliblar sarlavha matnini yozing (\\n = yangi qator):", reply_markup=back_kb()
    )
    return ST_WIN_HDR

async def win_hdr_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    c = load()
    c["winners_header"] = update.message.text.replace("\\n", "\n")
    save(c)
    await update.message.reply_text("✅ Saqlandi!", reply_markup=MAIN_KB)
    return ST_MAIN

# ═══════════════════════════════════════════════
# AVATAR
# ═══════════════════════════════════════════════
async def menu_avatar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    await update.callback_query.edit_message_text(
        "👤 Avatar rasmni yuboring (photo sifatida):", reply_markup=back_kb()
    )
    return ST_AVATAR

async def got_avatar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file  = await ctx.bot.get_file(photo.file_id)
    fname = "avatar.jpg"
    await file.download_to_drive(UPLOADS_DIR / fname)
    c = load()
    c["avatar_url"] = f"/uploads/{fname}"
    save(c)
    await update.message.reply_text("✅ Avatar saqlandi!", reply_markup=MAIN_KB)
    return ST_MAIN

# ═══════════════════════════════════════════════
# FONT SIZES
# ═══════════════════════════════════════════════
FONT_FIELDS = {
    "message_text":    "Xabar matni",
    "timestamp":       "Vaqt belgisi",
    "winner_text":     "G'oliblar matni",
    "winners_header":  "G'oliblar sarlavhasi",
    "game_title":      "O'yin sarlavhasi",
    "win_popup_title": "G'alaba popup sarlavhasi",
    "win_popup_text":  "G'alaba popup matni",
    "form_title":      "Forma sarlavhasi",
    "form_subtitle":   "Forma alt matni",
    "submit_button":   "Tugma matni",
}

async def menu_fonts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    c = load()
    fs = c.get("font_sizes", {})
    txt = "🔤 *Shrift o'lchamlari* (px)\n\n"
    for k, v in FONT_FIELDS.items():
        txt += f"{v}: `{fs.get(k, '—')}`\n"
    rows = [[InlineKeyboardButton(v, callback_data=f"font_{k}")] for k, v in FONT_FIELDS.items()]
    rows.append([InlineKeyboardButton("◀ Orqaga", callback_data="back_main")])
    await update.callback_query.edit_message_text(txt, reply_markup=kb(rows), parse_mode="Markdown")
    return ST_FONT_SEL

async def font_sel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer(update.callback_query)
    field = update.callback_query.data.split("_", 1)[1]
    ctx.user_data["font_field"] = field
    await update.callback_query.edit_message_text(
        f"'{FONT_FIELDS.get(field, field)}' uchun o'lchamni yozing (px, masalan: 16):",
        reply_markup=back_kb()
    )
    return ST_FONT_VAL

async def font_val_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    field = ctx.user_data.pop("font_field", "")
    try: val = int(update.message.text.strip())
    except ValueError: val = 16
    c = load()
    c.setdefault("font_sizes", {})[field] = val
    save(c)
    await update.message.reply_text(f"✅ {FONT_FIELDS.get(field, field)}: {val}px", reply_markup=MAIN_KB)
    return ST_MAIN

# ═══════════════════════════════════════════════
# CONVERSATION HANDLER
# ═══════════════════════════════════════════════
def build_conv():
    text_f  = filters.TEXT & ~filters.COMMAND
    photo_f = filters.PHOTO

    return ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            ST_MAIN: [
                CallbackQueryHandler(menu_msg,      pattern="^menu_msg$"),
                CallbackQueryHandler(menu_game,     pattern="^menu_game$"),
                CallbackQueryHandler(menu_result,   pattern="^menu_result$"),
                CallbackQueryHandler(menu_form,     pattern="^menu_form$"),
                CallbackQueryHandler(menu_winners,  pattern="^menu_winners$"),
                CallbackQueryHandler(menu_avatar,   pattern="^menu_avatar$"),
                CallbackQueryHandler(menu_fonts,    pattern="^menu_fonts$"),
                CallbackQueryHandler(back_main,     pattern="^back_main$"),
            ],
            # ---- Messages ----
            ST_MSG_MENU: [
                CallbackQueryHandler(msg_add_start,  pattern="^msg_add$"),
                CallbackQueryHandler(msg_edit_start, pattern="^msg_edit$"),
                CallbackQueryHandler(msg_del_start,  pattern="^msg_del$"),
                CallbackQueryHandler(back_main,      pattern="^back_main$"),
            ],
            ST_MSG_ADD_TEXT:    [MessageHandler(text_f, msg_add_text)],
            ST_MSG_DELAY:       [MessageHandler(text_f, msg_add_delay)],
            ST_MSG_ADD_IMG: [
                CallbackQueryHandler(msg_img_yes, pattern="^msg_img_yes$"),
                CallbackQueryHandler(msg_img_no,  pattern="^msg_img_no$"),
                MessageHandler(photo_f, msg_got_photo),
            ],
            ST_MSG_ADD_QA: [
                CallbackQueryHandler(qa_yes, pattern="^qa_yes$"),
                CallbackQueryHandler(qa_no,  pattern="^qa_no$"),
            ],
            ST_MSG_ADD_QA_ANS:  [MessageHandler(text_f, got_qa_answers)],
            ST_MSG_EDIT_SEL: [
                CallbackQueryHandler(msg_edit_sel, pattern="^edit_msg_"),
                CallbackQueryHandler(menu_msg,     pattern="^menu_msg$"),
            ],
            ST_MSG_EDIT_TEXT:   [MessageHandler(text_f, msg_edit_text)],
            ST_MSG_DEL_SEL: [
                CallbackQueryHandler(msg_del_confirm, pattern="^del_msg_"),
                CallbackQueryHandler(menu_msg,        pattern="^menu_msg$"),
            ],
            # ---- Game ----
            ST_GAME_MENU: [
                CallbackQueryHandler(game_type_ask,    pattern="^game_type$"),
                CallbackQueryHandler(game_title_ask,   pattern="^game_title$"),
                CallbackQueryHandler(game_win_val_ask, pattern="^game_win_val$"),
                CallbackQueryHandler(game_win_ptitle_ask, pattern="^game_win_ptitle$"),
                CallbackQueryHandler(game_win_ptext_ask,  pattern="^game_win_ptext$"),
                CallbackQueryHandler(game_sound_ask,   pattern="^game_sound$"),
                CallbackQueryHandler(back_main,        pattern="^back_main$"),
            ],
            ST_GAME_TYPE: [
                CallbackQueryHandler(game_type_set, pattern="^gtype_"),
                CallbackQueryHandler(menu_game,     pattern="^menu_game$"),
            ],
            ST_GAME_TITLE:     [MessageHandler(text_f, game_field_set)],
            ST_GAME_WIN_VAL:   [MessageHandler(text_f, game_field_set)],
            ST_GAME_WIN_PTITLE:[MessageHandler(text_f, game_field_set)],
            ST_GAME_WIN_PTEXT: [MessageHandler(text_f, game_field_set)],
            ST_GAME_SOUND:     [MessageHandler(text_f, game_field_set)],
            # ---- Result ----
            ST_RESULT_MENU: [
                CallbackQueryHandler(res_img_ask, pattern="^res_img$"),
                CallbackQueryHandler(res_cd_ask,  pattern="^res_cd$"),
                CallbackQueryHandler(res_mid_ask, pattern="^res_mid$"),
                CallbackQueryHandler(back_main,   pattern="^back_main$"),
            ],
            ST_RESULT_IMG: [MessageHandler(photo_f, res_got_photo)],
            ST_RESULT_CD:  [MessageHandler(text_f,  res_cd_set)],
            ST_RESULT_MID: [MessageHandler(text_f,  res_mid_set)],
            # ---- Form ----
            ST_FORM_MENU: [
                CallbackQueryHandler(form_title_ask,  pattern="^form_title$"),
                CallbackQueryHandler(form_sub_ask,    pattern="^form_sub$"),
                CallbackQueryHandler(form_btn_ask,    pattern="^form_btn$"),
                CallbackQueryHandler(form_group_ask,  pattern="^form_group$"),
                CallbackQueryHandler(back_main,       pattern="^back_main$"),
            ],
            ST_FORM_TITLE: [MessageHandler(text_f, form_field_set)],
            ST_FORM_SUB:   [MessageHandler(text_f, form_field_set)],
            ST_FORM_BTN:   [MessageHandler(text_f, form_field_set)],
            ST_FORM_GROUP: [MessageHandler(text_f, form_field_set)],
            # ---- Winners ----
            ST_WINNERS_MENU: [
                CallbackQueryHandler(win_add_start, pattern="^win_add$"),
                CallbackQueryHandler(win_del_start, pattern="^win_del$"),
                CallbackQueryHandler(win_hdr_ask,   pattern="^win_hdr$"),
                CallbackQueryHandler(back_main,     pattern="^back_main$"),
            ],
            ST_WIN_ADD_NAME: [MessageHandler(text_f, win_add_name)],
            ST_WIN_ADD_DISC: [MessageHandler(text_f, win_add_disc)],
            ST_WIN_HDR:      [MessageHandler(text_f, win_hdr_set)],
            ST_WIN_DEL: [
                CallbackQueryHandler(win_del_confirm, pattern="^wdel_"),
                CallbackQueryHandler(menu_winners,    pattern="^menu_winners$"),
            ],
            # ---- Fonts ----
            ST_FONT_SEL: [
                CallbackQueryHandler(font_sel,  pattern="^font_"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
            ST_FONT_VAL: [MessageHandler(text_f, font_val_set)],
            # ---- Avatar ----
            ST_AVATAR: [
                MessageHandler(photo_f, got_avatar),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(back_main, pattern="^back_main$"),
        ],
        per_message=False,
    )

# ───────── MAIN ─────────
def main():
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log.info("Flask server started on http://0.0.0.0:8080")

    # Build and run bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(build_conv())
    log.info("Bot started. Polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
