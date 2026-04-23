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
    'Super': 'Supermercado'
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
id_file = "last_id.txt"
if os.path.exists(id_file):
    with open(id_file, "r") as f:
        last_message_id = int(f.read())
else:
    last_message_id = 0
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
                # Order reversed to properly insert on Google Sheets
                OldToNewest_list = NewToOldest_list[::-1]
            else:
                print(f"⚫ Message from date {telegram_message.date} [ID:{telegram_message.id}] is not a text!")
    
    if not NewToOldest_list:
        print("No new text messages to read :)")
        return
    print(f"--- Reading group messages post message ID: {last_message_id} ---")

    try:
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
    next_row = len(sheet.col_values(1)) + 1
    total_rows = sheet.row_count

    for message in OldToNewest_list:
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

            # If need to write in more rows, add cells
            if next_row > total_rows:
                cells_to_add = 1
                sheet.add_rows(cells_to_add)
                print(f"↕️ New cell added.")

            #Dictionary
            type = types_map.get(type, type)
            
            # Determines if price has any dots or commas. Return -1 if not
            dot_position = price.rfind('.')
            comma_position = price.rfind(',')
            # If both position are not -1, price is formatted acording to the Google Gheets. Dots removed and comma added (Format: 10000,xx)
            if dot_position != -1 or comma_position != -1:
                if comma_position > dot_position:
                    # Input: 10.000,54 | Output: 10000,54
                    price = price.replace(".", "")
                else:
                    # Input: 10,000.54 | Output: 10000,54
                    price = price.replace(",", "").replace(".", ",")

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
                    cell_range = f"A{next_row}:D{next_row}"
                    sheet.update(range_name=cell_range, values=[data], value_input_option='USER_ENTERED')
                    print(f"✅ Inserted on Row {next_row}: {name} ({type}) ${price} - [ID:{id}]")
                    next_row += 1
                except Exception as e:
                    print(f"❌ Unable to insert: {e}")
            else:
                print(f'⛔ Text message {message} not inserted! Price was not found ( Price:{price} ) ')
        else:
            print(f"⛔ Text message {message} not inserted! It only has {len(message)} parts! 5 are necessary.")
    
    # Save last message id 
    with open(id_file, "w") as f:
        f.write(str(new_last_message_id))
    print(f"💾 Progress Save. Next execution will be with messages after ID:{new_last_message_id}")
with client:
    client.loop.run_until_complete(main())