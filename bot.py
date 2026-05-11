import re
import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.messages import CreateChatRequest

load_dotenv()

API_ID = int(os.getenv("32415663"))
API_HASH = os.getenv("20df10ed337f4a6b54384859edea1556') 
BOT_TOKEN = os.getenv("8614020088:AAGCqe2wIIEKimwVzunUIE0JTL3UPzECAH0")
ADMIN_USERNAME = os.getenv("@Crypto_8099")
MAIN_GROUP = os.getenv("@escrow_only_usdt")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def is_valid_format(text: str) -> bool:
    import re
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

@bot.on(events.NewMessage(chats=MAIN_GROUP))
async def filter_format(event):
    msg = event.message
    if not msg.text or msg.text.startswith("/"):
        return
    try:
        sender = await event.get_sender()
        if sender.username and sender.username.lower() == ADMIN_USERNAME.strip("@").lower():
            return
    except:
        pass
    if not is_valid_format(msg.text):
        try:
            await msg.delete()
        except:
            pass

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(event):
    await event.reply(
        "✅ **Escrow Bot Active!**\n\n"
        "/escrow @username - Naya deal group banaye\n"
        "/complete - Deal complete (group mein)\n"
        "/cancel - Deal cancel (group mein)\n"
        "/status - Deal status (group mein)"
    )

@bot.on(events.NewMessage(pattern="/escrow"))
async def escrow_cmd(event):
    msg = event.message
    sender = await event.get_sender()
    seller = f"@{sender.username}" if sender.username else sender.first_name
    
    parts = msg.text.split()
    if len(parts) < 2:
        await event.reply("❌ Usage: /escrow @buyer_username")
        return
    
    buyer = parts[1]
    if not buyer.startswith("@"):
        await event.reply("❌ Username @ se start hona chahiye")
        return
    
    try:
        async with TelegramClient("user_session", API_ID, API_HASH) as userbot:
            await userbot.start()
            group = await userbot(CreateChatRequest(
                users=[buyer, ADMIN_USERNAME],
                title=f"🤝 Deal | {seller} & {buyer}"
            ))
        
        await event.reply(
            f"✅ **Group Created!**\n\n"
            f"👤 Buyer: {buyer}\n"
            f"👤 Seller: {seller}\n"
            f"👨‍💼 Admin: {ADMIN_USERNAME}\n\n"
            f"Check your chats - new group created!"
        )
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

async def main():
    logger.info("🚀 Bot started!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())
