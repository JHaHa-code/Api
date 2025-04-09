# Python 3.10-slim 이미지를 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필수 라이브러리 설치
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

# 필요 라이브러리 설치
COPY requirements.txt ./ 
RUN pip install --upgrade pip && pip install -r requirements.txt

# 구글 크롬 설치
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && apt-get -y --fix-broken install \
    && rm google-chrome-stable_current_amd64.deb

# ChromeDriver 설치 (버전 수정)
RUN wget https://chromedriver.storage.googleapis.com/135.0.0/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Flask 애플리케이션 코드 복사
COPY . .

# 5000 포트 개방
EXPOSE 5000

# 애플리케이션 실행
CMD ["python", "app.py"]
