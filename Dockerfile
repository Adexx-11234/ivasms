FROM python:3.11-slim-bullseye

# تثبيت التبعيات الأساسية للنظام والمتصفح
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    curl \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libgbm1 \
    libasound2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# تثبيت Google Chrome المستقر
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# تعيين متغيرات البيئة لـ Chrome
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV PYTHONUNBUFFERED=1

CMD ["python", "ivasms_bot_TG.py"]
