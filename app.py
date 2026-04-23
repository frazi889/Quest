import logging
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
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


# ---------------- HEALTH SERVER ----------------
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


# ---------------- QUESTION GENERATOR ----------------
def make_question(question: str, options: list[str], answer: int) -> dict:
    return {"q": question, "o": options, "a": answer}


def generate_english_questions() -> list[dict]:
    questions = []

    words = [
        ("happy", "glad", "sad", "angry", "weak"),
        ("big", "large", "tiny", "short", "low"),
        ("smart", "clever", "dull", "lazy", "weak"),
        ("fast", "quick", "slow", "late", "weak"),
        ("begin", "start", "stop", "end", "close"),
        ("small", "tiny", "huge", "wide", "tall"),
        ("angry", "furious", "calm", "happy", "weak"),
        ("easy", "simple", "hard", "heavy", "strong"),
        ("end", "finish", "open", "build", "start"),
        ("rich", "wealthy", "poor", "weak", "empty"),
    ]
    for i in range(20):
        w = words[i % len(words)]
        questions.append(
            make_question(
                f"What is the synonym of '{w[0]}'?",
                [w[2], w[1], w[3], w[4]],
                1,
            )
        )

    spellings = [
        ("Beautiful", ["Beautifull", "Beautiful", "Beutiful", "Beautifool"], 1),
        ("Receive", ["Recieve", "Receive", "Receeve", "Reseive"], 1),
        ("February", ["Febuary", "February", "Febrary", "Feburuary"], 1),
        ("Tomorrow", ["Tommorow", "Tomorrow", "Tommorrow", "Tomorow"], 1),
        ("Definitely", ["Definately", "Definitely", "Definatly", "Defenitely"], 1),
        ("Separate", ["Seperate", "Separate", "Seperete", "Separrate"], 1),
        ("Successful", ["Succesful", "Successful", "Successfull", "Sucessful"], 1),
        ("Accommodation", ["Acomodation", "Accommodation", "Accomodation", "Acommodation"], 1),
        ("Environment", ["Enviroment", "Environment", "Environmant", "Enviornment"], 1),
        ("Necessary", ["Necesary", "Necessary", "Neccessary", "Necassary"], 1),
    ]
    for i in range(20):
        s = spellings[i % len(spellings)]
        questions.append(make_question("Choose the correct spelling.", s[1], s[2])) 

