FROM python:3.10-slim

WORKDIR /app

# 필수 패키지 및 종속성 설치
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
    fonts-liberation \
    libvulkan1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt ./ 
RUN pip install --upgrade pip && pip install -r requirements.txt

# Chrome 설치
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && apt-get -y --fix-broken install \
    && rm google-chrome-stable_current_amd64.deb

# ChromeDriver 135.0.7049.84 버전 다운로드 및 설치
RUN wget https://chromedriver.storage.googleapis.com/135.0.7049.84/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Flask 앱 파일 복사
COPY . .

# Flask 앱 포트 열기
EXPOSE 5000

# Flask 앱 실행
CMD ["python", "app.py"]
