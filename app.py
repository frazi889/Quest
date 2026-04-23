import json
import logging
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))
QUESTIONS_FILE = Path("questions.json")
QUESTIONS_PER_ROUND = 10

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__) 

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Quiz Bot is running")

    def log_message(self, format, *args):
        return


def run_health_server() -> None:
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info("Health server running on port %s", PORT)
    server.serve_forever()


def load_questions() -> dict:
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError("questions.json not found")

    with QUESTIONS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


QUESTION_BANK = load_questions()

SUBJECTS = {
    "english": "📘 English",
    "gk": "🌍 General Knowledge",
    "science": "🧪 Science",
    "math": "➗ Math",
    "physics": "⚛️ Physics",
    "chemistry": "⚗️ Chemistry",
}

LEVELS = {
    "easy": "🟢 Easy",
    "medium": "🟡 Medium",
    "hard": "🔴 Hard",
} 

def init_user_session(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["subject"] = None
    context.user_data["level"] = None
    context.user_data["questions"] = []
    context.user_data["index"] = 0
    context.user_data["score"] = 0
    context.user_data["answered"] = False


def get_questions(subject: str, level: str) -> list:
    subject_data = QUESTION_BANK.get(subject, {})
    level_data = subject_data.get(level, [])
    return level_data


def pick_round_questions(subject: str, level: str, count: int = QUESTIONS_PER_ROUND) -> list:
    questions = get_questions(subject, level)
    if not questions:
        return []

    if len(questions) <= count:
        selected = questions[:]
        random.shuffle(selected)
        return selected

    return random.sample(questions, count) 

def subject_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📘 English", callback_data="subject:english"),
            InlineKeyboardButton("🌍 GK", callback_data="subject:gk"),
        ],
        [
            InlineKeyboardButton("🧪 Science", callback_data="subject:science"),
            InlineKeyboardButton("➗ Math", callback_data="subject:math"),
        ],
        [
            InlineKeyboardButton("⚛️ Physics", callback_data="subject:physics"),
            InlineKeyboardButton("⚗️ Chemistry", callback_data="subject:chemistry"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def level_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🟢 Easy", callback_data="level:easy"),
            InlineKeyboardButton("🟡 Medium", callback_data="level:medium"),
        ],
        [
            InlineKeyboardButton("🔴 Hard", callback_data="level:hard"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="back:subjects"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def result_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("▶️ Continue", callback_data="continue_quiz"),
            InlineKeyboardButton("🔁 Restart", callback_data="restart_quiz"),
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="back:subjects"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard) 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    init_user_session(context)

    text = (
        "👋 Welcome to Study Quiz Bot!\n\n"
        "📚 Subjects:\n"
        "• English\n"
        "• General Knowledge\n"
        "• Science\n"
        "• Math\n"
        "• Physics\n"
        "• Chemistry\n\n"
        "အောက်က subject ကိုရွေးပြီး quiz စပါ။"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=subject_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=subject_keyboard())


async def send_question(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    questions = context.user_data.get("questions", [])
    index = context.user_data.get("index", 0)
    score = context.user_data.get("score", 0)

    if index >= len(questions):
        await show_result(query, context)
        return

    q = questions[index]
    subject = context.user_data.get("subject", "unknown")
    level = context.user_data.get("level", "unknown")

    keyboard = [
        [InlineKeyboardButton(f"A. {q['options'][0]}", callback_data="answer:0")],
        [InlineKeyboardButton(f"B. {q['options'][1]}", callback_data="answer:1")],
        [InlineKeyboardButton(f"C. {q['options'][2]}", callback_data="answer:2")],
        [InlineKeyboardButton(f"D. {q['options'][3]}", callback_data="answer:3")],
    ]

    text = (
        f"📘 Subject: {SUBJECTS.get(subject, subject)}\n"
        f"🎯 Level: {LEVELS.get(level, level)}\n"
        f"❓ Question {index + 1}/{len(questions)}\n"
        f"🏆 Score: {score}\n\n"
        f"{q['question']}"
    )

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
  ) 

async def show_result(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    score = context.user_data.get("score", 0)
    total = len(context.user_data.get("questions", []))
    subject = SUBJECTS.get(context.user_data.get("subject", ""), "")
    level = LEVELS.get(context.user_data.get("level", ""), "")

    text = (
        "🎉 Quiz Finished!\n\n"
        f"📘 Subject: {subject}\n"
        f"🎯 Level: {level}\n"
        f"✅ Score: {score}/{total}\n"
    )

    await query.edit_message_text(
        text=text,
        reply_markup=result_keyboard(),
    )


async def handle_subject_callback(query, context: ContextTypes.DEFAULT_TYPE, subject: str) -> None:
    context.user_data["subject"] = subject
    context.user_data["level"] = None

    await query.edit_message_text(
        text=f"{SUBJECTS.get(subject)} ကိုရွေးထားပါတယ်။\n\nLevel ရွေးပါ။",
        reply_markup=level_keyboard(),
    ) 

async def show_result(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    score = context.user_data.get("score", 0)
    total = len(context.user_data.get("questions", []))
    subject = SUBJECTS.get(context.user_data.get("subject", ""), "")
    level = LEVELS.get(context.user_data.get("level", ""), "")

    text = (
        "🎉 Quiz Finished!\n\n"
        f"📘 Subject: {subject}\n"
        f"🎯 Level: {level}\n"
        f"✅ Score: {score}/{total}\n"
    )

    await query.edit_message_text(
        text=text,
        reply_markup=result_keyboard(),
    )


async def handle_subject_callback(query, context: ContextTypes.DEFAULT_TYPE, subject: str) -> None:
    context.user_data["subject"] = subject
    context.user_data["level"] = None

    await query.edit_message_text(
        text=f"{SUBJECTS.get(subject)} ကိုရွေးထားပါတယ်။\n\nLevel ရွေးပါ။",
        reply_markup=level_keyboard(),
  ) 

async def handle_level_callback(query, context: ContextTypes.DEFAULT_TYPE, level: str) -> None:
    subject = context.user_data.get("subject")
    if not subject:
        await query.edit_message_text(
            text="Subject အရင်ရွေးပါ။",
            reply_markup=subject_keyboard(),
        )
        return

    selected_questions = pick_round_questions(subject, level, QUESTIONS_PER_ROUND)
    if not selected_questions:
        await query.edit_message_text(
            text="ဒီ subject/level အတွက် questions မရှိသေးပါ။",
            reply_markup=subject_keyboard(),
        )
        return

    context.user_data["level"] = level
    context.user_data["questions"] = selected_questions
    context.user_data["index"] = 0
    context.user_data["score"] = 0
    context.user_data["answered"] = False

    await send_question(query, context)


async def handle_answer_callback(query, context: ContextTypes.DEFAULT_TYPE, selected_idx: int) -> None:
    questions = context.user_data.get("questions", [])
    index = context.user_data.get("index", 0)

    if index >= len(questions):
        await show_result(query, context)
        return

    current_q = questions[index]
    correct_idx = current_q["answer"]

    if selected_idx == correct_idx:
        context.user_data["score"] += 1
        result_text = "✅ Correct!"
    else:
        result_text = (
            "❌ Wrong!\n"
            f"Correct Answer: {current_q['options'][correct_idx]}"
        )

    context.user_data["index"] += 1

    keyboard = [
        [InlineKeyboardButton("➡️ Next Question", callback_data="next_question")]
    ]

    await query.edit_message_text(
        text=result_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    ) 

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    if data.startswith("subject:"):
        subject = data.split(":", 1)[1]
        await handle_subject_callback(query, context, subject)
        return

    if data.startswith("level:"):
        level = data.split(":", 1)[1]
        await handle_level_callback(query, context, level)
        return

    if data.startswith("answer:"):
        selected_idx = int(data.split(":", 1)[1])
        await handle_answer_callback(query, context, selected_idx)
        return

    if data == "next_question":
        await send_question(query, context)
        return

    if data == "continue_quiz":
        subject = context.user_data.get("subject")
        level = context.user_data.get("level")
        selected_questions = pick_round_questions(subject, level, QUESTIONS_PER_ROUND)

        context.user_data["questions"] = selected_questions
        context.user_data["index"] = 0
        context.user_data["score"] = 0

        await send_question(query, context)
        return

    if data == "restart_quiz":
        init_user_session(context)
        await query.edit_message_text(
            text="🔁 Quiz restarted.\n\nSubject ကိုပြန်ရွေးပါ။",
            reply_markup=subject_keyboard(),
        )
        return

    if data == "back:subjects":
        init_user_session(context)
        await query.edit_message_text(
            text="📚 Subject ကိုရွေးပါ။",
            reply_markup=subject_keyboard(),
        )
        return


def main() -> None:
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))

    logger.info("Starting Study Quiz Bot...")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main() 


