import os
import logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route("/")
def index():
    return "Timetable API is running."

@app.route("/api/timetable", methods=["POST"])
def get_timetable():
    data = request.get_json()
    userid = data.get("userid")
    passwd = data.get("passwd")

    if not userid or not passwd:
        return jsonify({"error": "Missing userid or passwd"}), 400

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            logging.info("접속 시도 중...")
            page.set_default_timeout(30000)
            page.goto("https://hb.sjedu.net/login_st.php", wait_until="load")

            page.fill('input[name="userid"]', userid)
            page.fill('input[name="passwd"]', passwd)
            page.click('input[type="submit"]')
            page.wait_for_timeout(2000)

            logging.info("로그인 성공 후 시간표 페이지로 이동 시도 중...")
            page.goto("https://hb.sjedu.net/st/st_schedule.php", wait_until="load")
            page.wait_for_timeout(1000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            timetable = soup.select_one("table")

            return jsonify({"html": timetable.prettify() if timetable else "시간표 테이블 없음"})
        except Exception as e:
            logging.exception("에러 발생:")
            return jsonify({"error": str(e)}), 500
        finally:
            browser.close()