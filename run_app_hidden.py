import os
import sys
import subprocess
import webbrowser
import time
import threading
import traceback
import logging
from werkzeug.serving import make_server

# 로그 설정
def _get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


log_file = os.path.join(_get_app_dir(), 'app_error.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

HEARTBEAT_TTL_SECONDS = 15
IDLE_SHUTDOWN_SECONDS = 25

def open_browser():
    """브라우저를 열어 웹앱에 접속합니다."""
    try:
        time.sleep(2)  # 서버가 시작될 때까지 잠시 대기
        webbrowser.open('http://127.0.0.1:5000')
        logging.info("브라우저가 열렸습니다.")
    except Exception as e:
        logging.error(f"브라우저 열기 실패: {e}")
        traceback.print_exc(file=open(log_file, 'a'))

def run_flask_app():
    """Flask 앱을 백그라운드에서 실행합니다."""
    try:
        current_dir = _get_app_dir()
        logging.info(f"현재 디렉토리: {current_dir}")
        
        # 브라우저 자동 열기 스레드 시작
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        logging.info("Flask 앱 시작 중...")

        from app import app
        from routes import blog_routes

        server = make_server('127.0.0.1', 5000, app)

        def _monitor_idle_shutdown():
            had_client = False
            last_active = time.time()
            while True:
                now = time.time()
                tracker = blog_routes._CLIENT_TRACKER
                active = any((now - ts) <= HEARTBEAT_TTL_SECONDS for ts in list(tracker.values()))
                if active:
                    had_client = True
                    last_active = now
                else:
                    if had_client and (now - last_active) >= IDLE_SHUTDOWN_SECONDS:
                        logging.info("No active browser clients. Shutting down server.")
                        try:
                            server.shutdown()
                        except Exception as e:
                            logging.error(f"서버 종료 실패: {e}")
                        break
                time.sleep(1)

        t = threading.Thread(target=_monitor_idle_shutdown, daemon=True)
        t.start()
        server.serve_forever()
        
    except Exception as e:
        logging.error(f"앱 실행 중 오류 발생: {e}")
        traceback.print_exc(file=open(log_file, 'a'))
        print(f"오류 발생: {e}")
        input("계속하려면 아무 키나 누르세요...")

if __name__ == "__main__":
    try:
        logging.info("애플리케이션 시작")
        run_flask_app()
    except Exception as e:
        logging.error(f"메인 실행 오류: {e}")
        traceback.print_exc(file=open(log_file, 'a'))
        print(f"오류 발생: {e}")
        input("계속하려면 아무 키나 누르세요...")