grammar = [
        ("What is the past tense of 'go'?", ["Goed", "Went", "Gone", "Going"], 1),
        ("What is the plural of 'child'?", ["Childs", "Children", "Childes", "Child"], 1),
        ("Which one is a verb?", ["Blue", "Quickly", "Run", "Beauty"], 2),
        ("Choose the correct article: ___ apple", ["a", "an", "the", "no article"], 1),
        ("What is the past tense of 'eat'?", ["Eated", "Ate", "Eaten", "Eating"], 1),
        ("What is the plural of 'mouse'?", ["Mouses", "Mouse", "Mice", "Mices"], 2),
        ("Choose the correct article: ___ hour", ["a", "an", "the", "no article"], 1),
        ("What is the past tense of 'write'?", ["Writed", "Written", "Wrote", "Writing"], 2),
        ("What is the plural of 'woman'?", ["Womans", "Women", "Womanes", "Womens"], 1),
        ("What is the past tense of 'buy'?", ["Buyed", "Bought", "Buy", "Buying"], 1),
    ]
    for i in range(20):
        g = grammar[i % len(grammar)]
        questions.append(make_question(g[0], g[1], g[2]))

    sentence_sets = [
        ("Choose the correct sentence.", ["He go to school.", "He goes to school.", "He going school.", "He gone to school."], 1),
        ("Choose the correct sentence.", ["She don't like tea.", "She doesn't likes tea.", "She doesn't like tea.", "She not like tea."], 2),
        ("Choose the correct sentence.", ["They is playing.", "They are playing.", "They am playing.", "They playing are."], 1),
        ("Choose the correct sentence.", ["I has a pen.", "I have a pen.", "I am have a pen.", "I having a pen."], 1),
        ("Choose the correct sentence.", ["We was late.", "We were late.", "We is late.", "We be late."], 1),
        ("Choose the correct sentence.", ["There is many books.", "There are many books.", "There be many books.", "There many books are."], 1),
        ("Choose the correct sentence.", ["She have a cat.", "She has a cat.", "She having a cat.", "She haves a cat."], 1),
        ("Choose the correct sentence.", ["Does he likes tea?", "Does he like tea?", "Do he like tea?", "He does like tea?"], 1),
        ("Choose the correct sentence.", ["I didn't went.", "I didn't go.", "I doesn't go.", "I not go."], 1),
        ("Which sentence is correct?", ["He don't play.", "He doesn't play.", "He not plays.", "He isn't play."], 1),
    ]
    for i in range(20):
        s = sentence_sets[i % len(sentence_sets)]
        questions.append(make_question(s[0], s[1], s[2]))

    misc = [
        ("Which word is a noun?", ["Run", "Happiness", "Quickly", "Slow"], 1),
        ("Which word is an adjective?", ["Beautiful", "Run", "Slowly", "Book"], 0),
        ("Which word is an adverb?", ["Quickly", "Quick", "Quickness", "Quicker"], 0),
        ("Which word is a preposition?", ["Under", "Jump", "Blue", "Soft"], 0),
        ("Which is a conjunction?", ["And", "Table", "Fast", "She"], 0),
        ("Which is a pronoun?", ["Table", "He", "Red", "Run"], 1),
        ("Which word is an interjection?", ["Oh!", "Walk", "Happy", "Inside"], 0),
        ("Which word is a determiner?", ["This", "Jump", "Blue", "Slowly"], 0),
        ("Which word is a possessive pronoun?", ["Mine", "Me", "I", "My"], 0),
        ("Which is a reflexive pronoun?", ["Myself", "Me", "Mine", "My"], 0),
    ]
    for i in range(20):
        m = misc[i % len(misc)]
        questions.append(make_question(m[0], m[1], m[2]))

    return questions[:100] 

def generate_gk_questions() -> list[dict]:
    base = [
        ("What is the capital of Japan?", ["Seoul", "Tokyo", "Bangkok", "Beijing"], 1),
        ("How many continents are there?", ["5", "6", "7", "8"], 2),
        ("Which planet is known as the Red Planet?", ["Earth", "Mars", "Jupiter", "Venus"], 1),
        ("Which ocean is the largest?", ["Atlantic", "Indian", "Arctic", "Pacific"], 3),
        ("Which country is famous for the Eiffel Tower?", ["Italy", "France", "Germany", "Spain"], 1),
        ("What is the capital of Thailand?", ["Bangkok", "Tokyo", "Hanoi", "Seoul"], 0),
        ("What is the capital of Myanmar?", ["Yangon", "Mandalay", "Naypyidaw", "Bago"], 2),
        ("Which continent is Egypt in?", ["Asia", "Africa", "Europe", "Australia"], 1),
        ("What is the capital of South Korea?", ["Busan", "Tokyo", "Seoul", "Beijing"], 2),
        ("Which is the largest planet?", ["Mars", "Saturn", "Earth", "Jupiter"], 3),
        ("Which country has the Great Wall?", ["Japan", "China", "India", "Korea"], 1),
        ("Which country uses the yen?", ["China", "Thailand", "Japan", "Vietnam"], 2),
        ("What is the national animal of Myanmar?", ["Tiger", "Elephant", "Peacock", "Lion"], 2),
        ("Which desert is the largest hot desert?", ["Gobi", "Kalahari", "Sahara", "Arabian"], 2),
        ("How many days are there in a leap year?", ["364", "365", "366", "367"], 2),
        ("Which month has 28 days in a normal year?", ["February", "January", "March", "December"], 0),
        ("What color are emeralds?", ["Red", "Blue", "Green", "Yellow"], 2),
        ("Which animal is known as the king of the jungle?", ["Tiger", "Elephant", "Lion", "Leopard"], 2),
        ("What is the capital of India?", ["Mumbai", "Delhi", "Kolkata", "Chennai"], 1),
        ("Which country is famous for pizza?", ["France", "Italy", "Spain", "Germany"], 1),
    ]
    questions = []
    for i in range(5):
        for q in base:
            questions.append(make_question(q[0], q[1], q[2]))
    return questions[:100]


