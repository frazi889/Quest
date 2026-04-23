import logging
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ----------------------------
# Simple health server for Render Web Service
# ----------------------------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Quiz Bot is running")

    def log_message(self, format, *args):
        return


def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info("Health server running on port %s", PORT)
    server.serve_forever()


# ----------------------------
# Question Bank
# answer = correct option index (0,1,2,3)
# ----------------------------
QUESTION_BANK = {
    "english": [
        {
            "question": "What is the synonym of 'happy'?",
            "options": ["Sad", "Glad", "Angry", "Weak"],
            "answer": 1,
        },
        {
            "question": "Choose the correct spelling.",
            "options": ["Beautifull", "Beautiful", "Beutiful", "Beautifool"],
            "answer": 1,
        },
        {
            "question": "What is the antonym of 'hot'?",
            "options": ["Cold", "Warm", "Boiling", "Heat"],
            "answer": 0,
        },
        {
            "question": "Which one is a verb?",
            "options": ["Beautiful", "Quickly", "Run", "Blue"],
            "answer": 2,
        },
        {
            "question": "Which sentence is correct?",
            "options": ["He go to school.", "He goes to school.", "He going school.", "He gone to school."],
            "answer": 1,
        },
    ],
    "gk": [
        {
            "question": "What is the capital of Japan?",
            "options": ["Seoul", "Tokyo", "Bangkok", "Beijing"],
            "answer": 1,
        },
        {
            "question": "How many continents are there?",
            "options": ["5", "6", "7", "8"],
            "answer": 2,
        },
        {
            "question": "Which planet is known as the Red Planet?",
            "options": ["Earth", "Mars", "Jupiter", "Venus"],
            "answer": 1,
        },
        {
            "question": "Which ocean is the largest?",
            "options": ["Atlantic", "Indian", "Arctic", "Pacific"],
            "answer": 3,
        },
        {
            "question": "Which country is famous for the Eiffel Tower?",
            "options": ["Italy", "France", "Germany", "Spain"],
            "answer": 1,
        },
    ],
    "science": [
        {
            "question": "Plants make food by which process?",
            "options": ["Respiration", "Digestion", "Photosynthesis", "Evaporation"],
            "answer": 2,
        },
        {
            "question": "What gas do humans need to breathe?",
            "options": ["Carbon dioxide", "Hydrogen", "Oxygen", "Nitrogen"],
            "answer": 2,
        },
        {
            "question": "Which part of the body pumps blood?",
            "options": ["Lungs", "Brain", "Heart", "Liver"],
            "answer": 2,
        },
        {
            "question": "Water freezes at what temperature (C)?",
            "options": ["0", "10", "50", "100"],
            "answer": 0,
        },
        {
            "question": "Which organ helps us see?",
            "options": ["Ear", "Eye", "Nose", "Skin"],
            "answer": 1,
        },
    ],
    "math": [
        {
            "question": "What is 2 + 2?",
            "options": ["2", "3", "4", "5"],
            "answer": 2,
        },
        {
            "question": "What is 10 x 5?",
            "options": ["15", "50", "40", "100"],
            "answer": 1,
        },
        {
            "question": "What is 12 ÷ 3?",
            "options": ["3", "4", "5", "6"],
            "answer": 1,
        },
        {
            "question": "What is 9 - 4?",
            "options": ["3", "4", "5", "6"],
            "answer": 2,
        },
        {
            "question": "What is the square of 6?",
            "options": ["12", "18", "24", "36"],
            "answer": 3,
        },
    ],
    "physics": [
        {
            "question": "Unit of force is?",
            "options": ["Joule", "Newton", "Watt", "Volt"],
            "answer": 1,
        },
        {
            "question": "What pulls objects toward Earth?",
            "options": ["Heat", "Light", "Gravity", "Sound"],
            "answer": 2,
        },
        {
            "question": "Unit of current is?",
            "options": ["Ampere", "Meter", "Kelvin", "Pascal"],
            "answer": 0,
        },
        {
            "question": "Speed = ?",
            "options": ["Distance / Time", "Time / Distance", "Mass x Time", "Force / Area"],
            "answer": 0,
        },
        {
            "question": "Which one is a form of energy?",
            "options": ["Mass", "Velocity", "Heat", "Length"],
            "answer": 2,
        },
    ],
    "chemistry": [
        {
            "question": "Symbol of water is?",
            "options": ["O2", "H2O", "CO2", "NaCl"],
            "answer": 1,
        },
        {
            "question": "pH less than 7 means?",
            "options": ["Acid", "Base", "Neutral", "Salt"],
            "answer": 0,
        },
        {
            "question": "Common salt chemical formula is?",
            "options": ["NaCl", "H2SO4", "KOH", "CaCO3"],
            "answer": 0,
        },
        {
            "question": "Which is a gas?",
            "options": ["Iron", "Oxygen", "Wood", "Glass"],
            "answer": 1,
        },
        {
            "question": "Which one is an acid?",
            "options": ["HCl", "NaOH", "KOH", "Ca(OH)2"],
            "answer": 0,
        },
    ],
}

