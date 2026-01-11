import os
import subprocess
import sys

def build_exe():
    """PyInstaller를 사용하여 EXE 파일을 생성합니다."""
    # 현재 디렉토리 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 로봇 아이콘 경로
    icon_path = os.path.join(current_dir, "robot_icon.ico")
    
    sep = ';' if sys.platform == 'win32' else ':'

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        f"--icon={icon_path}",
        "--name=스마트콘텐츠생성기",
        f"--add-data=templates{sep}templates",
        f"--add-data=static{sep}static",
        "--hidden-import=flask",
        "--hidden-import=werkzeug",
        "--hidden-import=google.generativeai",
        "--hidden-import=markdown",
        "--hidden-import=dotenv",
        "run_app_hidden.py"
    ]
    
    try:
        # PyInstaller 실행
        print("빌드 시작 중...")
        subprocess.run(pyinstaller_cmd, cwd=current_dir, check=True)
        print("\n빌드 완료! dist 폴더에서 EXE 파일을 확인하세요.")
        
    except subprocess.CalledProcessError as e:
        print(f"빌드 중 오류 발생: {e}")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")

if __name__ == "__main__":
    build_exe()
