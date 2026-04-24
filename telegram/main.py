import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import os 
from dotenv import load_dotenv

load_dotenv("./creds/.env")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
chat_id = int(os.getenv("CHAT_ID"))
session_str = os.getenv("SESSION_STR")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

google_creds_raw = os.getenv("GOOGLE_CREDS_JSON")

if google_creds_raw:
    creds_dict = json.loads(google_creds_raw)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name('./creds/sheet_creds.json', scope)

client_gs = gspread.authorize(creds)


# Session file
client = TelegramClient(StringSession(session_str), api_id, api_hash)

available_types = ['Supermercado', 'Compra', 'Servicio', 'Ropa', 'Entretenimiento', 'Inversion', 'Combustible', 'Deuda', 'Credito']
NewToOldest_list = []
# Map
types_map = {
    'S': 'Servicio',
    'C': 'Compra',
    'Super': 'Supermercado',
    'Comb': 'Combustible',
    'D': 'Deuda',
    'E': 'Entretenimiento',
    'R': 'Ropa',
    'Cred': 'Credito',
    'I': 'Inversion'
}

def price_is_valid(price):
    # Remove thousand separators (dots) and replace commas with dots (decimal separator)
    # Input: 10.000,40 - Output: 10000.40
    price_formatted = price.replace(".", "").replace(",", ".")
    try:
        float(price_formatted)
        return True
    except ValueError:
        return False

# ---  Read last ID file  ---
try:
    print(f"📡 Fetching last text message ID...")
    config_sheet = client_gs.open("!Dinero").worksheet("Inicio")
    # Read saved ID 
    cell_value = config_sheet.acell('C1').value
    last_message_id = int(cell_value) if cell_value else 0
except Exception as e:
    print(f"❌ Error to read Last ID value {e}")
    exit()

async def main():
    new_last_message_id = last_message_id
    
    async for telegram_message in client.iter_messages(chat_id, min_id=last_message_id, reverse=False):

        if telegram_message.id > new_last_message_id:
            new_last_message_id = telegram_message.id

        if new_last_message_id > last_message_id:
            # Validates if the message is a text in order to avoid reading stickers and images
            if telegram_message.text:
                # Divide a large message into individual messages - LIST COMPREHENSION
                words = [
                    [telegram_message.id ,telegram_message.date.strftime("%d/%m/%Y")] + line.split() # .split() converts it to ['Product', 'Type', 'Price'] // Input "Product Type Price"
                    for line in reversed(telegram_message.text.splitlines()) 
                        if line.strip()
                ]

                NewToOldest_list.extend(words)
                # Order reversed just in case
                OldToNewest_list = NewToOldest_list[::-1]
            else:
                print(f"⚫ Message from date {telegram_message.date} [ID:{telegram_message.id}] is not a text!")
    
    if not NewToOldest_list:
        print("No new text messages to read :)")
        return
    print(f"--- Reading group messages post message ID: {last_message_id} ---")

    try:
        if google_creds_raw:
            creds_dict = json.loads(google_creds_raw)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            print("✅ Connected using Github Secrets")
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('creds/sheet_creds.json', scope)

        client_gs = gspread.authorize(creds)
        # Google Sheet file
        spreadsheet = client_gs.open("!Dinero")
        
        # Worksheet name
        sheet = spreadsheet.worksheet("Compras")
        print(f"✅ Succesful connection to Google Sheets | File: {spreadsheet} - Sheet: {sheet}")
    except Exception as e:
        print(f"❌ Error to connect Google Sheets: {e}")
        exit()

    # How many rows the sheet has
    total_rows = sheet.row_count

    for message in NewToOldest_list:
        # Validates if the message is acceptable (5 values minimum)
        # [ID, Date, Name, Type, Price]
        if len(message) >= 5: 
            # Array first positions are ID and Date
            id = message[0]
            date = message[1]
            # Array last but one position is the type of product
            part = message[-2].lower()
            type = (part.rstrip('s') if len(part) > 1 else part).capitalize() #Determines if only a letter 'S' or a word
            #Array last position is the price
            price = message[-1]
            
            # Join everything except the second and last 2 positions
            name = " ".join(message[2:-2])

            #Dictionary
            type = types_map.get(type, type)
            
            # Format price text messages to return this output: 100000,xx
            s = str(price).strip()
            if "." in s and "," in s: # If messages has both separators, the last is the decimal
                if s.rfind(".") > s.rfind(","):
                    # Input: 100,000.xx
                    price = s.replace(",", "").replace(".",",")
                else:
                    # Input: 100.000,xx
                    price = s.replace(".", "")
            elif "," in s: # If only commas...
                # If there are not 2 decimals...
                if len(s.split(",")[-1]) != 2:
                    # Input: 100,000
                    price = s.replace(",", "")
            elif "." in s: # If only dots...
                # If there are not 2 decimals
                if len(s.split(".")[-1]) != 2:
                    # Input: 100.000
                    price = s.replace(".", "")
                else:
                    # Input: 100000.xx
                    price = s.replace(".", ",")

            if price_is_valid(price):

                #Validates if type exist between the options
                if type not in available_types:
                    final_type = "Compra"
                    print(f"⚠️ Text message {message} does not have a recognizable type. Saved as '{final_type}'.")
                    type = final_type
                # --- Insert in Google Sheets ---
                try:
                    # Insert row with 4 values
                    data = [date, name, type, price]
                    sheet.insert_row(data, index=total_rows)
                    print(f"✅ Inserted {name} ({type}) ${price} - [ID:{id}]")
                except Exception as e:
                    print(f"❌ Unable to insert: {e}")
            else:
                print(f'⛔ Text message {message} not inserted! Price was not found ( Price:{price} ) ')
        else:
            print(f"⛔ Text message {message} not inserted! It only has {len(message)} parts! 5 are necessary.")
    
    # Save last message id 
    if new_last_message_id > last_message_id:
        config_sheet.update(range_name='C1', values=[[new_last_message_id]])
        print(f"💾 Progress Save. Next execution will be with messages after ID:{new_last_message_id}")

with client:
    client.loop.run_until_complete(main())