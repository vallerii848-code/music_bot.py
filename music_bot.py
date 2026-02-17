import os
import subprocess
import yt_dlp
import asyncio

from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# ----------------------------
# 🔑 Токен беремо із Render
BOT_TOKEN = os.getenv("BOT_TOKEN")

# URL webhook
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# ----------------------------
# Flask сервер
app_flask = Flask(__name__)

# Telegram application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# ----------------------------
# Налаштування
MAX_FILE_SIZE_MB = 45
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
DOWNLOADS_DIR = "downloads"

# ============================
# Команди бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎧 Привіт! Надішли мені посилання на YouTube — я зроблю MP3 і надішлю!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💡 Просто відправ мені YouTube-посилання, і я згенерую MP3.")

# ============================
# Основна логіка завантаження
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    await update.message.reply_text("⏬ Завантажую аудіо, зачекай...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{DOWNLOADS_DIR}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
    }

    try:
        # Завантаження
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'music')
            filename = ydl.prepare_filename(info)

        mp3_filename = os.path.splitext(filename)[0] + ".mp3"

        # Конвертація у MP3
        subprocess.run([
            "ffmpeg", "-y", "-i", filename,
            "-vn", "-ab", "128k", "-ar", "44100", "-f", "mp3", mp3_filename
        ])

        # Надсилаємо аудіо
        await update.message.reply_audio(
            audio=open(mp3_filename, 'rb'),
            title=title,
            caption=f"🎵 {title}"
        )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Сталася помилка: {e}")

    finally:
        # Очищаємо завантажені файли
        if os.path.exists(DOWNLOADS_DIR):
            for f in os.listdir(DOWNLOADS_DIR):
                os.remove(os.path.join(DOWNLOADS_DIR, f))

# ============================
# Додаємо хендлери
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

# ============================
# Flask routes
@app_flask.route("/")
def home():
    return "Bot is running"

@app_flask.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.json, application.bot)
    asyncio.run(application.process_update(update))
    return "ok"