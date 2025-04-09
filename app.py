from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re
import os
import json
from datetime import datetime
import threading
app = Flask(__name__)
# Chrome 드라이버 설정 (전역으로 한 번만 로드)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--window-size=1920,1080")
# Chrome 드라이버 초기화
driver_lock = threading.Lock()
def init_driver():
    try:
        print("Initializing Chrome driver..")
        return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Chrome 드라이버 초기화 오류: {e}")
        return None
def check_for_timetable_class(driver, debug_folder=None):
    """timetable 클래스를 가진 테이블이 있는지 확인"""
    page_source = driver.page_source
    # 디버깅용 HTML 저장
    if debug_folder:
        with open(f"{debug_folder}/current_page.html", "w", encoding="utf-8") as f:
            f.write(page_source)
    # BeautifulSoup으로 파싱
    soup = BeautifulSoup(page_source, 'html.parser')
    # timetable 클래스를 가진 테이블 찾기
    timetable = soup.find('table', {'class': 'timetable'})
    if timetable:
        print("timetable 클래스를 가진 테이블 발견!")
        return True
    # 클래스 이름에 timetable이 포함된 테이블 찾기
    tables_with_timetable_class = soup.find_all(lambda tag: tag.name == 'table' and 
                                              tag.get('class') and 
                                              'timetable' in ' '.join(tag.get('class')))
    if tables_with_timetable_class:
        print(f"{len(tables_with_timetable_class)}개의 timetable 관련 클래스를 가진 테이블 발견!")
        return True
    print("timetable 클래스를 가진 테이블을 찾을 수 없음")
    return False
def extract_timetable_data_by_class(driver):
    """timetable 클래스를 가진 테이블에서 데이터 추출"""
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    # timetable 클래스를 가진 테이블 찾기
    timetable = soup.find('table', {'class': 'timetable'})
    # 클래스 이름에 timetable이 포함된 테이블 찾기
    if not timetable:
        tables = soup.find_all(lambda tag: tag.name == 'table' and 
                              tag.get('class') and 
                              'timetable' in ' '.join(tag.get('class')))
        if tables:
            timetable = tables[0]
    if not timetable:
        print("timetable 클래스를 가진 테이블을 찾을 수 없음")
        return []
    # 시간표 데이터 추출
    timetable_data = []
    rows = timetable.find_all('tr')
    # 헤더 확인
    header_row = rows[0]
    headers = [th.get_text(strip=True) for th in (header_row.find_all('th') or header_row.find_all('td'))]
    print(f"헤더: {headers}")
    # 데이터 행 처리
    for row in rows[1:]:
        columns = row.find_all('td')
        if not columns:
            continue
        # 교시 추출
        period = columns[0].get_text(strip=True)
        # 각 요일별 과목 추출
        subjects = []
        for col in columns[1:]:
            subject_text = col.get_text(strip=True)
            # 불필요한 문자 정리
            subject_text = re.sub(r'\s+', ' ', subject_text)
            subjects.append(subject_text)
        timetable_data.append({
            'period': period,
            'subjects': subjects
        })
    return timetable_data
@app.route('/api/timetable', methods=['POST'])
def get_timetable():
    """
    시간표 데이터를 가져오는 API 엔드포인트
    요청 형식: JSON { "username": "아이디", "password": "비밀번호" }
    응답 형식: JSON { "success": boolean, "data": 시간표 데이터, "message": "상태 메시지" }
    """
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({
            "success": False,
            "message": "아이디와 비밀번호를 제공해주세요."
        }), 400
    username = data['username']
    password = data['password']
    # 드라이버 초기화
    with driver_lock:
        driver = init_driver()
        if not driver:
            return jsonify({
                "success": False,
                "message": "브라우저 초기화에 실패했습니다."
            }), 500
        try:
            # 로그인 페이지로 이동
            driver.get("https://hb.sjedu.net/login_st.php")
            print("로그인 페이지를 로드했습니다")
            time.sleep(2)
            # 로그인 시도
            try:
                input_fields = driver.find_elements(By.TAG_NAME, "input")
                id_field = None
                pw_field = None
                login_button = None
                for field in input_fields:
                    field_type = field.get_attribute("type")
                    field_name = field.get_attribute("name")
                    if field_type == "text" and field_name:
                        id_field = field
                    elif field_type == "password" and field_name:
                        pw_field = field
                    elif field_type == "submit" or (field_type == "button" and "로그인" in (field.get_attribute("value") or "")):
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
                    print("login 요청 전송됨")
                    time.sleep(3)
                    # 로그인 성공 확인
                    if "로그아웃" not in driver.page_source:
                        return jsonify({
                            "success": False,
                            "message": "로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요."
                        }), 401
                    print("로그인 성공!")
                else:
                    return jsonify({
                        "success": False,
                        "message": "로그인 폼을 찾을 수 없습니다."
                    }), 500
            except Exception as e:
                print(f"로그인 도중 오류 발생: {e}")
                return jsonify({
                    "success": False,
                    "message": "로그인 처리 중 오류가 발생했습니다."
                }), 500
            # 메인 페이지로 이동
            driver.get("https://hb.sjedu.net/index_view.php")
            print("메인 페이지로 이동")
            time.sleep(2)
            # 시간표 찾기 시도
            timetable_found = False
            # 방법 1: 시간표 관련 링크 찾기
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    if "시간표" in link_text or "timetable" in link_href.lower():
                        print(f"시간표 관련 링크 발견: {link_text}")
                        link.click()
                        time.sleep(2)
                        if check_for_timetable_class(driver):
                            timetable_found = True
                            break
            except Exception as e:
                print(f"시간표 링크 찾기 오류: {e}")
            # 방법 2: 직접 URL 접근
            if not timetable_found:
                possible_urls = [
                    "https://hb.sjedu.net/edusel2/stu_timetable_view.php",
                    "https://hb.sjedu.net/edusel2/timetable.php",
                    "https://hb.sjedu.net/timetable.php",
                    "https://hb.sjedu.net/edusel2/stu_timetable.php",
                    "https://hb.sjedu.net/stu_timetable.php"
                ]
                for url in possible_urls:
                    print(f"URL 시도: {url}")
                    driver.get(url)
                    time.sleep(2)
                    if check_for_timetable_class(driver):
                        timetable_found = True
                        break
            # 시간표를 찾지 못한 경우
            if not timetable_found:
                return jsonify({
                    "success": False,
                    "message": "시간표를 찾을 수 없습니다."
                }), 404
            # 시간표 데이터 추출
            timetable_data = extract_timetable_data_by_class(driver)
            if timetable_data:
                return jsonify({
                    "success": True,
                    "data": timetable_data,
                    "message": "시간표를 성공적으로 가져왔습니다."
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "시간표 데이터를 추출하는 데 실패했습니다."
                }), 500
        except Exception as e:
            print(f"시간표 추출 중 오류 발생: {e}")
            return jsonify({
                "success": False,
                "message": "시간표 추출 중 오류가 발생했습니다."
            }), 500
        finally:
            # 드라이버 종료
            driver.quit()
            print("Chrome 드라이버 종료됨")
@app.route('/')
def index():
    return """
    <h1>화봉고 시간표 API</h1>
    <p>POST /api/timetable 에 JSON 형식으로 요청을 보내주세요.</p>
    <p>요청 형식: {"username": "아이디", "password": "비밀번호"}</p>
    """
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
