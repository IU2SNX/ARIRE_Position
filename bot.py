import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import requests
import folium

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

def generate_map(chat_id):
    # Esempio di dati APRS
    aprs_data = get_aprs_data()

    # Creare la mappa
    m = folium.Map(location=[45.4642, 9.19], zoom_start=13)
    for member in aprs_data:
        folium.Marker([member['lat'], member['lon']], popup=member['name']).add_to(m)

    # Salvare la mappa
    m.save("map.html")
    # Per inviare l'immagine statica, è necessario convertire map.html in PNG usando uno strumento esterno.

def get_aprs_data():
    # Simulazione chiamata API APRS
    url = f"https://api.aprs.fi/api/get?what=loc&apikey={APRS_API_KEY}&format=json"
    response = requests.get(url).json()
    # Estrarre i dati pertinenti
    return [{'name': entry['name'], 'lat': float(entry['lat']), 'lon': float(entry['lng'])}
            for entry in response.get('entries', [])]

# Setup del bot
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Il token del bot non è definito. Controlla le variabili di ambiente.")

    from telegram.ext import Updater
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(CommandHandler("add_member", add_member))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
