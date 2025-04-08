from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re
import threading
import os
import traceback

app = Flask(__name__)

CHROME_PATH = os.getenv("CHROME_PATH", "/usr/bin/chromium")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

driver_lock = threading.Lock()

def log(msg):
    print(f"[LOG] {msg}")

def init_driver():
    log("Initializing Chrome driver...")
    try:
        chrome_options = Options()
        chrome_options.binary_location = CHROME_PATH
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        service = Service(executable_path=CHROMEDRIVER_PATH)
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        log(f"Driver init failed: {e}")
        traceback.print_exc()
        return None

def check_for_timetable_class(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    timetable = soup.find('table', {'class': 'timetable'})
    if timetable:
        return True
    tables = soup.find_all(lambda tag: tag.name == 'table' and tag.get('class') and 'timetable' in ' '.join(tag.get('class')))
    return bool(tables)

def extract_timetable_data_by_class(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    timetable = soup.find('table', {'class': 'timetable'})
    if not timetable:
        tables = soup.find_all(lambda tag: tag.name == 'table' and tag.get('class') and 'timetable' in ' '.join(tag.get('class')))
        if tables:
            timetable = tables[0]
    if not timetable:
        return []

    timetable_data = []
    rows = timetable.find_all('tr')
    headers = [th.get_text(strip=True) for th in (rows[0].find_all('th') or rows[0].find_all('td'))]

    for row in rows[1:]:
        columns = row.find_all('td')
        if not columns:
            continue
        period = columns[0].get_text(strip=True)
        subjects = [re.sub(r'\s+', ' ', col.get_text(strip=True)) for col in columns[1:]]
        timetable_data.append({'period': period, 'subjects': subjects})
    return timetable_data

@app.route('/api/timetable', methods=['POST'])
def get_timetable():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "아이디와 비밀번호를 제공해주세요."}), 400

    username = data['username']
    password = data['password']
    log(f"요청 수신: username={username}")

    with driver_lock:
        driver = init_driver()
        if not driver:
            return jsonify({"success": False, "message": "브라우저 초기화에 실패했습니다."}), 500

        try:
            driver.get("https://hb.sjedu.net/login_st.php")
            time.sleep(2)

            input_fields = driver.find_elements(By.TAG_NAME, "input")
            id_field = pw_field = login_button = None

            for field in input_fields:
                field_type = field.get_attribute("type")
                field_name = field.get_attribute("name")
                if field_type == "text":
                    id_field = field
                elif field_type == "password":
                    pw_field = field
                elif field_type in ["submit", "button"] and "로그인" in (field.get_attribute("value") or ""):
                    login_button = field

            if id_field and pw_field:
                id_field.clear()
                id_field.send_keys(username)
                pw_field.clear()
                pw_field.send_keys(password)
                if login_button:
                    login_button.click()
                else:
                    pw_field.submit()

                time.sleep(3)

                if "로그아웃" not in driver.page_source:
                    log("로그인 실패")
                    return jsonify({"success": False, "message": "로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요."}), 401
            else:
                log("로그인 폼 못 찾음")
                return jsonify({"success": False, "message": "로그인 폼을 찾을 수 없습니다."}), 500

            driver.get("https://hb.sjedu.net/index_view.php")
            time.sleep(2)

            urls = [
                "https://hb.sjedu.net/edusel2/stu_timetable_view.php",
                "https://hb.sjedu.net/edusel2/timetable.php",
                "https://hb.sjedu.net/timetable.php",
                "https://hb.sjedu.net/edusel2/stu_timetable.php",
                "https://hb.sjedu.net/stu_timetable.php"
            ]

            timetable_found = False
            for url in urls:
                driver.get(url)
                time.sleep(2)
                if check_for_timetable_class(driver):
                    log(f"시간표 발견: {url}")
                    timetable_found = True
                    break

            if not timetable_found:
                return jsonify({"success": False, "message": "시간표를 찾을 수 없습니다."}), 404

            timetable_data = extract_timetable_data_by_class(driver)
            if timetable_data:
                return jsonify({"success": True, "data": timetable_data, "message": "시간표를 성공적으로 가져왔습니다."})
            else:
                return jsonify({"success": False, "message": "시간표 데이터를 추출하는 데 실패했습니다."}), 500

        except Exception as e:
            log(f"에러 발생: {e}")
            traceback.print_exc()
            return jsonify({"success": False, "message": "시간표 추출 중 오류가 발생했습니다."}), 500
        finally:
            driver.quit()
            log("드라이버 종료됨")

@app.route('/')
def index():
    return """
    <h1>화봉고 시간표 API</h1>
    <p>POST /api/timetable 에 JSON 형식으로 요청을 보내주세요.</p>
    <p>요청 예시: {"username": "아이디", "password": "비밀번호"}</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
