from telethon import TelegramClient
import os 
from dotenv import load_dotenv

load_dotenv("./creds/.env")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
chat_id = int(os.getenv("CHAT_ID"))


# Session file
client = TelegramClient('sesion_gastos', api_id, api_hash)

async def main():
    print(f"--- Reading group messages ---")
    
    # iter_messages read the messages from the recent one to the old one
    # 'limit=20' return the last 10
    async for message in client.iter_messages(chat_id, limit=10):
        if message.text:

            messageParts = message.text.split()
            if len(messageParts) >= 3:
                
                # Last 2 positions
                price = messageParts[-1]
                type = messageParts[-2]
                # Join everything except the last 2 positions
                name = " ".join(messageParts[:-2])
                
                if price.isdigit():
                    # Converts date to dd/mm/yyyy
                    date = message.date.strftime("%d/%m/%Y")
                    print(f"✅ {date} | {name} ({type}) ${price}")

with client:
    client.loop.run_until_complete(main())