# URL 입력 및 관리 테스트 플랜

## 개요
- **앱 URL**: http://localhost:5001
- **seed 파일**: seed.spec.ts
- **테스트 파일**: tests/url-management/

## 테스트 케이스

### Suite 1: URL 입력

#### TC-1.1: 유효한 YouTube URL 입력
**Steps:**
1. 앱 접속
2. URL 입력 필드에 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 입력
3. Enter 키 누름

**Expected:**
- URL 카드가 URL 목록에 추가됨
- 입력 필드가 초기화됨
- URL 카드에 영상 정보 표시

#### TC-1.2: youtu.be 단축 URL 입력
**Steps:**
1. URL 입력 필드에 "https://youtu.be/dQw4w9WgXcQ" 입력
2. Enter 키 누름

**Expected:**
- URL 카드가 정상 추가됨

#### TC-1.3: 잘못된 URL 입력
**Steps:**
1. URL 입력 필드에 "invalid-url" 입력
2. Enter 키 누름

**Expected:**
- 에러 메시지 표시
- URL이 목록에 추가되지 않음

#### TC-1.4: 빈 입력
**Steps:**
1. URL 입력 필드가 비어있는 상태에서 Enter 키 누름

**Expected:**
- 아무 동작 없음 또는 안내 메시지

### Suite 2: URL 카드 관리

#### TC-2.1: URL 삭제
**Steps:**
1. URL 추가 후 삭제 버튼 클릭

**Expected:**
- URL 카드가 목록에서 제거됨
- 카운트 업데이트

#### TC-2.2: 최대 10개 URL 제한
**Steps:**
1. 11개의 URL 추가 시도

**Expected:**
- 10개 이후 추가 시 경고 메시지
- 11번째 URL 추가 거부

#### TC-2.3: 중복 URL 검증
**Steps:**
1. 동일한 URL을 두 번 추가 시도

**Expected:**
- 중복 경고 메시지
- 두 번째 추가 거부
