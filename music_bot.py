import os
import subprocess
import yt_dlp
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# 🔑 ВСТАВ СЮДИ СВІЙ ТОКЕН ВІД @BotFather
BOT_TOKEN = "8288730710:AAHRechqr_KEKL0rTLFrSL7eDnC_55nkjyY"

# 📦 Максимальний розмір файлу (Telegram ліміт 50МБ)
MAX_FILE_SIZE_MB = 45
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# 📂 Папка для завантажень
DOWNLOADS_DIR = "downloads"


# ======== Команди ========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎧 Привіт! Надішли мені посилання на YouTube — я зроблю MP3 і надішлю тобі!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💡 Просто відправ мені YouTube-посилання, і я згенерую MP3.")


# ======== Основна логіка ========

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Створюємо теку для завантажень
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

        # 🔊 Конвертація у MP3
        subprocess.run([
            "ffmpeg", "-y", "-i", filename,
            "-vn", "-ab", "128k", "-ar", "44100", "-f", "mp3", mp3_filename
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 🧩 Перевірка розміру
        size = os.path.getsize(mp3_filename)
        if size > MAX_FILE_SIZE:
            await update.message.reply_text("⚙️ Файл великий — стискаю до меншого розміру...")
            smaller = os.path.splitext(mp3_filename)[0] + "_small.mp3"

            # адаптивне стиснення — пробуємо 96kbps, потім 64kbps
            for bitrate in ["96k", "64k"]:
                subprocess.run([
                    "ffmpeg", "-y", "-i", mp3_filename, "-b:a", bitrate, smaller
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.getsize(smaller) <= MAX_FILE_SIZE:
                    mp3_filename = smaller
                    break

        # 🔁 Повторна спроба надсилання
        for attempt in range(3):
            try:
                await update.message.reply_audio(
                    audio=open(mp3_filename, 'rb'),
                    title=title,
                    caption=f"🎵 {title}"
                )
                break
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(5)
                else:
                    raise e

    except Exception as e:
        await update.message.reply_text(f"⚠️ Сталася помилка: {e}")

    finally:
        # 🧹 Очищаємо файли
        for f in os.listdir(DOWNLOADS_DIR):
            os.remove(os.path.join(DOWNLOADS_DIR, f))


# ======== Запуск ========

def main():
    print("🚀 Бот запускається...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

    print("✅ Бот працює! Очікує повідомлення...")
    app.run_polling()


if __name__ == "__main__":
    main()
