import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import MessageHandler, Filters
import requests
import folium

# Variabili di ambiente
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
APRS_API_KEY = os.getenv('APRS_API_KEY')

# Verifica del token
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Il token del bot non è definito. Controlla le variabili di ambiente.")

# Flask app
app = Flask(__name__)

# Configura il bot e il dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# Database temporaneo
members_callsigns = []

# Funzioni del bot
def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Aggiungi Membro", callback_data='add_member')],
                [InlineKeyboardButton("Genera Mappa", callback_data='generate_map')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Scegli un'opzione:", reply_markup=reply_markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == 'add_member':
        query.message.reply_text("Invia il nominativo del membro da aggiungere:")
        context.user_data['add_member'] = True
    elif query.data == 'generate_map':
        query.message.reply_text("Generazione mappa in corso...")
        generate_map(query.message.chat_id)

def add_member(update: Update, context: CallbackContext):
    context.user_data['add_member'] = False
    # Controlla che l'utente abbia inviato un nominativo valido
    callsign = update.message.text.strip().upper()  # Rimuove spazi e converte in maiuscolo
    if not callsign:
        update.message.reply_text("Per favore, fornisci un nominativo APRS valido.")
        return

    # Aggiungi il nominativo alla lista se non è già presente
    if callsign not in members_callsigns:
        members_callsigns.append(callsign)
        update.message.reply_text(f"Nominativo {callsign} aggiunto con successo!")
    else:
        update.message.reply_text(f"Il nominativo {callsign} è già presente nella lista.")


from geopy.distance import geodesic
from math import radians, degrees
import folium
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
import time

def generate_map(chat_id):
    # Esempio di dati APRS (da sostituire con la chiamata API reale)
    aprs_data = get_aprs_data(chat_id)

    if not aprs_data:
        bot.send_message(chat_id=chat_id, text="APRS vuoto")
        return

    bot.send_message(chat_id=chat_id, text=f"Trovati {len(aprs_data)} membri")
    # Calcola il centro della mappa
    latitudes = [entry['lat'] for entry in aprs_data]
    longitudes = [entry['lon'] for entry in aprs_data]
    center_lat = sum(latitudes) / len(latitudes)
    center_lon = sum(longitudes) / len(longitudes)

    # Calcola la distanza massima dal centro
    center = (center_lat, center_lon)
    max_distance = max(geodesic(center, (entry['lat'], entry['lon'])).meters for entry in aprs_data)

    # Aggiungi un buffer di 100 metri
    max_distance += 100

    # Stima del livello di zoom
    def calculate_zoom(distance):
        if distance < 1000:  # Meno di 1 km
            return 15
        elif distance < 5000:  # 1-5 km
            return 13
        elif distance < 10000:  # 5-10 km
            return 12
        elif distance < 20000:  # 10-20 km
            return 11
        else:
            return 10

    zoom_level = calculate_zoom(max_distance)

    # Creare la mappa centrata
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level)

    # Aggiungere i marker
    for member in aprs_data:
        folium.Marker(
            location=[member['lat'], member['lon']],
            popup=member['name']
        ).add_to(m)

    # Salvare la mappa come HTML
    map_file = "map.html"
    m.save(map_file)

    # Utilizzare Selenium per generare l'immagine
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    driver.set_window_size(1024, 1024)

    driver.get(f"file://{os.path.abspath(map_file)}")
    time.sleep(5)  # Attendere il caricamento della mappa

    screenshot_file = "map_screenshot.png"
    driver.save_screenshot(screenshot_file)
    driver.quit()

    # Convertire e ridimensionare l'immagine
    corrected_file = "map_corrected.jpg"
    with Image.open(screenshot_file) as img:
        img = img.convert("RGB")
        img.thumbnail((1024, 1024), Image.ANTIALIAS)
        img.save(corrected_file, format="JPEG", quality=85)

    # Inviare l'immagine tramite Telegram
    with open(corrected_file, 'rb') as f:
        bot.send_photo(chat_id=chat_id, photo=f)

    # Pulizia file temporanei
    os.remove(map_file)
    os.remove(screenshot_file)
    os.remove(corrected_file)

def get_aprs_data(chat_id):
    # Usa i nominativi aggiunti dinamicamente
    if not members_callsigns:
        bot.send_message(chat_id=chat_id, text="members_callsigns è vuota")
        return []  # Nessun nominativo nella lista

    # Costruisci l'URL con i nominativi presenti nella lista
    callsigns_str = ",".join(members_callsigns[:20])  # Limite massimo di 20 nominativi
    url = f"https://api.aprs.fi/api/get?name={callsigns_str}&what=loc&apikey={APRS_API_KEY}&format=json"

    # Effettua la richiesta all'API
    response = requests.get(url).json()  

    # Verifica il risultato
    if response.get("result") != "ok":
        print(f"Errore nella richiesta APRS: {response.get('description')}")
        return []

    # Estrai i dati dei membri
    entries = response.get("entries", [])
    if not entries:
        bot.send_message(chat_id=chat_id, text="entries from response is empty")
        print("Nessun dato trovato per i nominativi forniti.")
        return []
    aprs_data = []
    for entry in entries:
        aprs_data.append({
            "name": entry["name"],  # Nome del nominativo
            "lat": float(entry["lat"]),  # Latitudine
            "lon": float(entry["lng"]),  # Longitudine
            "comment": entry.get("comment", ""),  # Commento (facoltativo)
        })

    return aprs_data


# Aggiungi gestori al dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button))

# dispatcher.add_handler(CommandHandler("add_member", add_member))
# Define a custom filter as a function
def custom_filter(update, context):
    return context.user_data.get('add_member', False)
# Register the handler
dispatcher.add_handler(MessageHandler(Filters.all, add_member, custom_filter))

# Route per il webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'OK'

# Imposta il webhook al lancio
@app.before_first_request
def set_webhook():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    bot.set_webhook(webhook_url)

# Avvio del server Flask
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
