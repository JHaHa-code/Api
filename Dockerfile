FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libxshmfence-dev \
    fonts-noto-color-emoji \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt ./ 
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Chrome and Chromedriver
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && apt-get -y --fix-broken install \
    && rm google-chrome-stable_current_amd64.deb

# Install ChromeDriver
RUN wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Add the script to run the Flask app
COPY . .

EXPOSE 5000
CMD ["python", "app.py"]
