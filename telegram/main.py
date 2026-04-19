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
    all_list = [] 
    async for message in client.iter_messages(chat_id, limit=6, reverse=False):
        if message.text:
            
            # Divide a large message into individual messages
            lines = message.text.splitlines()
            for line in reversed(lines):
                
                # Clean 
                line = line.strip()
                if not line: continue # If empty...
                messageParts = line.split()
                all_list.append(messageParts) # Guardamos la sub-lista
            
            if len(messageParts) >= 3: 
                # Last 2 positions
                price = messageParts[-1].capitalize()
                type = messageParts[-2].capitalize()

                # if type == 'Compras':
                #     type = 'Compra'
                # if type == 'Servicio':
                #     type = 'Servicios'
                    
                # Join everything except the last 2 positions
                name = " ".join(messageParts[:-2])

                if price.isdigit():
                    # Converts date to dd/mm/yyyy
                    date = message.date.strftime("%d/%m/%Y")
                    #print(f"✅ {date} | {name} ({type}) ${price}")

    all_list.reverse()
    for product in all_list:
        print(f"Producto: {product}")
with client:
    client.loop.run_until_complete(main())