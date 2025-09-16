from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
from PIL import Image, ImageDraw, ImageFont
import qrcode
from io import BytesIO
import os

# Load from GitHub Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

# Steps
NAME, ROLL, COURSE, COLLEGE, PHOTO = range(5)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Let's create your Student ID.\n\nPlease enter your Name:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['name'] = update.message.text
    await update.message.reply_text("✅ Got it!\nNow send your Roll Number:")
    return ROLL

async def get_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['roll'] = update.message.text
    await update.message.reply_text("👌 Great!\nNow send your Course:")
    return COURSE

async def get_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['course'] = update.message.text
    await update.message.reply_text("📚 Nice!\nNow send your College Name:")
    return COLLEGE

async def get_college(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['college'] = update.message.text
    await update.message.reply_text("📷 Finally, please send your Photo:")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    photo_bytes = BytesIO()
    await photo.download_to_memory(out=photo_bytes)
    photo_bytes.seek(0)
    user_data['photo'] = Image.open(photo_bytes).resize((100, 100))

    # Make QR
    qr_text = f"{user_data['name']} | {user_data['roll']} | {user_data['course']} | {user_data['college']}"
    qr_img = qrcode.make(qr_text).resize((100, 100))

    # Create ID Card
    card = Image.new("RGB", (600, 350), "white")
    draw = ImageDraw.Draw(card)

    font_title = ImageFont.truetype("arial.ttf", 24)
    font_text = ImageFont.truetype("arial.ttf", 20)

    # College
    draw.text((150, 20), user_data['college'], font=font_title, fill="black")

    # Details
    draw.text((50, 120), f"Name: {user_data['name']}", font=font_text, fill="black")
    draw.text((50, 170), f"Roll: {user_data['roll']}", font=font_text, fill="black")
    draw.text((50, 220), f"Course: {user_data['course']}", font=font_text, fill="black")

    # Paste Photo + QR
    card.paste(user_data['photo'], (450, 50))
    card.paste(qr_img, (450, 200))

    bio = BytesIO()
    bio.name = "student_id.png"
    card.save(bio, "PNG")
    bio.seek(0)

    await update.message.reply_photo(bio, caption="🎓 Here is your Student ID Card!")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Process cancelled.")
    return ConversationHandler.END

# Main
app = Application.builder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        ROLL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_roll)],
        COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_course)],
        COLLEGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_college)],
        PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)

app.run_polling()