def generate_science_questions() -> list[dict]:
    base = [
        ("Plants make food by which process?", ["Respiration", "Digestion", "Photosynthesis", "Evaporation"], 2),
        ("What gas do humans need to breathe?", ["Carbon dioxide", "Hydrogen", "Oxygen", "Nitrogen"], 2),
        ("Which part of the body pumps blood?", ["Lungs", "Brain", "Heart", "Liver"], 2),
        ("Water freezes at what temperature (C)?", ["0", "10", "50", "100"], 0),
        ("Which organ helps us see?", ["Ear", "Eye", "Nose", "Skin"], 1),
        ("What planet do we live on?", ["Mars", "Earth", "Jupiter", "Venus"], 1),
        ("Which gas do plants use in photosynthesis?", ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], 2),
        ("How many legs does an insect have?", ["4", "6", "8", "10"], 1),
        ("Which part of a plant absorbs water?", ["Leaf", "Flower", "Root", "Stem"], 2),
        ("Which vitamin do we get from sunlight?", ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], 3),
        ("What is H2O commonly called?", ["Salt", "Water", "Oxygen", "Sugar"], 1),
        ("Which organ helps us breathe?", ["Heart", "Liver", "Lungs", "Kidney"], 2),
        ("What do bees make?", ["Milk", "Honey", "Juice", "Wax paper"], 1),
        ("Which celestial body gives Earth light during the day?", ["Moon", "Sun", "Mars", "Star"], 1),
        ("Which blood cells fight germs?", ["Red blood cells", "White blood cells", "Platelets", "Plasma"], 1),
        ("Which sense organ is used for hearing?", ["Eye", "Ear", "Nose", "Tongue"], 1),
        ("How many planets are in the solar system?", ["7", "8", "9", "10"], 1),
        ("What is the boiling point of water in Celsius?", ["50", "75", "100", "120"], 2),
        ("Which organ filters blood?", ["Kidney", "Heart", "Lung", "Brain"], 0),
        ("Which animal changes from caterpillar to butterfly?", ["Ant", "Bee", "Butterfly", "Spider"], 2),
    ]
    questions = []
    for i in range(5):
        for q in base:
            questions.append(make_question(q[0], q[1], q[2]))
    return questions[:100] 

def generate_math_questions() -> list[dict]:
    base = [
        ("What is 2 + 2?", ["2", "3", "4", "5"], 2),
        ("What is 10 x 5?", ["15", "50", "40", "100"], 1),
        ("What is 12 ÷ 3?", ["3", "4", "5", "6"], 1),
        ("What is 9 - 4?", ["3", "4", "5", "6"], 2),
        ("What is the square of 6?", ["12", "18", "24", "36"], 3),
        ("What is 7 + 8?", ["14", "15", "16", "17"], 1),
        ("What is 15 - 7?", ["6", "7", "8", "9"], 2),
        ("What is 9 x 9?", ["72", "81", "99", "90"], 1),
        ("What is 20 ÷ 4?", ["4", "5", "6", "7"], 1),
        ("What is 11 + 13?", ["22", "23", "24", "25"], 2),
        ("What is 100 - 45?", ["45", "50", "55", "60"], 2),
        ("What is 8 x 7?", ["54", "56", "58", "60"], 1),
        ("What is 49 ÷ 7?", ["6", "7", "8", "9"], 1),
        ("What is half of 50?", ["20", "25", "30", "35"], 1),
        ("What is 3 squared?", ["6", "9", "12", "3"], 1),
        ("What is 5 cubed?", ["15", "25", "75", "125"], 3),
        ("What is 18 + 27?", ["43", "44", "45", "46"], 2),
        ("What is 90 ÷ 10?", ["8", "9", "10", "11"], 1),
        ("What is 14 x 2?", ["26", "27", "28", "29"], 2),
        ("What is 81 - 19?", ["60", "61", "62", "63"], 2),
    ]
    questions = []
    for i in range(5):
        for q in base:
            questions.append(make_question(q[0], q[1], q[2]))
    return questions[:100]


