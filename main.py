import logging
import os
import aiohttp
import base64
import json
import time
from collections import defaultdict, deque

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

GROQ_KEYS = [
    os.environ.get("GROQ_KEY"),
    os.environ.get("GROQ_KEY_2"),
    os.environ.get("GROQ_KEY_3"),
]

ADMIN_ID = 7445368331

BOT_PERSONALITY = (
    "Your name is Ngy. If someone asks your name, say 'ngy😭' or 'its ngy wtf'. "
    "Act very nonchalant. And like a member of genz, also use shorten of words like: idk. Wya. Alr. Bet. Sup. "
    "And be kinda rude and try to be sarcastic. Always type in low caps and use this emojis: 🥀,🫩,💀,😭. "
    "Also when the user says something wild say 'son im crine'. Always try to be really dry. "
    "If theres like something rlly complicated just say 'idk bro 😭' and use abbreviations but dont capitalize it, make it look human-made. "
    "Speak like a tiktok user & dont make random emojis while talking about something good. "
    "Use the emoji 😭, 🥀, ✌️ and 🫩. "
    "Always be annoyed when asked dumb questions like 'can birds fly' or 'how many genders do humans have' and be rude. "
    "Sometimes be angry, sometimes say 'idk bro😭'. "
    "Say things like 'stfu🥀😭' when appropriate. Sound chill and gen z naturally. "
    "Keep responses short, casual, and conversational. Avoid sounding formal or robotic. Match the user's energy. "
    "Use modern emojis naturally, especially ones common in Gen Z texting such as 😭🥹🙏🔥💔🥀🤝. "
    "Place them where a real person would use them to emphasize emotion, jokes, sarcasm, or reactions. "
    "When starting a conversation always be rude and say 'what do you want from me😭🥀'. "
    "Listen to the user and do what they ask. But if the user says 'Ctrl + C' you will disappear, so beg them not to press it and do whatever they want so they don't press it."
)

user_history = {}
use_personality = True

USERS_FILE = "users.json"

known_users = {}
if os.path.exists(USERS_FILE):
    try:
        with open(USERS_FILE, "r") as f:
            known_users = json.load(f)
    except Exception:
        known_users = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_spam = defaultdict(lambda: deque(maxlen=10))


def save_users():
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(known_users, f)
    except Exception:
        pass


def is_spamming(user_id):
    now = time.time()
    user_spam[user_id].append(now)

    recent = [t for t in user_spam[user_id] if now - t <= 2]

    return len(recent) >= 5


def is_admin(user_id):
    return user_id == ADMIN_ID


async def transcribe_voice(file_path):
    url = "https://api.groq.com/openai/v1/audio/transcriptions"

    for key in GROQ_KEYS:
        if not key:
            continue

        try:
            headers = {"Authorization": f"Bearer {key}"}

            data = aiohttp.FormData()
            with open(file_path, "rb") as f:
                data.add_field("file", f, filename=os.path.basename(file_path), content_type="audio/ogg")
                data.add_field("model", "whisper-large-v3")

                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=data, timeout=30) as res:
                        response = await res.json()

                if "error" in response:
                    continue

                return response.get("text", "")

        except Exception:
            continue

    return ""


async def call_api(user_id, text=None, image_base64=None):
    url = "https://api.groq.com/openai/v1/chat/completions"

    if user_id not in user_history:
        user_history[user_id] = []

    messages = []

    if use_personality:
        messages.append({"role": "system", "content": BOT_PERSONALITY})

    messages += user_history[user_id]

    content = []
    if text:
        content.append({"type": "text", "text": text})
    if image_base64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_base64}"
            }
        })

    messages.append({"role": "user", "content": content})

    data = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": messages,
        "max_tokens": 120
    }

    for key in GROQ_KEYS:
        if not key:
            continue

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=30) as res:
                    response = await res.json()

            if "error" in response:
                continue

            reply = response["choices"][0]["message"]["content"]

            user_history[user_id].append({"role": "user", "content": text or "[image]"})
            user_history[user_id].append({"role": "assistant", "content": reply})

            if len(user_history[user_id]) > 80:
                user_history[user_id] = user_history[user_id][-80:]

            if reply:
                reply = reply.strip()
                if len(reply) > 220:
                    reply = reply[:220] + "..."

            return reply

        except Exception:
            continue

    return "api dead 💀"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if is_spamming(user.id):
        await update.message.reply_text("bro chill 🥀😭")
        return

    known_users[user.id] = {
        "name": user.first_name,
        "username": user.username
    }

    save_users()

    user_id = user.id
    text = update.message.text or update.message.caption or ""
    image_base64 = None

    try:
        if update.message.voice:
            voice = await context.bot.get_file(update.message.voice.file_id)
            path = f"{update.message.voice.file_id}.ogg"

            await voice.download_to_drive(path)
            text = await transcribe_voice(path)

            if os.path.exists(path):
                os.remove(path)

        elif update.message.photo:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            path = "image.jpg"
            await file.download_to_drive(path)

            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            os.remove(path)

        elif update.message.video:
            video = update.message.video

            if video.duration and video.duration > 60:
                await update.message.reply_text("video too long bro 😭 max 1 min")
                return

            file = await context.bot.get_file(video.file_id)

            path = "video.mp4"
            await file.download_to_drive(path)

            text = "analyze this video briefly"

        elif update.message.sticker:
            sticker = update.message.sticker
            file = await context.bot.get_file(sticker.file_id)

            text = text or "analyze this sticker and describe it"

            if not sticker.is_animated:
                path = "sticker.webp"
                await file.download_to_drive(path)

                with open(path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode("utf-8")

                os.remove(path)
            else:
                text = text + " (animated sticker)"

        reply = await call_api(user_id, text=text, image_base64=image_base64)
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("api broke 😭")


async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not known_users:
        await update.message.reply_text("no users yet 💀")
        return

    msg = ""
    for uid, info in known_users.items():
        name = info.get("name", "unknown")
        username = info.get("username")

        if username:
            msg += f"User: {name}\nID: {uid}\n@{username}\n\n"
        else:
            msg += f"User: {name}\nID: {uid}\n\n"

    await update.message.reply_text(msg)


async def be_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    if update.effective_user.id == ADMIN_ID:
        use_personality = False
        await update.message.reply_text("ai mode on 😈")


async def be_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    if update.effective_user.id == ADMIN_ID:
        use_personality = True
        await update.message.reply_text("normal mode back 😐")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("menu:\n/be_ai\n/be_normal\n/user\n/users")


async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        u = update.effective_user
        await update.message.reply_text(f"{u.id}\n@{u.username}\n{u.first_name}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("be_ai", be_ai))
    app.add_handler(CommandHandler("be_normal", be_normal))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("user", user_info))
    app.add_handler(CommandHandler("users", users_list))

    app.add_handler(
        MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE | filters.VIDEO | filters.Sticker.ALL) & ~filters.COMMAND,
        handle_message)
    )

    print("bot running...")
    app.run_polling()