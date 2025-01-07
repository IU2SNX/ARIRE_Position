# Usa un'immagine Python con supporto per Chrome
FROM python:3.11-slim

# Installa le librerie di sistema necessarie
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file del progetto
COPY . .

# Aggiorna pip e installa le dipendenze Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Comando di avvio del bot
CMD ["python", "bot.py"]
