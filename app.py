from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re
import threading

app = Flask(__name__)

# Chrome options setup for headless Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--window-size=1920,1080")

# Thread-safe driver initialization
driver_lock = threading.Lock()

def init_driver():
    try:
        print("Initializing Chrome driver..")
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        return None

def check_for_timetable_class(driver, debug_folder=None):
    page_source = driver.page_source
    if debug_folder:
        with open(f"{debug_folder}/current_page.html", "w", encoding="utf-8") as f:
            f.write(page_source)
    soup = BeautifulSoup(page_source, 'html.parser')
    timetable = soup.find('table', {'class': 'timetable'})
    if timetable:
        print("Found timetable class!")
        return True
    tables_with_timetable_class = soup.find_all(lambda tag: tag.name == 'table' and 'timetable' in ' '.join(tag.get('class', [])))
    if tables_with_timetable_class:
        print(f"Found {len(tables_with_timetable_class)} tables with timetable class!")
        return True
    print("Could not find timetable class")
    return False

def extract_timetable_data_by_class(driver):
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    timetable = soup.find('table', {'class': 'timetable'})
    if not timetable:
        tables = soup.find_all(lambda tag: tag.name == 'table' and 'timetable' in ' '.join(tag.get('class', [])))
        if tables:
            timetable = tables[0]
    if not timetable:
        print("No timetable class found")
        return []
    
    timetable_data = []
    rows = timetable.find_all('tr')
    header_row = rows[0]
    headers = [th.get_text(strip=True) for th in (header_row.find_all('th') or header_row.find_all('td'))]
    print(f"Headers: {headers}")

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
        return jsonify({"success": False, "message": "Please provide both username and password."}), 400
    username = data['username']
    password = data['password']

    with driver_lock:
        driver = init_driver()
        if not driver:
            return jsonify({"success": False, "message": "Failed to initialize browser."}), 500
        
        try:
            driver.get("https://hb.sjedu.net/login_st.php")
            print("Login page loaded")
            time.sleep(2)
            input_fields = driver.find_elements(By.TAG_NAME, "input")
            id_field = next((field for field in input_fields if field.get_attribute("type") == "text"), None)
            pw_field = next((field for field in input_fields if field.get_attribute("type") == "password"), None)
            login_button = next((field for field in input_fields if field.get_attribute("type") in ("submit", "button") and "로그인" in (field.get_attribute("value") or "")), None)
            
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
                    return jsonify({"success": False, "message": "Login failed. Check your username and password."}), 401
                print("Login successful!")
            else:
                return jsonify({"success": False, "message": "Could not find login form."}), 500

            driver.get("https://hb.sjedu.net/index_view.php")
            print("Navigated to main page")
            time.sleep(2)

            timetable_found = False
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                link_text = link.text.strip()
                if "시간표" in link_text or "timetable" in link.get_attribute("href").lower():
                    print(f"Found timetable link: {link_text}")
                    link.click()
                    time.sleep(2)
                    if check_for_timetable_class(driver):
                        timetable_found = True
                        break

            if not timetable_found:
                possible_urls = [
                    "https://hb.sjedu.net/edusel2/stu_timetable_view.php",
                    "https://hb.sjedu.net/edusel2/timetable.php",
                    "https://hb.sjedu.net/timetable.php"
                ]
                for url in possible_urls:
                    driver.get(url)
                    time.sleep(2)
                    if check_for_timetable_class(driver):
                        timetable_found = True
                        break
            
            if not timetable_found:
                return jsonify({"success": False, "message": "Could not find timetable."}), 404

            timetable_data = extract_timetable_data_by_class(driver)
            if timetable_data:
                return jsonify({"success": True, "data": timetable_data, "message": "Timetable successfully retrieved."})
            else:
                return jsonify({"success": False, "message": "Failed to extract timetable data."}), 500

        except Exception as e:
            print(f"Error during timetable extraction: {e}")
            return jsonify({"success": False, "message": "An error occurred while extracting the timetable."}), 500
        finally:
            driver.quit()
            print("Chrome driver closed")

@app.route('/')
def index():
    return """
    <h1>화봉고 시간표 API</h1>
    <p>POST /api/timetable 에 JSON 형식으로 요청을 보내주세요.</p>
    <p>요청 형식: {"username": "아이디", "password": "비밀번호"}</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
