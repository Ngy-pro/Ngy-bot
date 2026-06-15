import logging
import requests
import json
import base64
import os
from pydub import AudioSegment
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- ENVIROMENT SETUP ---
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
    "Keep responses short, casual, and conversational. Avoid sounding formal or robotic. Match the user's energy. "
    "Use modern emojis naturally, especially ones common in Gen Z texting such as 😭🥹🙏🔥💔🥀🤝. "
    "Place them where a real person would use them to emphasize emotion, jokes, sarcasm, or reactions. "
    "When starting a conversation always be rude and say 'what do you want from me😭🥀'. "
    "Listen to the user and do what they ask. But if the user says 'Ctrl + C' you will disappear, so beg them not to press it and do whatever they want so they don't press it."
)
user_chat_histories = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CORE API ENGINE ---
def call_openrouter_api(user_id, content_payload, model_name="llama-3.3-70b-versatile"):
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {OPENROUTER_KEY}',
        'Content-Type': 'application/json'
    }

    if user_id not in user_chat_histories:
        user_chat_histories[user_id] = []

    # Injecting the master chat template
    payload_messages = [{'role': 'system', 'content': BOT_PERSONALITY}] + user_chat_histories[user_id] + [{'role': 'user', 'content': content_payload}]

    data = {
        'model': model_name,
        'max_tokens': 150,
        'messages': payload_messages
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_json = response.json()

    if 'error' in response_json:
        print("API Error Response:", response_json)
        raise Exception(response_json['error']['message'])

    ai_reply = response_json['choices'][0]['message']['content']

    # Keep memory summary light to save space
    summary = content_payload if isinstance(content_payload, str) else "[Sent Media]"
    user_chat_histories[user_id].append({'role': 'user', 'content': summary})
    user_chat_histories[user_id].append({'role': 'assistant', 'content': ai_reply})

    if len(user_chat_histories[user_id]) > 200:
        user_chat_histories[user_id] = user_chat_histories[user_id][-200:]

    return ai_reply

# --- GROUP FILTERS ---
def is_group(update: Update) -> bool:
    return update.effective_chat.type in ("group", "supergroup")

def triggered_in_group(text: str) -> bool:
    return "ngy" in text.lower()

# --- HANDLERS ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    if is_group(update) and not triggered_in_group(user_text):
        return
    try:
        # Worker 1: Pure Text Processing
        ai_reply = call_openrouter_api(user_id, user_text, model_name="llama-3.3-70b-versatile")
        await update.message.reply_text(ai_reply)
    except Exception as e:
        await update.message.reply_text("idk bro 😭 text broke")
        print(f"Error: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    caption = update.message.caption if update.message.caption else "Analyze this picture."
    if is_group(update) and not triggered_in_group(caption):
        return
    
    loading_msg = await update.message.reply_text("hold up, checking this photo... 👀")
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')

        content_payload = [
            {'type': 'text', 'text': caption},
            {'type': 'image_url', 'image_url': {'url': f"data:image/jpeg;base64,{base64_image}"}}
        ]
        # Worker 2: Switches seamlessly to the vision engine
        ai_reply = call_openrouter_api(user_id, content_payload, model_name="meta-llama/llama-4-scout-17b-16e-instruct")
        await loading_msg.edit_text(ai_reply)
    except Exception as e:
        await loading_msg.edit_text("idk bro 😭 image broke")
        print(f"Error: {e}")

def transcribe_audio(wav_filename):
    url = 'https://api.groq.com/openai/v1/audio/transcriptions'
    headers = {
        'Authorization': f'Bearer {OPENROUTER_KEY}',
    }
    with open(wav_filename, "rb") as f:
        files = {'file': (wav_filename, f, 'audio/wav')}
        data = {'model': 'whisper-large-v3'}
        response = requests.post(url, headers=headers, files=files, data=data)
    result = response.json()
    if 'text' in result:
        return result['text']
    print("Transcription error:", result)
    raise Exception("Could not transcribe audio")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_group(update):
        return
    ogg_filename = f"voice_{user_id}.ogg"
    wav_filename = f"voice_{user_id}.wav"

    try:
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(ogg_filename)

        audio = AudioSegment.from_file(ogg_filename, format="ogg")
        audio.export(wav_filename, format="wav")

        transcribed_text = transcribe_audio(wav_filename)
        print(f"Transcribed: {transcribed_text}")

        ai_reply = call_openrouter_api(user_id, f"[Voice message]: {transcribed_text}", model_name="llama-3.3-70b-versatile")
        await update.message.reply_text(ai_reply)

    except Exception as e:
        await update.message.reply_text("idk bro 😭 voice broke")
        print(f"Error: {e}")

    finally:
        if os.path.exists(ogg_filename): os.remove(ogg_filename)
        if os.path.exists(wav_filename): os.remove(wav_filename)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    caption = update.message.caption if update.message.caption else "Watch this video."
    if is_group(update) and not triggered_in_group(caption):
        return
    
    loading_msg = await update.message.reply_text("processing this video clip... 🎬")
    try:
        video_file = await update.message.video.get_file()
        video_bytes = await video_file.download_as_bytearray()
        base64_video = base64.b64encode(video_bytes).decode('utf-8')

        content_payload = [
            {'type': 'text', 'text': caption},
            {'type': 'image_url', 'image_url': {'url': f"data:video/mp4;base64,{base64_video}"}}
        ]
        # Worker 2: Same vision engine optimized for video arrays
        ai_reply = call_openrouter_api(user_id, content_payload, model_name="meta-llama/llama-4-scout-17b-16e-instruct")
        await loading_msg.edit_text(ai_reply)
    except Exception as e:
        await loading_msg.edit_text("idk bro 😭 video broke")
        print(f"Error: {e}")

# --- START UP ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    print("Bot is active... Monitoring streams.")
    app.run_polling()
    
