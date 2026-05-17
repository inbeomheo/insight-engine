"""NPS feedback request service tests."""

from services.platform.nps_feedback_service import build_nps_feedback_response


def test_build_nps_feedback_response_accepts_valid_score_and_user():
    payload, status = build_nps_feedback_response(
        {"score": "8", "feedback": "useful"},
        user_id="user-1",
    )

    assert status == 200
    assert payload == {
        "success": True,
        "user_id": "user-1",
        "score": 8,
        "feedback": "useful",
    }


def test_build_nps_feedback_response_defaults_feedback_and_user():
    payload, status = build_nps_feedback_response({"score": 0})

    assert status == 200
    assert payload == {
        "success": True,
        "user_id": "anonymous",
        "score": 0,
        "feedback": "",
    }


def test_build_nps_feedback_response_rejects_missing_score():
    payload, status = build_nps_feedback_response({})

    assert status == 400
    assert payload == {"error": "score\ub294 0~10 \uc0ac\uc774\uc5ec\uc57c \ud569\ub2c8\ub2e4."}


def test_build_nps_feedback_response_rejects_out_of_range_score():
    payload, status = build_nps_feedback_response({"score": 11})

    assert status == 400
    assert payload == {"error": "score\ub294 0~10 \uc0ac\uc774\uc5ec\uc57c \ud569\ub2c8\ub2e4."}


def test_build_nps_feedback_response_rejects_non_numeric_score():
    payload, status = build_nps_feedback_response({"score": "bad"})

    assert status == 400
    assert payload == {"error": "score\ub294 0~10 \uc0ac\uc774\uc5ec\uc57c \ud569\ub2c8\ub2e4."}