def generate_physics_questions() -> list[dict]:
    base = [
        ("Unit of force is?", ["Joule", "Newton", "Watt", "Volt"], 1),
        ("What pulls objects toward Earth?", ["Heat", "Light", "Gravity", "Sound"], 2),
        ("Unit of current is?", ["Ampere", "Meter", "Kelvin", "Pascal"], 0),
        ("Speed = ?", ["Distance / Time", "Time / Distance", "Mass x Time", "Force / Area"], 0),
        ("Which one is a form of energy?", ["Mass", "Velocity", "Heat", "Length"], 2),
        ("Unit of power is?", ["Volt", "Watt", "Newton", "Pascal"], 1),
        ("Which travels fastest?", ["Sound", "Light", "Rain", "Wind"], 1),
        ("What device measures temperature?", ["Barometer", "Thermometer", "Ammeter", "Speedometer"], 1),
        ("What is the SI unit of length?", ["Centimeter", "Meter", "Kilometer", "Inch"], 1),
        ("What is the SI unit of mass?", ["Gram", "Milligram", "Kilogram", "Ton"], 2),
        ("Which force slows moving objects?", ["Magnetism", "Gravity", "Friction", "Electricity"], 2),
        ("Which mirror gives an upright virtual image?", ["Concave", "Convex", "Plane", "Both convex and plane"], 3),
        ("Which quantity has both magnitude and direction?", ["Speed", "Distance", "Vector", "Mass"], 2),
        ("What is the speed of light closest to?", ["3 x 10^8 m/s", "3 x 10^6 m/s", "3 x 10^5 m/s", "3 x 10^3 m/s"], 0),
        ("What is used to measure electric current?", ["Voltmeter", "Ammeter", "Barometer", "Thermometer"], 1),
        ("Which energy is stored in food?", ["Heat", "Chemical", "Light", "Nuclear"], 1),
        ("What happens to objects in free fall?", ["They move upward", "They accelerate downward", "They stop", "They lose mass"], 1),
        ("Sound needs what to travel?", ["Vacuum", "Medium", "Sunlight", "Darkness"], 1),
        ("Which color of light has highest frequency?", ["Red", "Blue", "Violet", "Green"], 2),
        ("Which law explains action and reaction?", ["Newton's First Law", "Newton's Second Law", "Newton's Third Law", "Ohm's Law"], 2),
    ]
    questions = []
    for i in range(5):
        for q in base:
            questions.append(make_question(q[0], q[1], q[2]))
    return questions[:100]


