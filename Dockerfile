# Usa un'immagine Python con supporto per Chrome
FROM python:3.11-slim

# Installa Chromium e il WebDriver
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file del progetto
COPY . .

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando di avvio del bot
CMD ["python", "bot.py"]
