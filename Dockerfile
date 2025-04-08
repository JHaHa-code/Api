# 베이스 이미지
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    fonts-nanum \
    libglib2.0-0 \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libasound2 \
    libxshmfence1 \
    libxrandr2 \
    libgbm1 \
    libu2f-udev \
    xdg-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 복사 및 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 설치 (브라우저 포함)
RUN playwright install --with-deps

# 앱 파일 복사
COPY . .

# 서버 실행
CMD ["python", "app.py"]
