import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from telethon import TelegramClient
import os 
from dotenv import load_dotenv

# Google Sheets Scope
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
        "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('creds/sheet_creds.json', scope)
    client_gs = gspread.authorize(creds)
    # Google Sheet Name
    sheet = client_gs.open("!Dinero").sheet1 
    print("✅ Succesful connection to Google Sheets")
except Exception as e:
    print(f"❌ Error to connect Google Sheets: {e}")
    exit()

load_dotenv("./creds/.env")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
chat_id = int(os.getenv("CHAT_ID"))

# Session file
client = TelegramClient('sesion_gastos', api_id, api_hash)

available_types = ['Supermercado', 'Compra', 'Servicio', 'Ropa', 'Entretenimiento', 'Inversion', 'Combustible', 'Deuda', 'Credito']
NewToOldest_list = []
# Map
types_map = {
    'S': 'Servicio',
    'C': 'Compra',
    'Super': 'Supermercado'
}

# --- 1. Read last ID  ---
id_file = "last_id.txt"
if os.path.exists(id_file):
    with open(id_file, "r") as f:
        last_message_id = int(f.read())
else:
    last_message_id = 0
async def main():
    print(f"--- Reading group messages post message ID: {last_message_id} ---")

    new_last_message_id = last_message_id
    
    async for telegram_message in client.iter_messages(chat_id, min_id=last_message_id, reverse=False):
        
        if telegram_message.id > new_last_message_id:
            new_last_message_id = telegram_message.id
            
        if telegram_message.text:

            # Divide a large message into individual messages - LIST COMPREHENSION
            words = [
                [telegram_message.id ,telegram_message.date.strftime("%d/%m/%Y")] + line.split() # .split() converts it to ['Product', 'Type', 'Price'] // Input "Product Type Price"
                for line in reversed(telegram_message.text.splitlines()) 
                    if line.strip()
            ]

            NewToOldest_list.extend(words)
    # Order reversed to properly insert on Google Sheets
    OldToNewest_list = NewToOldest_list[::-1]
    # If there are new messages...
    if new_last_message_id > last_message_id:

        # How many rows the sheet has
        next_row = len(sheet.col_values(1)) + 1
        total_rows = sheet.row_count

        for message in OldToNewest_list:
            print(message)
            # Validates if the message is acceptable (3 values minimum)
            if len(message) >= 3: 
                # Array first position is the date
                id = message[0]
                date = message[1]
                # Array last but one position is the type of product
                part = message[-2].lower()
                type = (part.rstrip('s') if len(part) > 1 else part).capitalize() #Determines if only a letter 'S' or a word
                #Array last position is the price
                price = message[-1]
                
                # Join everything except the first and last 2 positions
                name = " ".join(message[2:-2])

                #Validates if price is a digit
                if price.isdigit():

                    # If need to write in more rows, add cells
                    if next_row > total_rows:
                        cells_to_add = 1
                        sheet.add_rows(cells_to_add)
                        print(f"↕️ New cell added.")

                    #Dictionary
                    type = types_map.get(type, type)

                    #Validates if type exist between the options
                    if type not in available_types:
                        final_type = "Compra"
                        print(f"⚠️ Product Type:'{type}' not recognized. Saved as '{final_type}'.")
                        type = final_type

                    # --- Insert in Google Sheets ---
                    try:
                        # Insert row with 4 values
                        data = [date, name, type, price]
                        cell_range = f"A{next_row}:D{next_row}"
                        sheet.update(range_name=cell_range, values=[data], value_input_option='USER_ENTERED')
                        print(f"✅ Inserted on Row {next_row}: {name} ({type}) ${price} ({id})")
                        next_row += 1
                    except Exception as e:
                        print(f"❌ Unable to insert: {e}")
            else:
                print(f"⛔ Product {message} not accepted")
    # Save last message id 
    
        with open(id_file, "w") as f:
            f.write(str(new_last_message_id))
        print(f"💾 Progress Save. Next execution will be with: {new_last_message_id}")
    else:
        print("No new messages to process.")
with client:
    client.loop.run_until_complete(main())