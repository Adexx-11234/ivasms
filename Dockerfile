FROM python:3.9-slim

# تثبيت المتطلبات
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# تثبيت Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# تثبيت undetected-chromedriver (هو نفسه هيدير ChromeDriver)
RUN pip install undetected-chromedriver==3.5.4

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DISPLAY=:99

CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 & python ivasms_bot_TG.py"]
