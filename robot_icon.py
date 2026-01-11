import requests
import os

def download_robot_icon():
    # 로봇 아이콘 URL (무료 아이콘)
    icon_url = "https://cdn-icons-png.flaticon.com/512/4712/4712027.png"
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robot_icon.ico")
    
    # 아이콘 파일이 없을 경우에만 다운로드
    if not os.path.exists(icon_path):
        try:
            response = requests.get(icon_url)
            if response.status_code == 200:
                with open(icon_path, 'wb') as f:
                    f.write(response.content)
                print("로봇 아이콘이 다운로드되었습니다.")
            else:
                print(f"아이콘 다운로드 실패: {response.status_code}")
        except Exception as e:
            print(f"아이콘 다운로드 중 오류 발생: {e}")
    
    return icon_path

if __name__ == "__main__":
    download_robot_icon()
