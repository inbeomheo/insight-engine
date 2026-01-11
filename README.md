# AI 블로그 포스트 생성기 설치 및 사용 가이드

## 프로그램 소개
**AI 블로그 포스트 생성기**는 YouTube 영상 또는 웹페이지 URL을 입력하면, Google Gemini AI를 활용하여 고품질 블로그 포스트를 자동으로 생성해주는 웹 애플리케이션입니다.

- 다양한 Gemini 모델(2.5 Pro, Flash 등) 선택 지원
- 여러 URL을 한 번에 입력해 배치 생성 가능
- 생성된 결과 복사 및 재생성(리제너레이트) 기능
- 직관적인 UI, 다크모드 지원

---

## 설치 및 실행 방법

### 1. 필수 프로그램 설치
- Python 3.8 이상 버전 설치 (https://www.python.org/downloads/)

### 2. 프로그램 실행 준비
1. 압축 파일을 풉니다.
2. 명령 프롬프트(cmd)에서 해당 폴더로 이동합니다.
3. 아래 명령어로 필요한 패키지를 설치합니다:
   ```bash
   pip install -r requirements.txt
   ```
※ beautifulsoup4, requests 등도 requirements.txt에 포함되어 있습니다.

### 3. API 키 설정
- `.env` 파일을 프로젝트 루트에 생성하고 아래와 같이 본인의 API 키를 입력합니다:
  ```env
  GENAI_API_KEY=발급받은-Gemini-API-키
  YOUTUBE_API_KEY=발급받은-YouTube-API-키
  ```
※ 개발 편의를 위해 config.py에 키가 하드코딩되어 있지만, 실제 배포/공유 시에는 반드시 .env 파일을 사용하여 키를 보호하세요.

### 4. 프로그램 실행
1. 명령 프롬프트에서 실행:
   ```bash
   python app.py
   ```
2. 웹 브라우저에서 접속:
   - http://localhost:5000 으로 접속

## API 키 발급 방법

### Gemini API 키 발급
1. https://makersuite.google.com/app/apikey 방문
2. API 키 생성

### YouTube API 키 발급
1. https://console.cloud.google.com/ 방문
2. 새 프로젝트 생성
3. YouTube Data API v3 활성화
4. 사용자 인증 정보에서 API 키 생성

## 주의사항
- API 키는 절대 공개하거나 공유하지 마세요
- 각자의 컴퓨터에서 개별적으로 API 키를 설정해야 합니다

## 폴더 구조
```
AI-블로그-포스트-생성기/
├── app.py                # 메인 Flask 앱
├── config.py             # 환경설정 및 API 키 관리
├── requirements.txt      # 의존성 패키지 목록
├── static/               # JS, CSS, 이미지 등 정적 파일
│   └── js/
│       └── main.js
├── templates/            # HTML 템플릿
│   └── index.html
├── routes/               # Flask 블루프린트 라우트
│   └── blog_routes.py
├── services/             # AI/콘텐츠 처리 서비스 모듈
│   ├── ai_service.py
│   └── content_service.py
├── .env                  # (직접 생성) API 키 파일
└── ...
```

## 자주 묻는 질문(FAQ) 및 문제 해결
- 실행 오류 발생 시:
  1. Python 3.8 이상이 설치되어 있는지 확인
  2. `pip install -r requirements.txt`로 모든 패키지가 정상 설치되었는지 확인
  3. .env 파일 또는 config.py에 API 키가 올바르게 입력되었는지 확인
  4. 명령 프롬프트를 관리자 권한으로 실행해보기
  5. 포트 충돌 시 기존 5000번 포트 사용 중인 프로세스 종료
- AI 키 오류 또는 모델 선택 오류:
  - Gemini/YouTube API 키가 유효한지, 사용량 제한에 걸리지 않았는지 확인
  - 지원 모델명(gemini-2.5-pro, gemini-2.5-flash 등) 중 하나를 선택
- 네트워크 문제:
  - 인터넷 연결 상태 확인
  - 방화벽/프록시 환경에서는 외부 API 접근이 차단될 수 있음

도움이 필요하면 이슈를 등록해 주세요!
