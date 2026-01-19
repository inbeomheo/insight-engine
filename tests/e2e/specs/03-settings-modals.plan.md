# 설정 및 모달 테스트 플랜

## 개요
- **앱 URL**: http://localhost:5001
- **seed 파일**: seed.spec.ts
- **테스트 파일**: tests/settings-modals/

## 테스트 케이스

### Suite 1: 온보딩 모달

#### TC-1.1: 온보딩 모달 표시
**Steps:**
1. 앱 첫 방문 시 (localStorage 클리어)

**Expected:**
- 온보딩 모달 자동 표시
- 환영 메시지 및 안내 텍스트

#### TC-1.2: 온보딩 완료
**Steps:**
1. 온보딩 모달에서 시작하기 버튼 클릭

**Expected:**
- 모달 닫힘
- localStorage에 완료 상태 저장

#### TC-1.3: 재방문 시 모달 미표시
**Steps:**
1. 온보딩 완료 후 페이지 새로고침

**Expected:**
- 온보딩 모달 표시되지 않음

### Suite 2: 설정 모달

#### TC-2.1: 설정 모달 열기
**Steps:**
1. 사이드바의 설정 버튼 클릭

**Expected:**
- 설정 모달 표시
- API 키 입력 필드들 표시

#### TC-2.2: API 키 입력
**Steps:**
1. OpenAI API 키 입력 필드에 값 입력
2. 저장 버튼 클릭

**Expected:**
- 입력값 저장
- 성공 메시지 표시

#### TC-2.3: 모달 외부 클릭 닫기
**Steps:**
1. 설정 모달 열기
2. 모달 외부 (오버레이) 클릭

**Expected:**
- 모달 닫힘

#### TC-2.4: ESC 키로 닫기
**Steps:**
1. 설정 모달 열기
2. ESC 키 누름

**Expected:**
- 모달 닫힘

### Suite 3: 커스텀 스타일 모달

#### TC-3.1: 커스텀 스타일 모달 열기
**Steps:**
1. "나만의 스타일 만들기" 카드 클릭

**Expected:**
- 커스텀 스타일 모달 표시
- 스타일 이름, 설명 입력 필드

#### TC-3.2: 커스텀 스타일 저장
**Steps:**
1. 스타일 이름 입력
2. 프롬프트 입력
3. 저장 버튼 클릭

**Expected:**
- 새 스타일 카드 추가
- 모달 닫힘

### Suite 4: 모달 접근성

#### TC-4.1: 포커스 트랩
**Steps:**
1. 모달 열기
2. Tab 키로 포커스 순회

**Expected:**
- 포커스가 모달 내부에만 유지됨

#### TC-4.2: ARIA 속성 확인
**Steps:**
1. 모달 열기
2. ARIA 속성 검사

**Expected:**
- role="dialog"
- aria-modal="true"
- aria-labelledby 설정
