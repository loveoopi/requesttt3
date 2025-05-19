import os
from telethon import TelegramClient, events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantsAdmins
import logging
import asyncio
import signal
import sys

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded Telegram API credentials
API_ID = 22580205
API_HASH = '0925158a403a28fce3f3f46eca72bc99'
BOT_TOKEN = '8168429266:AAEemf15r7i7iQxO6nn45nIg2odU3QjbY4M'

# Initialize Telethon client
client = TelegramClient('bot', API_ID, API_HASH)

# Store pending join requests (chat_id -> list of user_ids)
pending_requests = {}

# Event handler for new join requests
@client.on(events.ChatAction)
async def handle_join_request(event):
    if event.user_joined or event.user_added:
        chat_id = event.chat_id
        user_id = event.user_id
        # Store pending join request
        if chat_id not in pending_requests:
            pending_requests[chat_id] = []
        if user_id not in pending_requests[chat_id]:
            pending_requests[chat_id].append(user_id)
            logger.info(f"New join request from user {user_id} in chat {chat_id}")

# Command to accept all pending join requests
@client.on(events.NewMessage(pattern='/acceptu'))
async def accept_all(event):
    chat = await event.get_chat()
    sender = await event.get_sender()
    
    # Check if used in a group
    if not hasattr(chat, 'admin_rights'):
        await event.reply("This command can only be used in groups.")
        return

    # Check if sender is an admin
    chat_entity = await client.get_entity(chat.id)
    admins = await client.get_participants(chat_entity, filter=ChannelParticipantsAdmins)
    if not any(admin.id == sender.id for admin in admins):
        await event.reply("Only group admins can use this command.")
        return

    chat_id = chat.id
    if chat_id not in pending_requests or not pending_requests[chat_id]:
        await event.reply("No pending join requests.")
        return

    try:
        # Approve each user (remove restrictions)
        for user_id in pending_requests[chat_id]:
            await client(EditBannedRequest(
                channel=chat_id,
                participant=user_id,
                banned_rights=ChatBannedRights(
                    until_date=None,
                    view_messages=False  # Allow viewing messages (approve)
                )
            ))
            logger.info(f"Accepted join request from user {user_id} in chat {chat_id}")

        count = len(pending_requests[chat_id])
        pending_requests[chat_id] = []  # Clear requests
        await event.reply(f"Accepted {count} join request(s).")
    except Exception as e:
        logger.error(f"Error accepting join requests: {e}")
        await event.reply("An error occurred while accepting join requests.")

# Command to reject all pending join requests
@client.on(events.NewMessage(pattern='/rejectu'))
async def reject_all(event):
    chat = await event.get_chat()
    sender = await event.get_sender()
    
    # Check if used in a group
    if not hasattr(chat, 'admin_rights'):
        await event.reply("This command can only be used in groups.")
        return

    # Check if sender is an admin
    chat_entity = await client.get_entity(chat.id)
    admins = await client.get_participants(chat_entity, filter=ChannelParticipantsAdmins)
    if not any(admin.id == sender.id for admin in admins):
        await event.reply("Only group admins can use this command.")
        return

    chat_id = chat.id
    if chat_id not in pending_requests or not pending_requests[chat_id]:
        await event.reply("No pending join requests.")
        return

    try:
        # Reject each user (ban or keep restricted)
        for user_id in pending_requests[chat_id]:
            await client(EditBannedRequest(
                channel=chat_id,
                participant=user_id,
                banned_rights=ChatBannedRights(
                    until_date=None,
                    view_messages=True  # Deny access
                )
            ))
            logger.info(f"Rejected join request from user {user_id} in chat {chat_id}")

        count = len(pending_requests[chat_id])
        pending_requests[chat_id] = []  # Clear requests
        await event.reply(f"Rejected {count} join request(s).")
    except Exception as e:
        logger.error(f"Error rejecting join requests: {e}")
        await event.reply("An error occurred while rejecting join requests.")

# Signal handler for graceful shutdown
def handle_shutdown(loop):
    tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()

async def main():
    # Start the client
    logger.info("Bot is starting...")
    await client.start(bot_token=BOT_TOKEN)
    
    # Run the client with polling
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Create and configure the event loop
    loop = asyncio.get_event_loop()
    
    # Set up signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown, loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(client.disconnect())
        loop.close()
