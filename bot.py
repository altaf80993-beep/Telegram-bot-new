import re
import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatMemberStatus

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@admin")
ESCROW_GROUP_ID = os.getenv("MAIN_GROUP", "@escrow_group")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def is_valid_format(text: str) -> bool:
    pattern = re.compile(
        r"^(#Selling|#Buying)\s*[\r\n]+"
        r"Chain:\s*.+[\r\n]+"
        r"Amount\[USDT(?:/USDC)?\]:\s*.+[\r\n]+"
        r"Amount\[INR\]:\s*.+[\r\n]+"
        r"Rate\[INR(?:/USDT)?\]:\s*.+[\r\n]+"
        r"Payment Method:\s*.+",
        re.IGNORECASE
    )
    return bool(pattern.match(text.strip()))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Active!\n/escrow @username - Escrow group link")

async def escrow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.message.from_user
    seller = f"@{sender.username}" if sender.username else sender.first_name
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /escrow @buyer_username")
        return
    buyer = args[0]
    if not buyer.startswith("@"):
        await update.message.reply_text("Buyer username @ se start hona chahiye")
        return
    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=ESCROW_GROUP_ID,
            member_limit=3,
            creates_join_request=False
        )
        await update.message.reply_text(
            f"ESCROW CREATED\n\n"
            f"Buyer: {buyer}\n"
            f"Seller: {seller}\n"
            f"Admin: {ADMIN_USERNAME}\n\n"
            f"Join Link: {invite.invite_link}"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text or msg.text.startswith("/"):
        return
    try:
        member = await context.bot.get_chat_member(msg.chat_id, msg.from_user.id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except:
        pass
    if not is_valid_format(msg.text):
        try:
            await msg.delete()
        except:
            pass

flask_app = Flask(__name__)

@flask_app.route("/", methods=["GET"])
def home():
    return "Bot Running!"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), app.bot)
    app.update_queue.put(update)
    return "OK"

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("escrow", escrow_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_messages))

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.initialize())
    
    loop.run_until_complete(app.bot.set_webhook(
        url="https://telegram-bot-new-3-3jir.onrender.com/webhook"
    ))
    
    loop.run_until_complete(app.start())
    logger.info("Bot running with webhook...")
    flask_app.run(host="0.0.0.0", port=PORT)
