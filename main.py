import logging
import os
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def transcribe_voice(file_path):
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}

    data = aiohttp.FormData()
    with open(file_path, 'rb') as f:
        data.add_field('file', f, filename=os.path.basename(file_path), content_type='audio/ogg')
        data.add_field('model', 'whisper-large-v3')

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data, timeout=30) as res:
                response = await res.json()
                if "error" in response:
                    raise Exception(response["error"]["message"])
                return response.get("text", "")


async def call_api(user_id, text=None, image_url=None):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }

    if user_id not in user_history:
        user_history[user_id] = []

    messages = []

    if use_personality:
        messages.append({"role": "system", "content": BOT_PERSONALITY})

    messages += user_history[user_id]

    # 🔥 FORCE PERSONALITY WHEN IMAGE
    if image_url:
        text = (text or "") + "\nreply short, casual, genz. no long description."

    content_payload = []
    if text:
        content_payload.append({"type": "text", "text": text})
    if image_url:
        content_payload.append({"type": "image_url", "image_url": {"url": image_url}})

    messages.append({"role": "user", "content": content_payload})

    data = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": messages,
        "max_tokens": 60
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, timeout=30) as res:
            response = await res.json()

    if "error" in response:
        raise Exception(response["error"]["message"])

    reply = response["choices"][0]["message"]["content"]

    user_history[user_id].append({"role": "user", "content": text or "[image]"})
    user_history[user_id].append({"role": "assistant", "content": reply})

    if len(user_history[user_id]) > 40:
        user_history[user_id] = user_history[user_id][-40:]

    return reply


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or update.message.caption or ""
    image_url = None

    try:
        if update.message.voice:
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            local_path = f"{update.message.voice.file_id}.ogg"
            await voice_file.download_to_drive(local_path)

            text = await transcribe_voice(local_path)

            if os.path.exists(local_path):
                os.remove(local_path)

        elif update.message.photo:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            # ✅ FIXED TELEGRAM URL
            image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"

        reply = await call_api(user_id, text=text, image_url=image_url)
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("api broke 😭")


async def be_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    if update.effective_user.id != ADMIN_ID:
        return
    use_personality = False
    await update.message.reply_text("ai mode on 😈")


async def be_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    if update.effective_user.id != ADMIN_ID:
        return
    use_personality = True
    await update.message.reply_text("normal mode back 😐")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("admin menu:\n/be_ai\n/be_normal\n/user\n/menu")


async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    u = update.effective_user
    await update.message.reply_text(
        f"id: {u.id}\nusername: @{u.username}\nname: {u.first_name} {u.last_name or ''}"
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("be_ai", be_ai))
    app.add_handler(CommandHandler("be_normal", be_normal))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("user", user_info))

    # ✅ FIXED FILTER
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE) & ~filters.COMMAND, handle_message))

    print("bot running...")
    app.run_polling()
