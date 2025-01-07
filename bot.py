import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, CallbackContext
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
members = []

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
    if context.user_data.get('add_member'):
        members.append(update.message.text)
        update.message.reply_text(f"{update.message.text} aggiunto!")
        context.user_data['add_member'] = False

from PIL import Image
import imgkit

def generate_map(chat_id):
    # Esempio di dati APRS
    aprs_data = get_aprs_data()

    # Creare la mappa
    m = folium.Map(location=[45.4642, 9.19], zoom_start=13)
    for member in aprs_data:
        folium.Marker([member['lat'], member['lon']], popup=member['name']).add_to(m)

    # Salvare la mappa come HTML
    map_file = "map.html"
    m.save(map_file)

    # Convertire l'HTML in PNG
    png_file = "map.png"
    imgkit.from_file(map_file, png_file)

    # Ridimensionare l'immagine per soddisfare i requisiti di Telegram
    resized_file = "map_resized.png"
    with Image.open(png_file) as img:
        img = img.convert("RGB")  # Assicurarsi che sia in formato RGB
        max_size = (1024, 1024)  # Risoluzione massima supportata da Telegram
        img.thumbnail(max_size, Image.ANTIALIAS)  # Ridimensiona mantenendo il rapporto
        img.save(resized_file, format="PNG")

    # Inviare l'immagine ridimensionata tramite Telegram
    with open(resized_file, 'rb') as f:
        bot.send_photo(chat_id=chat_id, photo=f)



def get_aprs_data():
    # Simulazione chiamata API APRS
    url = f"https://api.aprs.fi/api/get?what=loc&apikey={APRS_API_KEY}&format=json"
    response = requests.get(url).json()
    # Estrarre i dati pertinenti
    return [{'name': entry['name'], 'lat': float(entry['lat']), 'lon': float(entry['lng'])}
            for entry in response.get('entries', [])]

# Aggiungi gestori al dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_handler(CommandHandler("add_member", add_member))

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
