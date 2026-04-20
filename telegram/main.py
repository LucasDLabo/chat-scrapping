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

async def main():
    print(f"--- Reading group messages ---")
    
    # iter_messages read the messages from the recent one to the old one
    # 'limit=10' return the last 10
    async for message in client.iter_messages(chat_id, limit=99, reverse=True):
        if message.text:
            
            # Divide a large message into individual messages
            lines = message.text.splitlines()
            for line in lines:
                # Clean 
                line = line.strip()
                if not line: continue # If empty...
                messageParts = line.split()

                #Validates if the message is acceptable (3 values minimum)
                if len(messageParts) >= 3: 
                    # Last 2 positions
                    part = messageParts[-2].lower()
                    type = (part.rstrip('s') if len(part) > 1 else part).capitalize() #Determines if only a letter 'S' or a word
                    price = messageParts[-1]
                    
                    # Join everything except the last 2 positions
                    name = " ".join(messageParts[:-2])

                    #Validates if price is a digit
                    if price.isdigit():

                        # Verifications
                        next_row = len(sheet.col_values(1)) + 1
                        # How many rows the sheet has
                        total_rows = sheet.row_count

                        if next_row > total_rows:
                        # If need to write in more rows, add cells
                            cells_to_add = 1
                            sheet.add_rows(cells_to_add)
                            print(f"↕️ New cell added.")

                        # Converts date to dd/mm/yyyy
                        date = message.date.strftime("%d/%m/%Y")

                        if type == 'S': type = 'Servicio'
                        if type == 'C': type = 'Compra'
                        if type == 'Super': type = 'Supermercado'

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
                            print(f"✅ Inserted on Row {next_row}: {name} ({type}) ${price}")
                            next_row += 1
                        except Exception as e:
                            print(f"❌ Unable to insert: {e}")
                else:
                    print(f"⛔ Product {messageParts} not accepted")

with client:
    client.loop.run_until_complete(main())