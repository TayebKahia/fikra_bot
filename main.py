from flask import Flask, request
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
import pyotp
import os
import re
import time
from dotenv import load_dotenv
from datetime import datetime
import logging

# Load environment variables
load_dotenv()

# Telegram bot token and secret keys
BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_KEY_PAIRS = os.getenv("SECRET_KEY_PAIRS", "")

# Parse secret keys
SECRET_KEYS = {
    pair.split(":")[0]: pair.split(":")[1]
    for pair in SECRET_KEY_PAIRS.split(",")
    if ":" in pair
}

# Flask app setup
app = Flask(__name__)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define conversation states
EMAIL = range(1)

# Function to generate OTP and time remaining
def generate_otp_with_time(secret_key):
    totp = pyotp.TOTP(secret_key)
    otp = totp.now()
    time_remaining = totp.interval - (int(time.time()) % totp.interval)
    return otp, time_remaining

# Validate email format and domain
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@(gmail\.com|outlook\.com)$"
    return re.match(pattern, email)

# Start the /getotp process
async def getotp_start(update: Update, context):
    logger.info(f"User {update.effective_user.id} started the /getotp process.")
    await update.message.reply_text(
        "يرجى إدخال بريدك الإلكتروني (Gmail أو Outlook) للحصول على كلمة المرور لمرة واحدة.\n"
        "يمكنك كتابة /cancel لإلغاء العملية."
    )
    return EMAIL

# Process the email input
async def process_email(update: Update, context):
    email = update.message.text.lower().strip()
    received_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Received email: {email} at {received_time}")

    if not is_valid_email(email):
        await update.message.reply_text("❌ بريد إلكتروني غير صالح!")
        return EMAIL

    secret_key = SECRET_KEYS.get(email)
    if not secret_key:
        await update.message.reply_text("❌ البريد الإلكتروني غير مسجل.")
        return EMAIL

    otp, time_remaining = generate_otp_with_time(secret_key)
    if time_remaining < 5:
        await update.message.reply_text(
            f"⚠️ كلمة المرور الحالية ستنتهي خلال {time_remaining} ثانية.\n"
            "انتظر قليلاً حتى يتم توليد كلمة مرور جديدة."
        )
    else:
        await update.message.reply_text(
            f"✅ كلمة المرور: {otp}\n"
            f"⏳ الوقت المتبقي لانتهاء الصلاحية: {time_remaining} ثانية"
        )

    return EMAIL

# Cancel the process
async def cancel(update: Update, context):
    logger.info(f"User {update.effective_user.id} cancelled the operation.")
    await update.message.reply_text("❌ تم إلغاء العملية. شكراً لاستخدامك البوت!")
    return ConversationHandler.END

# Set up Telegram bot application
application = Application.builder().token(BOT_TOKEN).build()

# Set up Telegram bot handlers
conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("getotp", getotp_start)],
    states={
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_email)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text(
    "مرحبًا بك في بوت OTP! استخدم /getotp للحصول على كلمة المرور لمرة واحدة."
)))
application.add_handler(conversation_handler)

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.process_update(update)
        return "OK", 200

# Health check route
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run(host="0.0.0.0", port=5000)



WEBHOOK_URL = f"https://fikra-bot.onrender.com/{BOT_TOKEN}"

def set_webhook():
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": WEBHOOK_URL},
    )
    if response.status_code == 200:
        logger.info("Webhook set successfully!")
    else:
        logger.error(f"Failed to set webhook: {response.text}")

# Call set_webhook in your __main__ section
if __name__ == "__main__":
    set_webhook()
    logger.info("Starting bot...")
    app.run(host="0.0.0.0", port=5000)

