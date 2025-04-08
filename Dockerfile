FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 필수 패키지 설치 (playwright 돌릴 때 필요)
RUN apt-get update && \
    apt-get install -y wget curl unzip gnupg libglib2.0-0 libnss3 libgdk-pixbuf2.0-0 libgtk-3-0 libxss1 libasound2 libxcomposite1 libxrandr2 libxdamage1 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 libxshmfence1 libgbm1 libxext6 libxfixes3 libxrender1 libfontconfig1 libxcursor1 && \
    apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

RUN playwright install --with-deps

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
