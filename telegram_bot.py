# telegram_financial_bot.py
import logging
import os
from dotenv import load_dotenv
import whisper
from pydub import AudioSegment
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import financial_core  # your financial logic


# --- Load environment variables ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Load Whisper model ---
MODEL_SIZE = "large"  # "tiny", "base", "small", "medium", "large"
print(f"Loading Whisper model '{MODEL_SIZE}'...")
model = whisper.load_model(MODEL_SIZE)
print("Whisper model loaded")


# --- Keyboard ---
main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💵 قیمت دلار"), KeyboardButton("🪙 قیمت طلا")],
        [KeyboardButton("📈 بورس"), KeyboardButton("📊 ارز دیجیتال")],
        [KeyboardButton("ℹ️ راهنما")],
    ],
    resize_keyboard=True,
)


# --- Helper function ---
def get_custom_response(text: str) -> dict:
    """Send text to financial module and return response."""
    try:
        return financial_core.process_request(text)
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {"type": "text", "text": "❌ خطا در پردازش درخواست."}


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"سلام {user.mention_html()}! 👋\nمن دستیار مالی شما هستم. متن یا ویس بفرستید.",
        reply_markup=main_keyboard
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📌 <b>راهنمای استفاده از ربات:</b>\n"
        "می‌توانید یکی از گزینه‌ها را انتخاب کنید یا متن بفرستید:\n"
        "💵 قیمت دلار\n🪙 قیمت طلا\n📈 بورس\n📊 ارز دیجیتال\n\n"
        "مثلاً تایپ کنید: <code>قیمت یورو</code>"
    )
    await update.message.reply_html(help_text, reply_markup=main_keyboard)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe Persian voice messages and respond."""
    user_message = update.message
    await user_message.reply_text("پیام صوتی دریافت شد، در حال پردازش...")

    try:
        # Download voice file (.oga)
        voice_file = await user_message.voice.get_file()
        oga_path = f"{voice_file.file_id}.oga"
        await voice_file.download_to_drive(oga_path)

        # Convert .oga to .wav
        wav_path = f"{voice_file.file_id}.wav"
        audio = AudioSegment.from_file(oga_path, format="ogg")
        audio.export(wav_path, format="wav")

        financial_prompt = (
            "گزارش امروز بورس و قیمت ارز. قیمت دلار، یورو، درهم و پوند چند است؟ "
            "وضعیت طلا، سکه امامی، سکه بهار آزادی، ربع سکه و نیم سکه در هفته گذشته چطور بود؟ "
            "لطفاً وضعیت شاخص کل، شاخص هم وزن و شاخص فرابورس را بررسی کنید. "
            "تحلیل تکنیکال نمادهای شستا، خودرو، خساپا، فولاد، شپنا، وبملت، وتجارت و وغدیر. "
            "اخبار سهام اپل، مایکروسافت، و تسلا. "
            "قیمت بیت کوین، اتریوم و تتر در بیست و چهار ساعت گذشته. "
            "آیا دیروز ده درصد یا پنجاه درصد رشد یا افت داشتیم؟"
            "گزارش امروز بورس و قیمت ارز. قیمت دلار، یورو و سکه بهار آزادی امروز چند است؟ "
            "لطفاً نمودار شاخص کل را در پنج روز گذشته، هفته گذشته و ماه گذشته برایم نشان بده. "
            "لطفاً چارت شاخص کل را در پنج روز گذشته، هفته گذشته و ماه گذشته و سال گذشته برایم نشان بده. "
            "تحلیل تکنیکال نمادهای شستا و خودرو. "
            "اخبار سهام اپل و مایکروسافت. "
            "قیمت بیت کوین و اتریوم در بیست و چهار ساعت گذشته چطور بود؟"
        )
        
        # Transcribe with Whisper
        result = model.transcribe(wav_path, language="fa", fp16=False,initial_prompt=financial_prompt)
        transcribed_text = result["text"]
        logger.info(f"Transcribed text: {transcribed_text}")

        # Get financial response
        response = get_custom_response(transcribed_text)

        if response["type"] == "text":
            await update.message.reply_text(response["text"], reply_markup=main_keyboard)
        elif response["type"] == "image":
            await update.message.reply_photo(
                photo=response["image"],
                caption=response.get("caption", ""),
                reply_markup=main_keyboard
            )
        else:
            await update.message.reply_text("❌ پاسخ نامعتبر دریافت شد.")

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await user_message.reply_text("❌ خطا در پردازش پیام صوتی.")

    finally:
        # Cleanup
        if os.path.exists(oga_path):
            os.remove(oga_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_message = update.message.text.strip()
    logger.info(f"User {update.effective_user.id} sent: {user_message}")

    if user_message in ["راهنما", "help", "/help", "ℹ️ راهنما"]:
        await help_command(update, context)
        return

    response = get_custom_response(user_message)

    if response["type"] == "text":
        await update.message.reply_text(response["text"], reply_markup=main_keyboard)
    elif response["type"] == "image":
        await update.message.reply_photo(
            photo=response["image"],
            caption=response.get("caption", ""),
            reply_markup=main_keyboard
        )
    else:
        await update.message.reply_text("❌ پاسخ نامعتبر دریافت شد.")


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("ربات در حال خاموش شدن است. 👋")
    context.application.stop()


# --- Main ---
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("exit", exit_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("🤖 Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
