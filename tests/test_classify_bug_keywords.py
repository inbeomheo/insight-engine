"""classify_message bug 키워드 보강 검증 (cycle 5 — cycle 2에서 발견한 분류 결함).

"안 눌려요"/"안 열려요" 같은 흔한 "안 된다" 버그 표현이 question으로
빠지던 문제를 해결한다.
"""
import pytest

from services.support.feedback_triage_service import classify_message


@pytest.mark.parametrize(
    "message",
    [
        "버튼이 안 눌려요",
        "파일이 안 열려요",
        "다운로드 버튼 안 눌림",
        "링크가 안 열려요",
    ],
)
def test_negated_action_classified_as_bug(message):
    # 흔한 "안 된다" 버그 표현이 question으로 빠지지 않아야 한다.
    assert classify_message(message)["kind"] == "bug"


def test_question_not_affected():
    assert classify_message("퓨전 분석이 뭐야?")["kind"] == "question"
    assert classify_message("사용법 알려줘")["kind"] == "question"


def test_existing_bug_keywords_still_work():
    assert classify_message("결제 화면에서 에러가 나요")["kind"] == "bug"
    assert classify_message("로그인이 안 돼요")["kind"] == "bug"


def test_usability_not_regressed():
    # 잘림/불편은 usability 유지 (bug로 오분류되면 안 됨)
    assert classify_message("모바일에서 메뉴가 잘려요")["kind"] == "usability"
    assert classify_message("화면이 불편해요")["kind"] == "usability"
