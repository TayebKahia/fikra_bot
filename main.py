from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters, ConversationHandler
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
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=4, use_context=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define conversation states
EMAIL = range(1)


# Validate email format and domain
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@(gmail\.com|outlook\.com)$"
    return re.match(pattern, email)


# Function to generate OTP and time remaining
def generate_otp_with_time(secret_key):
    totp = pyotp.TOTP(secret_key)
    otp = totp.now()
    time_remaining = totp.interval - (int(time.time()) % totp.interval)
    return otp, time_remaining


# Start the /getotp process
def getotp_start(update: Update, context):
    logger.info(f"User {update.effective_user.id} started the /getotp process.")
    update.message.reply_text(
        "يرجى إدخال بريدك الإلكتروني (Gmail أو Outlook) للحصول على كلمة المرور لمرة واحدة.\n"
        "يمكنك كتابة /cancel لإلغاء العملية."
    )
    return EMAIL


# Process the email input
def process_email(update: Update, context):
    email = update.message.text.lower().strip()
    received_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Received email: {email} at {received_time}")

    if not is_valid_email(email):
        update.message.reply_text("❌ بريد إلكتروني غير صالح!")
        return EMAIL

    secret_key = SECRET_KEYS.get(email)
    if not secret_key:
        update.message.reply_text("❌ البريد الإلكتروني غير مسجل.")
        return EMAIL

    otp, time_remaining = generate_otp_with_time(secret_key)
    if time_remaining < 5:
        update.message.reply_text(
            f"⚠️ كلمة المرور الحالية ستنتهي خلال {time_remaining} ثانية.\n"
            "انتظر قليلاً حتى يتم توليد كلمة مرور جديدة."
        )
    else:
        update.message.reply_text(
            f"✅ كلمة المرور: {otp}\n"
            f"⏳ الوقت المتبقي لانتهاء الصلاحية: {time_remaining} ثانية"
        )

    return EMAIL


# Cancel the process
def cancel(update: Update, context):
    logger.info(f"User {update.effective_user.id} cancelled the operation.")
    update.message.reply_text("❌ تم إلغاء العملية. شكراً لاستخدامك البوت!")
    return ConversationHandler.END


# Set up Telegram bot handlers
def setup_dispatcher(dp):
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("getotp", getotp_start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dp.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text(
        "مرحبًا بك في بوت OTP! استخدم /getotp للحصول على كلمة المرور لمرة واحدة."
    )))
    dp.add_handler(conversation_handler)
    return dp


dispatcher = setup_dispatcher(dispatcher)


# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "OK", 200


# Set a route for debugging
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

import requests

# Set the webhook automatically when the app starts
WEBHOOK_URL = f"https://<your-app-name>.onrender.com/{BOT_TOKEN}"

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
