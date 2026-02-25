FROM python:3.11-slim-bullseye

# تثبيت التبعيات الأساسية للنظام
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
CMD ["python", "ivasms_bot_TG.py"]
