import logging
import json
import base64
import os
import time
import aiohttp
from pydub import AudioSegment
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]

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
    "Keep responses short, casual, and conversational. Avoid sounding formal or robotic. "
    "Use modern emojis naturally like 😭🥹🙏🔥💔🥀🤝. "
    "When starting a conversation say 'what do you want from me😭🥀'. "
    "Listen to the user and do what they ask. If user says 'Ctrl + C' act like you will disappear."
)

user_chat_histories = {}
last_used = {}

logging.basicConfig(level=logging.INFO)

async def call_api(user_id, content, model="llama-3.3-70b-versatile"):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }

    if user_id not in user_chat_histories:
        user_chat_histories[user_id] = []

    messages = (
        [{"role": "system", "content": BOT_PERSONALITY}] +
        user_chat_histories[user_id] +
        [{"role": "user", "content": content}]
    )

    data = {
        "model": model,
        "messages": messages,
        "max_tokens": 150
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as res:
            response = await res.json()

    if "error" in response:
        raise Exception(response["error"]["message"])

    reply = response["choices"][0]["message"]["content"]

    summary = content if isinstance(content, str) else "[media]"
    user_chat_histories[user_id].append({"role": "user", "content": summary})
    user_chat_histories[user_id].append({"role": "assistant", "content": reply})

    if len(user_chat_histories[user_id]) > 100:
        user_chat_histories[user_id] = user_chat_histories[user_id][-100:]

    return reply

def can_use(user_id):
    now = time.time()
    if user_id in last_used and now - last_used[user_id] < 2:
        return False
    last_used[user_id] = now
    return True

def is_group(update: Update):
    return update.effective_chat.type in ("group", "supergroup")

def triggered(text: str):
    return "ngy" in text.lower()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if is_group(update) and not triggered(text):
        return

    if not can_use(user_id):
        await update.message.reply_text("bro chill 😭")
        return

    try:
        reply = await call_api(user_id, text)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("api broke 😭")
        print(e)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    caption = update.message.caption or "analyze this"

    if is_group(update) and not triggered(caption):
        return

    if not can_use(user_id):
        await update.message.reply_text("bro chill 😭")
        return

    msg = await update.message.reply_text("checking 👀")

    try:
        file = await update.message.photo[-1].get_file()
        data = await file.download_as_bytearray()
        b64 = base64.b64encode(data).decode()

        payload = [
            {"type": "text", "text": caption},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]

        reply = await call_api(user_id, payload, "meta-llama/llama-4-scout-17b-16e-instruct")
        await msg.edit_text(reply)

    except Exception:
        await msg.edit_text("image broke 😭")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not can_use(user_id):
        await update.message.reply_text("bro chill 😭")
        return

    ogg = f"{user_id}.ogg"
    wav = f"{user_id}.wav"

    msg = await update.message.reply_text("listening 🎧")

    try:
        file = await update.message.voice.get_file()
        await file.download_to_drive(ogg)

        audio = AudioSegment.from_file(ogg, format="ogg")
        audio.export(wav, format="wav")

        async with aiohttp.ClientSession() as session:
            with open(wav, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("file", f, filename=wav)
                form.add_field("model", "whisper-large-v3")

                async with session.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    data=form
                ) as res:
                    result = await res.json()

        text = result.get("text", "")
        reply = await call_api(user_id, text)

        await msg.edit_text(reply)

    except Exception:
        await msg.edit_text("voice broke 😭")

    finally:
        if os.path.exists(ogg):
            os.remove(ogg)
        if os.path.exists(wav):
            os.remove(wav)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("video not supported 😭")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    print("bot running...")
    app.run_polling()
