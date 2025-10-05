# APP/backend/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps for Chromium + chromedriver + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver \
    curl unzip gnupg ca-certificates fonts-liberation \
    libasound2 libnss3 libx11-6 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxi6 libxrandr2 libgbm1 libxkbcommon0 libxshmfence1 libatk-bridge2.0-0 libgtk-3-0 \
    libdrm2 libxext6 libxtst6 libu2f-udev xvfb \
 && rm -rf /var/lib/apt/lists/*

# App files
WORKDIR /app
COPY backend/ /app/
COPY Scraper/ /app/Scraper/

# Python deps (your combined requirements)
RUN pip install --no-cache-dir -r requirement.txt

# Render provides $PORT; run Flask directly (your app binds to $PORT)
CMD ["python", "app.py"]
