from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import threading
import re

app = Flask(__name__)
driver_lock = threading.Lock()

def check_for_timetable_class(page_content):
    """timetable 클래스를 가진 테이블이 있는지 확인"""
    soup = BeautifulSoup(page_content, 'html.parser')
    timetable = soup.find('table', {'class': 'timetable'})
    if timetable:
        print("timetable 클래스를 가진 테이블 발견!")
        return True
    tables = soup.find_all(lambda tag: tag.name == 'table' and 
                                      tag.get('class') and 
                                      'timetable' in ' '.join(tag.get('class')))
    if tables:
        print(f"{len(tables)}개의 timetable 관련 테이블 발견!")
        return True
    print("시간표 테이블 없음")
    return False

def extract_timetable_data(page_content):
    soup = BeautifulSoup(page_content, 'html.parser')
    timetable = soup.find('table', {'class': 'timetable'})
    if not timetable:
        tables = soup.find_all(lambda tag: tag.name == 'table' and 
                                          tag.get('class') and 
                                          'timetable' in ' '.join(tag.get('class')))
        if tables:
            timetable = tables[0]
    if not timetable:
        return []

    rows = timetable.find_all('tr')
    timetable_data = []
    headers = [th.get_text(strip=True) for th in (rows[0].find_all('th') or rows[0].find_all('td'))]
    print(f"헤더: {headers}")
    
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

    with driver_lock:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto("https://hb.sjedu.net/login_st.php", timeout=15000)
                page.fill('input[name="id"]', username)
                page.fill('input[name="passwd"]', password)
                page.click('input[type="submit"]')
                page.wait_for_timeout(2000)

                if "로그아웃" not in page.content():
                    return jsonify({"success": False, "message": "로그인에 실패했습니다. 아이디/비번 확인"}), 401
                print("로그인 성공!")

                page.goto("https://hb.sjedu.net/index_view.php", timeout=10000)
                time.sleep(1)

                timetable_found = False

                # 링크 클릭 방식
                links = page.query_selector_all("a")
                for link in links:
                    text = (link.inner_text() or "").strip()
                    href = (link.get_attribute("href") or "").lower()
                    if "시간표" in text or "timetable" in href:
                        print(f"시간표 링크 클릭: {text}")
                        link.click()
                        page.wait_for_timeout(2000)
                        if check_for_timetable_class(page.content()):
                            timetable_found = True
                            break

                # URL 직접 시도
                if not timetable_found:
                    candidate_urls = [
                        "https://hb.sjedu.net/edusel2/stu_timetable_view.php",
                        "https://hb.sjedu.net/edusel2/timetable.php",
                        "https://hb.sjedu.net/timetable.php",
                        "https://hb.sjedu.net/edusel2/stu_timetable.php",
                        "https://hb.sjedu.net/stu_timetable.php"
                    ]
                    for url in candidate_urls:
                        print(f"URL 직접 접근 시도: {url}")
                        page.goto(url)
                        page.wait_for_timeout(2000)
                        if check_for_timetable_class(page.content()):
                            timetable_found = True
                            break

                if not timetable_found:
                    return jsonify({"success": False, "message": "시간표를 찾을 수 없습니다."}), 404

                data = extract_timetable_data(page.content())
                if data:
                    return jsonify({"success": True, "data": data, "message": "시간표 가져오기 성공"})
                else:
                    return jsonify({"success": False, "message": "시간표 추출 실패"}), 500

            except Exception as e:
                print(f"오류 발생: {e}")
                return jsonify({"success": False, "message": "처리 중 오류 발생"}), 500
            finally:
                context.close()
                browser.close()

@app.route('/')
def index():
    return """
    <h1>화봉고 시간표 API (Playwright)</h1>
    <p>POST /api/timetable 에 JSON 형식으로 요청을 보내세요.</p>
    <p>{"username": "아이디", "password": "비밀번호"}</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