def generate_chemistry_questions() -> list[dict]:
    base = [
        ("Symbol of water is?", ["O2", "H2O", "CO2", "NaCl"], 1),
        ("pH less than 7 means?", ["Acid", "Base", "Neutral", "Salt"], 0),
        ("Common salt chemical formula is?", ["NaCl", "H2SO4", "KOH", "CaCO3"], 0),
        ("Which is a gas?", ["Iron", "Oxygen", "Wood", "Glass"], 1),
        ("Which one is an acid?", ["HCl", "NaOH", "KOH", "Ca(OH)2"], 0),
        ("What is the symbol for gold?", ["Ag", "Gd", "Au", "Go"], 2),
        ("What is the symbol for sodium?", ["So", "Na", "S", "N"], 1),
        ("What is the symbol for oxygen?", ["Ox", "Og", "O", "Oy"], 2),
        ("Which particle has negative charge?", ["Proton", "Neutron", "Electron", "Nucleus"], 2),
        ("Which particle has no charge?", ["Proton", "Neutron", "Electron", "Ion"], 1),
        ("What is CO2 called?", ["Carbon monoxide", "Carbon dioxide", "Calcium oxide", "Copper oxide"], 1),
        ("Which is a base?", ["HCl", "HNO3", "NaOH", "H2SO4"], 2),
        ("What is the center of an atom called?", ["Shell", "Electron", "Nucleus", "Orbit"], 2),
        ("Which state of matter has fixed shape?", ["Gas", "Liquid", "Solid", "Plasma"], 2),
        ("Which metal is liquid at room temperature?", ["Mercury", "Iron", "Aluminum", "Copper"], 0),
        ("What is the chemical symbol for iron?", ["Ir", "Fe", "In", "I"], 1),
        ("Which gas is used in balloons?", ["Oxygen", "Nitrogen", "Helium", "Hydrogen"], 2),
        ("What do we call a substance made from one type of atom?", ["Compound", "Mixture", "Element", "Solution"], 2),
        ("Which is an example of a mixture?", ["Water", "Oxygen", "Air", "Gold"], 2),
        ("What is the formula of methane?", ["CH4", "CO2", "H2O", "NH3"], 0),
    ]
    questions = []
    for i in range(5):
        for q in base:
            questions.append(make_question(q[0], q[1], q[2]))
    return questions[:100]


QUESTION_BANK = {
    "english": generate_english_questions(),
    "gk": generate_gk_questions(),
    "science": generate_science_questions(),
    "math": generate_math_questions(),
    "physics": generate_physics_questions(),
    "chemistry": generate_chemistry_questions(),
}

SUBJECT_LABELS = {
    "english": "📘 English",
    "gk": "🌍 GK",
    "science": "🧪 Science",
    "math": "➗ Math",
    "physics": "⚛️ Physics",
    "chemistry": "⚗️ Chemistry",
}

SUBJECT_TEXT_TO_KEY = {
    "📘 English": "english",
    "🌍 GK": "gk",
    "🧪 Science": "science",
    "➗ Math": "math",
    "⚛️ Physics": "physics",
    "⚗️ Chemistry": "chemistry",
}


# ---------------- KEYBOARDS ----------------
def subject_reply_keyboard():
    keyboard = [
        ["📘 English", "🌍 GK"],
        ["🧪 Science", "➗ Math"],
        ["⚛️ Physics", "⚗️ Chemistry"],
        ["🔄 Restart", "❌ Hide Keyboard"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Choose a subject...",
                            ) 

def answer_inline_keyboard(options):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"A. {options[0]}", callback_data="answer:0")],
        [InlineKeyboardButton(f"B. {options[1]}", callback_data="answer:1")],
        [InlineKeyboardButton(f"C. {options[2]}", callback_data="answer:2")],
        [InlineKeyboardButton(f"D. {options[3]}", callback_data="answer:3")],
    ])


def next_inline_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Next", callback_data="next")]
    ])


def result_inline_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔁 Restart Quiz", callback_data="restart_quiz"),
            InlineKeyboardButton("🏠 Subjects", callback_data="show_subjects"),
        ]
    ])