SUBJECT_LABELS = {
    "english": "📘 English",
    "gk": "🌍 GK",
    "science": "🧪 Science",
    "math": "➗ Math",
    "physics": "⚛️ Physics",
    "chemistry": "⚗️ Chemistry",
}


# ----------------------------
# Session Helpers
# ----------------------------
def reset_session(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["subject"] = None
    context.user_data["questions"] = []
    context.user_data["index"] = 0
    context.user_data["score"] = 0


def subject_keyboard():
    return InlineKeyboardMarkup([
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
    ])


def result_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔁 Restart", callback_data="restart"),
            InlineKeyboardButton("🏠 Subjects", callback_data="subjects"),
        ]
    ])


def answer_keyboard(options):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"A. {options[0]}", callback_data="answer:0")],
        [InlineKeyboardButton(f"B. {options[1]}", callback_data="answer:1")],
        [InlineKeyboardButton(f"C. {options[2]}", callback_data="answer:2")],
        [InlineKeyboardButton(f"D. {options[3]}", callback_data="answer:3")],
    ])


async def show_question(query, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data["questions"]
    index = context.user_data["index"]
    score = context.user_data["score"]
    subject = context.user_data["subject"]

    if index >= len(questions):
        await query.edit_message_text(
            text=(
                "🎉 Quiz Finished!\n\n"
                f"📘 Subject: {SUBJECT_LABELS.get(subject, subject)}\n"
                f"✅ Score: {score}/{len(questions)}"
            ),
            reply_markup=result_keyboard(),
        )
        return

    q = questions[index]
    await query.edit_message_text(
        text=(
            f"{SUBJECT_LABELS.get(subject, subject)}\n"
            f"❓ Question {index + 1}/{len(questions)}\n"
            f"🏆 Score: {score}\n\n"
            f"{q['question']}"
        ),
        reply_markup=answer_keyboard(q["options"]),
    )


# ----------------------------
# Handlers
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_session(context)
    text = (
        "👋 Welcome to Study Quiz Bot!\n\n"
        "Subjects:\n"
        "📘 English\n"
        "🌍 General Knowledge\n"
        "🧪 Science\n"
        "➗ Math\n"
        "⚛️ Physics\n"
        "⚗️ Chemistry\n\n"
        "အောက်က subject ကိုရွေးပါ။"
    )
    await update.message.reply_text(text, reply_markup=subject_keyboard())


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("subject:"):
        subject = data.split(":", 1)[1]
        questions = QUESTION_BANK.get(subject, [])[:]
        random.shuffle(questions)

        context.user_data["subject"] = subject
        context.user_data["questions"] = questions
        context.user_data["index"] = 0
        context.user_data["score"] = 0

        await show_question(query, context)
        return

    if data.startswith("answer:"):
        selected = int(data.split(":", 1)[1])
        index = context.user_data["index"]
        questions = context.user_data["questions"]
        current = questions[index]
        correct = current["answer"]

        if selected == correct:
            context.user_data["score"] += 1
            text = "✅ Correct!"
        else:
            text = f"❌ Wrong!\nCorrect answer: {current['options'][correct]}"

        context.user_data["index"] += 1

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ Next", callback_data="next")]
        ])

        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "next":
        await show_question(query, context)
        return

    if data == "restart":
        subject = context.user_data.get("subject")
        if not subject:
            await query.edit_message_text("Subject ကိုပြန်ရွေးပါ။", reply_markup=subject_keyboard())
            return

        questions = QUESTION_BANK.get(subject, [])[:]
        random.shuffle(questions)
        context.user_data["questions"] = questions
        context.user_data["index"] = 0
        context.user_data["score"] = 0

        await show_question(query, context)
        return

    if data == "subjects":
        reset_session(context)
        await query.edit_message_text("📚 Subject ကိုရွေးပါ။", reply_markup=subject_keyboard())
        return


def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Starting Quiz Bot...")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
