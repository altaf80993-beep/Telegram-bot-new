import re
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import CreateChatRequest, DeleteChatRequest
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import ChatInviteAlready

load_dotenv()

# ============ CONFIG ============
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
MAIN_GROUP = os.getenv("MAIN_GROUP")

# ============ DATA STORAGE ============
active_deals = {}  # {group_id: {"buyer": "@x", "seller": "@y", "status": "active"}}

# ============ LOGGING ============
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# ============ CLIENTS ============
userbot = TelegramClient("escrow_session", API_ID, API_HASH)
bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ============ FORMAT CHECK ============
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

# ============ DELETE NON-FORMAT MESSAGES ============
@bot.on(events.NewMessage(chats=MAIN_GROUP))
async def filter_format(event):
    msg = event.message
    if not msg.text:
        return
    
    # Skip commands and admin messages
    if msg.text.startswith("/"):
        return
    
    sender = await event.get_sender()
    try:
        if sender.username and sender.username.lower() == ADMIN_USERNAME.strip("@").lower():
            return
    except:
        pass
    
    if not is_valid_format(msg.text):
        try:
            await msg.delete()
            logger.info(f"Deleted: {msg.text[:50]}...")
        except Exception as e:
            logger.error(f"Delete failed: {e}")

# ============ /escrow COMMAND ============
@bot.on(events.NewMessage(pattern="/escrow"))
async def create_escrow(event):
    msg = event.message
    sender = await event.get_sender()
    seller_username = f"@{sender.username}" if sender.username else sender.first_name
    
    parts = msg.text.split()
    if len(parts) < 2:
        await event.reply("❌ Usage: /escrow @buyer_username")
        return
    
    buyer_username = parts[1]
    if not buyer_username.startswith("@"):
        await event.reply("❌ Buyer username @ se start hona chahiye")
        return
    
    # Get deal number
    deal_num = len(active_deals) + 1
    
    try:
        # Create new group using userbot
        group = await userbot(CreateChatRequest(
            users=[buyer_username, ADMIN_USERNAME],
            title=f"Deal #{deal_num} | {seller_username} 🤝 {buyer_username}"
        ))
        
        group_id = group.chats[0].id
        
        # Store deal info
        active_deals[group_id] = {
            "buyer": buyer_username,
            "seller": seller_username,
            "status": "active",
            "deal_num": deal_num,
            "created_at": datetime.now()
        }
        
        # Get invite link
        invite = await userbot.get_permissions(group_id, "me")
        
        # Welcome message in new group
        await userbot.send_message(group_id, 
            f"🔐 **Escrow Group Created**\n\n"
            f"📋 **Deal #{deal_num}**\n"
            f"👤 **Buyer:** {buyer_username}\n"
            f"👤 **Seller:** {seller_username}\n"
            f"👨‍💼 **Admin:** {ADMIN_USERNAME}\n\n"
            f"📌 **Commands:**\n"
            f"/complete - Deal successful\n"
            f"/cancel - Deal cancelled\n"
            f"/status - Check deal status"
        )
        
        await event.reply(
            f"✅ **Escrow Group Created!**\n\n"
            f"📋 **Deal #{deal_num}**\n"
            f"👤 **Buyer:** {buyer_username}\n"
            f"👤 **Seller:** {seller_username}\n"
            f"👨‍💼 **Admin:** {ADMIN_USERNAME}\n\n"
            f"🔗 Group created — all parties added.\n"
            f"Check your Telegram chats!"
        )
        
        logger.info(f"Deal #{deal_num} created: {seller_username} + {buyer_username}")
        
    except Exception as e:
        await event.reply(f"❌ Error: {e}")
        logger.error(f"Create group error: {e}")

# ============ /complete COMMAND ============
@bot.on(events.NewMessage(pattern="/complete"))
async def complete_deal(event):
    group_id = event.chat_id
    
    if group_id not in active_deals:
        await event.reply("❌ Ye koi active deal group nahi hai")
        return
    
    deal = active_deals[group_id]
    
    msg = (
        f"✅ **DEAL COMPLETED!** 🎉\n\n"
        f"📋 **Deal #{deal['deal_num']}**\n"
        f"👤 **Buyer:** {deal['buyer']}\n"
        f"👤 **Seller:** {deal['seller']}\n"
        f"📅 **Deal Time:** {deal['created_at'].strftime('%d-%b-%Y %I:%M %p')}\n\n"
        f"🤝 Deal successfully completed!\n"
        f"⚠️ This group will be deleted in 5 minutes."
    )
    
    await event.reply(msg)
    
    # Notify in main group
    await bot.send_message(MAIN_GROUP, 
        f"✅ **Deal #{deal['deal_num']} Completed!**\n"
        f"{deal['buyer']} 🤝 {deal['seller']}"
    )
    
    # Delete group after 5 minutes
    await asyncio.sleep(300)
    try:
        await userbot(DeleteChatRequest(chat_id=group_id))
        del active_deals[group_id]
        logger.info(f"Group {group_id} deleted after deal completion")
    except:
        pass

# ============ /cancel COMMAND ============
@bot.on(events.NewMessage(pattern="/cancel"))
async def cancel_deal(event):
    group_id = event.chat_id
    
    if group_id not in active_deals:
        await event.reply("❌ Ye koi active deal group nahi hai")
        return
    
    deal = active_deals[group_id]
    
    msg = (
        f"❌ **DEAL CANCELLED**\n\n"
        f"📋 **Deal #{deal['deal_num']}**\n"
        f"👤 **Buyer:** {deal['buyer']}\n"
        f"👤 **Seller:** {deal['seller']}\n\n"
        f"⚠️ This group will be deleted in 1 minute."
    )
    
    await event.reply(msg)
    
    # Notify in main group
    await bot.send_message(MAIN_GROUP, 
        f"❌ **Deal #{deal['deal_num']} Cancelled**\n"
        f"{deal['buyer']} ❌ {deal['seller']}"
    )
    
    # Delete group after 1 minute
    await asyncio.sleep(60)
    try:
        await userbot(DeleteChatRequest(chat_id=group_id))
        del active_deals[group_id]
        logger.info(f"Group {group_id} deleted after deal cancellation")
    except:
        pass

# ============ /status COMMAND ============
@bot.on(events.NewMessage(pattern="/status"))
async def deal_status(event):
    group_id = event.chat_id
    
    if group_id not in active_deals:
        await event.reply("❌ Ye koi active deal group nahi hai")
        return
    
    deal = active_deals[group_id]
    
    await event.reply(
        f"📊 **Deal Status**\n\n"
        f"📋 **Deal #{deal['deal_num']}**\n"
        f"👤 **Buyer:** {deal['buyer']}\n"
        f"👤 **Seller:** {deal['seller']}\n"
        f"📌 **Status:** {deal['status'].upper()}\n"
        f"📅 **Created:** {deal['created_at'].strftime('%d-%b-%Y %I:%M %p')}"
    )

# ============ /start COMMAND ============
@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(event):
    await event.reply(
        "✅ **Escrow Bot Active!**\n\n"
        "📌 **Commands:**\n"
        "/escrow @username - Create new deal group\n"
        "/complete - Mark deal as complete\n"
        "/cancel - Cancel deal\n"
        "/status - Check deal status\n\n"
        "⚠️ Sirf fixed format posts allowed in main group!"
    )

# ============ MAIN ============
async def main():
    await userbot.start()
    logger.info("🚀 Userbot started!")
    logger.info("🤖 Bot started!")
    logger.info("✅ Escrow system LIVE!")
    
    await asyncio.gather(
        bot.run_until_disconnected(),
        userbot.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())