# ---------------- SESSION ----------------
def reset_session(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["subject"] = None
    context.user_data["questions"] = []
    context.user_data["index"] = 0
    context.user_data["score"] = 0


def start_subject_quiz(context: ContextTypes.DEFAULT_TYPE, subject: str):
    questions = QUESTION_BANK.get(subject, [])[:]
    random.shuffle(questions)

    context.user_data["subject"] = subject
    context.user_data["questions"] = questions
    context.user_data["index"] = 0
    context.user_data["score"] = 0


async def send_current_question_to_message(message_target, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data.get("questions", [])
    index = context.user_data.get("index", 0)
    score = context.user_data.get("score", 0)
    subject = context.user_data.get("subject")

    if not questions:
        await message_target.reply_text(
            "❌ Questions မရှိသေးပါ။ Subject ကိုပြန်ရွေးပါ။",
            reply_markup=subject_reply_keyboard(),
        )
        return

    if index >= len(questions):
        await message_target.reply_text(
            (
                "🎉 Quiz Finished!\n\n"
                f"📘 Subject: {SUBJECT_LABELS.get(subject, subject)}\n"
                f"✅ Score: {score}/{len(questions)}"
            ),
            reply_markup=result_inline_keyboard(),
        )
        return

    q = questions[index]
    await message_target.reply_text(
        text=(
            f"{SUBJECT_LABELS.get(subject, subject)}\n"
            f"❓ Question {index + 1}/{len(questions)}\n"
            f"🏆 Score: {score}\n\n"
            f"{q['q']}"
        ),
        reply_markup=answer_inline_keyboard(q["o"]),
    )


async def edit_current_question(query, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data.get("questions", [])
    index = context.user_data.get("index", 0)
    score = context.user_data.get("score", 0)
    subject = context.user_data.get("subject")

    if not questions:
        await query.edit_message_text("❌ Questions မရှိသေးပါ။")
        return

    if index >= len(questions):
        await query.edit_message_text(
            (
                "🎉 Quiz Finished!\n\n"
                f"📘 Subject: {SUBJECT_LABELS.get(subject, subject)}\n"
                f"✅ Score: {score}/{len(questions)}"
            ),
            reply_markup=result_inline_keyboard(),
        )
        return

    q = questions[index]
    await query.edit_message_text(
        text=(
            f"{SUBJECT_LABELS.get(subject, subject)}\n"
            f"❓ Question {index + 1}/{len(questions)}\n"
            f"🏆 Score: {score}\n\n"
            f"{q['q']}"
        ),
        reply_markup=answer_inline_keyboard(q["o"]),
    )


# ---------------- HANDLERS ----------------
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
    await update.message.reply_text(
        text,
        reply_markup=subject_reply_keyboard(),
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if text == "🔄 Restart":
        reset_session(context)
        await update.message.reply_text(
            "🔄 Restart complete.\n\nSubject ကိုပြန်ရွေးပါ။",
            reply_markup=subject_reply_keyboard(),
        )
        return

    if text == "❌ Hide Keyboard":
        await update.message.reply_text(
            "Keyboard ကိုဖျောက်လိုက်ပါပြီ။ /start နဲ့ပြန်ဖွင့်နိုင်ပါတယ်။",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    subject = SUBJECT_TEXT_TO_KEY.get(text)
    if not subject:
        await update.message.reply_text(
            "အောက်က subject buttons တွေထဲက တစ်ခုရွေးပါ။",
            reply_markup=subject_reply_keyboard(),
        )
        return

    start_subject_quiz(context, subject)
    await send_current_question_to_message(update.message, context)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("answer:"):
        selected = int(data.split(":", 1)[1])
        index = context.user_data.get("index", 0)
        questions = context.user_data.get("questions", [])

        if not questions or index >= len(questions):
            await query.edit_message_text("❌ Quiz data not found. /start နဲ့ပြန်စပါ။")
            return

        current = questions[index]
        correct = current["a"]

        if selected == correct:
            context.user_data["score"] = context.user_data.get("score", 0) + 1
            text = "✅ Correct!"
        else:
            text = f"❌ Wrong!\nCorrect answer: {current['o'][correct]}"

        context.user_data["index"] = index + 1

        await query.edit_message_text(
            text=text,
            reply_markup=next_inline_keyboard(),
        )
        return

    if data == "next":
        await edit_current_question(query, context)
        return

    if data == "restart_quiz":
        subject = context.user_data.get("subject")
        if not subject:
            await query.edit_message_text("❌ Subject မတွေ့ပါ။ /start နဲ့ပြန်စပါ။")
            return

        start_subject_quiz(context, subject)
        await edit_current_question(query, context)
        return

    if data == "show_subjects":
        reset_session(context)
        await query.message.reply_text(
            "📚 Subject ကိုရွေးပါ။",
            reply_markup=subject_reply_keyboard(),
        )
        try:
            await query.delete_message()
        except Exception:
            pass
        return


def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Starting Quiz Bot...")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
