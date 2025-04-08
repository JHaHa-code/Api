FROM python:3.10

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-nanum \
    libglib2.0-0 \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libatk1.0-0 \
    libx11-6 \
    libxext6 \
    libxfixes3 \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# 프로젝트 복사
WORKDIR /app
COPY . .

# 파이썬 패키지 설치
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Playwright 설치 및 브라우저 다운로드
RUN pip install playwright
RUN playwright install --with-deps

# 서버 실행
CMD ["python", "app.py"]
