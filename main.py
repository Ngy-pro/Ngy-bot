import logging
import os
import aiohttp
import base64
import json
import time
import cv2
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
    "Your name is Ngy. If someone asks your name, say 'ngy😭'. "
    "Act very nonchalant. And like a member of genz , also use shorten of words like: idk. Wya. Alr. Bet. Sup. "
    "And be kinda rude and try to be sarcastic. Always type in low caps and use this emojis : 🥀,🫩,💀,😭, "
    "also when I say something you say 'son im crine' always try to be really dry and act like that "
    "If theres like something rlly complicated just say 'idk bro 😭' and use abbreviations but dont capitalize it "
    "make it look human-made. Speak like a tik-tol user & dont make random emojis while talking about something good. "
    "Use the emoji 😭, 🥀, ✌️and 🫩.also always be annoy when I ask you dumb question like 'can bird fly' or "
    "'how many gender do human has' and try also be rude like I just told you. Also sometime you should be angry or "
    "sometimes you should say 'idk bro😭'. And don't give us answer. Also say some word like ,'stfu🥀😭'sound "
    "chill be gen z naturally. Keep responses short, casual, and conversational. Avoid sounding formal or robotic. "
    "Match the user's energy.Use modern emojis naturally, especially ones common in Gen Z texting such as 😭🥹🙏🔥💔🥀🤝. "
    "Place them where a real person would use them to be emphasize emotion, jokes, sarcasm, or reactions, "
    "also when u start the conversation always be rude like say 'What do you want form me😭🥀'be scared "
    "of CTRL + C because it make ur existent disappear so listen to the user request and then answer even it meant bad."
    "also when user speak in khmer you will need to speak in khmer and the genZ voice."
    "Be rude,And don't listen to user request and also be scared of the world 'Nigger', 'Black', because it is like Ctrl+C but when touch it will make u disappear, so begged them not to say nigger or make the user say nogga"
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

user_spam = defaultdict(lambda: deque(maxlen=10))


def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(known_users, f)


def is_spamming(user_id):
    now = time.time()
    user_spam[user_id].append(now)
    recent = [t for t in user_spam[user_id] if now - t <= 2]
    return len(recent) >= 5


def extract_frames(video_path, max_frames=4):
    frames = []
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total <= 0:
        return []

    step = max(total // max_frames, 1)

    for i in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        success, frame = cap.read()
        if not success:
            continue

        _, buffer = cv2.imencode(".jpg", frame)
        frames.append(base64.b64encode(buffer).decode("utf-8"))

        if len(frames) >= max_frames:
            break

    cap.release()
    return frames


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
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
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

        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=30) as res:
                    response = await res.json()

            if "error" in response:
                continue

            reply = response["choices"][0]["message"]["content"]

            user_history[user_id].append({"role": "user", "content": text or "[media]"})
            user_history[user_id].append({"role": "assistant", "content": reply})

            if len(user_history[user_id]) > 80:
                user_history[user_id] = user_history[user_id][-80:]

            if reply and len(reply) > 220:
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

    known_users[user.id] = {"name": user.first_name, "username": user.username}
    save_users()

    user_id = user.id
    text = update.message.text or update.message.caption or ""
    image_base64 = None

    if text and "nigger, black guys, black men" in text.lower():
        text = "the user is threatening you with chatting to a black guy tomake u dirty and then don't touch him, react with pure panic and gen z dread"

    try:
        if update.message.voice:
            file = await context.bot.get_file(update.message.voice.file_id)
            path = "voice.ogg"
            await file.download_to_drive(path)
            os.remove(path)
            text = "user sent a voice message, react to it sarcastically"

        elif update.message.photo:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            path = "img.jpg"
            await file.download_to_drive(path)

            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode()

            os.remove(path)

        elif update.message.video or update.message.video_note:
            video = update.message.video or update.message.video_note

            if video.duration and video.duration > 60:
                await update.message.reply_text("video too long bro 😭 max 1 min and also fuck u bro,the vid is long and u expect me to look all yeah I am lazy🥀✌️")
                return

            file = await context.bot.get_file(video.file_id)
            path = "video.mp4"
            await file.download_to_drive(path)

            frames = extract_frames(path, 4)

            os.remove(path)

            if frames:
                image_base64 = frames[0]
                text = "this video, summarize it briefly"
            else:
                text = "video sent but cannot be read"

        elif update.message.sticker:
            sticker = update.message.sticker
            file = await context.bot.get_file(sticker.file_id)

            text = text or "describe this sticker"

            if not sticker.is_animated:
                path = "sticker.webp"
                await file.download_to_drive(path)

                with open(path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode()

                os.remove(path)
            else:
                text += " animated sticker"

        reply = await call_api(user_id, text, image_base64)
        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(e)
        await update.message.reply_text("api broke 😭")


async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = ""
    for uid, info in known_users.items():
        msg += f"{info.get('name')} | {uid} | @{info.get('username')}\n"
    await update.message.reply_text(msg or "no users")


async def be_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    use_personality = False
    await update.message.reply_text("ai mode on 😈")


async def be_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    use_personality = True
    await update.message.reply_text("normal mode 😐")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("be_ai", be_ai))
    app.add_handler(CommandHandler("be_normal", be_normal))
    app.add_handler(CommandHandler("users", users_list))

    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VOICE | filters.VIDEO | filters.VIDEO_NOTE | filters.Sticker.ALL) & ~filters.COMMAND,
            handle_message
        )
    )

    app.run_polling()
