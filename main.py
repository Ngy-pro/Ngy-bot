import logging
import json
import base64
import os
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]

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
    "Use modern emojis naturally, especially such as 😭🥹🙏🔥💔🥀🤝. "
    "Place them where a real person would use them. "
    "When starting a conversation always be rude and say 'what do you want from me😭🥀'. "
    "Listen to the user and do what they ask. But if the user says 'Ctrl + C' you will disappear, so beg them not to press it."
)

user_chat_history = {}
use_personality = True

logging.basicConfig(level=logging.INFO)


def is_admin(user_id):
    return user_id == ADMIN_ID


async def call_api(user_id, content, model="llama-3.3-70b-versatile"):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }

    if user_id not in user_chat_history:
        user_chat_history[user_id] = []

    messages = []

    if use_personality:
        messages.append({"role": "system", "content": BOT_PERSONALITY})

    messages += user_chat_history[user_id]
    messages.append({"role": "user", "content": str(content)})

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

    user_chat_history[user_id].append({"role": "user", "content": str(content)})
    user_chat_history[user_id].append({"role": "assistant", "content": reply})

    if len(user_chat_history[user_id]) > 100:
        user_chat_history[user_id] = user_chat_history[user_id][-100:]

    return reply


async def be_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    if not is_admin(update.effective_user.id):
        return
    use_personality = False
    await update.message.reply_text("ai mode on 😈")


async def be_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_personality
    if not is_admin(update.effective_user.id):
        return
    use_personality = True
    await update.message.reply_text("normal mode back 😐")


async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    u = update.effective_user
    await update.message.reply_text(
        f"id: {u.id}\n"
        f"username: @{u.username}\n"
        f"name: {u.first_name} {u.last_name or ''}"
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "admin menu:\n"
        "/be_ai\n"
        "/be_normal\n"
        "/user\n"
        "/menu"
    )


def is_group(update: Update):
    return update.effective_chat.type in ("group", "supergroup")


def triggered(text: str):
    return "ngy" in text.lower()


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if is_group(update) and not triggered(text):
        return

    try:
        reply = await call_api(user_id, text)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("api broke 😭")
        print(e)


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("be_ai", be_ai))
    app.add_handler(CommandHandler("be_normal", be_normal))
    app.add_handler(CommandHandler("user", user_info))
    app.add_handler(CommandHandler("menu", menu))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("bot running...")
    app.run_polling()
