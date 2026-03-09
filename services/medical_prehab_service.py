"""
수술 전 준비(프리헵) 키트 서비스

시술 유형별 준비 체크리스트, 타임라인, FAQ를 생성합니다.
순수 파이썬, 규칙 기반. 의료 면책조항을 반드시 포함합니다.
"""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class PrehabStep:
    """준비 단계"""
    step_number: int
    category: str
    instruction: str
    timing: str


@dataclass
class TimelineItem:
    """타임라인 항목"""
    days_before: int
    action: str
    category: str


@dataclass
class PrehabKit:
    """수술 전 준비 키트"""
    procedure_type: str
    preparation_steps: List[PrehabStep]
    timeline: List[TimelineItem]
    checklist: List[str]
    warnings: List[str]
    faq: List[Dict[str, str]]


# 의료 면책조항 (모든 키트에 필수 포함)
_MEDICAL_DISCLAIMER = (
    "이 정보는 일반적인 참고용이며 의료 전문가의 조언을 대체하지 않습니다. "
    "반드시 담당 의료 전문가와 상담하세요."
)

# 시술 유형별 데이터 정의
_PROCEDURE_DATA = {
    "general": {
        "label": "일반 수술",
        "steps": [
            PrehabStep(1, "검사", "혈액 검사 및 기본 건강 검진 완료", "2주 전"),
            PrehabStep(2, "약물", "복용 중인 약물 목록을 의료진에게 제출", "2주 전"),
            PrehabStep(3, "금식", "수술 전날 자정부터 금식 (물 포함)", "전날"),
            PrehabStep(4, "위생", "수술 부위 청결 유지, 매니큐어/화장 제거", "당일"),
            PrehabStep(5, "준비물", "신분증, 보험증, 편한 옷 준비", "당일"),
            PrehabStep(6, "동행", "보호자 동행 확인 (마취 후 귀가 불가)", "당일"),
        ],
        "timeline": [
            TimelineItem(14, "건강 검진 및 혈액 검사", "검사"),
            TimelineItem(14, "복용 약물 목록 정리", "약물"),
            TimelineItem(7, "금주 및 금연 시작", "생활습관"),
            TimelineItem(3, "수술 전 주의사항 재확인", "확인"),
            TimelineItem(1, "자정부터 금식 시작", "금식"),
            TimelineItem(0, "수술 당일 — 편한 옷, 신분증 지참", "당일"),
        ],
        "checklist": [
            "혈액 검사 완료",
            "심전도 검사 완료",
            "복용 약물 의료진 통보",
            "수술 동의서 서명",
            "금식 확인 (8시간 이상)",
            "보호자 동행 확인",
            "귀중품 보관 확인",
            "편한 옷차림",
        ],
        "faq": [
            {"q": "금식은 언제부터 해야 하나요?", "a": "일반적으로 수술 전날 자정부터 음식과 물을 포함하여 금식합니다. 의료진의 구체적 지시를 따르세요."},
            {"q": "복용 중인 약을 수술 당일에도 먹어야 하나요?", "a": "혈압약 등 일부 약은 소량의 물로 복용할 수 있지만, 반드시 의료진에게 확인하세요. 혈액 희석제(아스피린 등)는 보통 1~2주 전 중단합니다."},
            {"q": "수술 후 언제 퇴원할 수 있나요?", "a": "수술 종류와 회복 상태에 따라 다릅니다. 당일 퇴원부터 수일 입원까지 다양하므로 담당 의료 전문가와 상담하세요."},
        ],
    },
    "dental": {
        "label": "치과 시술",
        "steps": [
            PrehabStep(1, "구강검사", "파노라마 X-ray 및 구강 상태 확인", "1주 전"),
            PrehabStep(2, "약물", "복용 중인 약물(특히 혈액 희석제) 의료진에게 알림", "1주 전"),
            PrehabStep(3, "구강위생", "시술 전 양치 및 구강 청결 유지", "당일"),
            PrehabStep(4, "식사", "시술 2시간 전 가벼운 식사 권장 (전신마취 시 금식)", "당일"),
            PrehabStep(5, "준비물", "신분증, 보험증 지참", "당일"),
        ],
        "timeline": [
            TimelineItem(7, "구강 검사 및 X-ray 촬영", "검사"),
            TimelineItem(7, "혈액 희석제 중단 여부 확인", "약물"),
            TimelineItem(3, "알레르기 정보 의료진 전달", "확인"),
            TimelineItem(1, "음주/흡연 자제", "생활습관"),
            TimelineItem(0, "양치 후 방문, 편한 옷차림", "당일"),
        ],
        "checklist": [
            "X-ray 촬영 완료",
            "알레르기 정보 전달",
            "혈액 희석제 관련 상담",
            "시술 동의서 서명",
            "당일 양치 완료",
        ],
        "faq": [
            {"q": "임플란트 시술 후 통증이 심한가요?", "a": "개인차가 있지만 보통 시술 후 2-3일간 약간의 통증과 붓기가 있습니다. 처방된 진통제를 복용하면 관리 가능합니다. 의료 전문가와 상담하세요."},
            {"q": "시술 후 식사는 언제부터 가능한가요?", "a": "마취가 풀린 후(보통 2-3시간) 부드러운 음식부터 시작하세요. 딱딱하거나 뜨거운 음식은 3-5일 피하는 것이 좋습니다."},
            {"q": "시술 당일 운전해도 되나요?", "a": "국소마취만 받은 경우 가능하지만, 진정 치료(수면 마취)를 받은 경우 반드시 보호자 동행이 필요합니다."},
        ],
    },
    "orthopedic": {
        "label": "정형외과 수술",
        "steps": [
            PrehabStep(1, "영상검사", "MRI 또는 CT 촬영 완료", "2주 전"),
            PrehabStep(2, "재활준비", "수술 후 재활 계획 의료진과 상담", "2주 전"),
            PrehabStep(3, "근력강화", "수술 부위 주변 근력 강화 운동 (의료진 지시하에)", "2주 전"),
            PrehabStep(4, "약물", "진통제/소염제 복용 중단 여부 확인", "1주 전"),
            PrehabStep(5, "보조기구", "목발, 보조기 등 필요 기구 사전 준비", "3일 전"),
            PrehabStep(6, "금식", "수술 전날 자정부터 금식", "전날"),
            PrehabStep(7, "준비", "편한 옷, 헐렁한 바지 착용", "당일"),
        ],
        "timeline": [
            TimelineItem(14, "MRI/CT 촬영 및 수술 전 검사", "검사"),
            TimelineItem(14, "프리헵 운동 프로그램 시작", "재활"),
            TimelineItem(7, "진통제/소염제 중단 확인", "약물"),
            TimelineItem(3, "목발/보조기 사전 준비", "준비물"),
            TimelineItem(1, "금식 시작, 수술 부위 제모(필요 시)", "금식"),
            TimelineItem(0, "편한 옷차림, 보호자 동행", "당일"),
        ],
        "checklist": [
            "MRI/CT 촬영 완료",
            "수술 전 혈액 검사 완료",
            "프리헵 운동 완료",
            "진통제 중단 확인",
            "목발/보조기 준비",
            "집 안 안전 점검 (미끄럼 방지 등)",
            "금식 확인",
            "보호자 동행 확인",
        ],
        "faq": [
            {"q": "수술 전 운동을 해야 하나요?", "a": "네, 프리헵(수술 전 재활)은 수술 후 회복을 빠르게 합니다. 의료진이 안내하는 운동을 2주 전부터 꾸준히 하세요. 반드시 의료 전문가와 상담하세요."},
            {"q": "수술 후 얼마나 쉬어야 하나요?", "a": "수술 종류에 따라 다르지만, 무릎 관절경은 2-4주, 인공관절은 6-12주 정도 재활이 필요합니다."},
            {"q": "퇴원 후 혼자 생활할 수 있나요?", "a": "최소 1-2주간 일상생활에 도움이 필요합니다. 미리 보호자와 일정을 조율하세요."},
        ],
    },
    "cardiac": {
        "label": "심장 시술",
        "steps": [
            PrehabStep(1, "검사", "심장 초음파, 심전도, 혈액 검사", "2주 전"),
            PrehabStep(2, "약물", "항응고제/혈압약 조절 — 의료진 지시 준수", "2주 전"),
            PrehabStep(3, "생활습관", "금연, 금주, 저염식 실천", "2주 전"),
            PrehabStep(4, "운동", "가벼운 걷기 운동 (의료진 허가하에)", "1주 전"),
            PrehabStep(5, "금식", "시술 전날 자정부터 금식", "전날"),
            PrehabStep(6, "당일", "편한 옷, 보호자 동행, 귀중품 보관", "당일"),
        ],
        "timeline": [
            TimelineItem(14, "심장 검사 (초음파, 심전도, 혈액)", "검사"),
            TimelineItem(14, "항응고제 조절 시작", "약물"),
            TimelineItem(14, "금연/금주/저염식 시작", "생활습관"),
            TimelineItem(7, "가벼운 유산소 운동", "운동"),
            TimelineItem(3, "최종 검사 결과 확인", "확인"),
            TimelineItem(1, "금식 시작", "금식"),
            TimelineItem(0, "시술 당일 — 보호자 필수 동행", "당일"),
        ],
        "checklist": [
            "심장 초음파 완료",
            "심전도 검사 완료",
            "혈액 검사 완료",
            "항응고제 조절 확인",
            "금연 실천 중",
            "금식 확인 (8시간 이상)",
            "보호자 동행 확인",
            "응급 연락처 준비",
        ],
        "faq": [
            {"q": "심장 스텐트 시술은 위험한가요?", "a": "관상동맥 스텐트 시술은 비교적 안전하지만, 모든 시술에는 위험이 따릅니다. 담당 의료 전문가와 자세히 상담하세요."},
            {"q": "시술 후 약은 얼마나 복용해야 하나요?", "a": "스텐트 시술 후 항혈소판제를 최소 6개월~1년간 복용해야 합니다. 임의 중단은 위험하므로 의료진 지시를 따르세요."},
            {"q": "시술 후 운동은 언제부터 가능한가요?", "a": "보통 시술 후 1-2주 후 가벼운 걷기부터 시작하며, 점진적으로 운동 강도를 높입니다. 반드시 의료 전문가와 상담하세요."},
        ],
    },
    "cosmetic": {
        "label": "미용 시술",
        "steps": [
            PrehabStep(1, "상담", "시술 목표 및 기대 효과 상담", "2주 전"),
            PrehabStep(2, "피부관리", "시술 부위 자외선 차단 철저히", "2주 전"),
            PrehabStep(3, "약물", "아스피린, 비타민E 등 출혈 유발 약물 중단", "1주 전"),
            PrehabStep(4, "알코올", "시술 3일 전부터 금주", "3일 전"),
            PrehabStep(5, "당일준비", "메이크업 제거, 세안 후 방문", "당일"),
        ],
        "timeline": [
            TimelineItem(14, "시술 상담 및 계획 수립", "상담"),
            TimelineItem(14, "자외선 차단 강화", "피부관리"),
            TimelineItem(7, "출혈 유발 약물/보조제 중단", "약물"),
            TimelineItem(3, "금주 시작", "생활습관"),
            TimelineItem(1, "충분한 수면", "생활습관"),
            TimelineItem(0, "세안 후 민낯으로 방문", "당일"),
        ],
        "checklist": [
            "시술 상담 완료",
            "알레르기 정보 전달",
            "출혈 유발 약물 중단 확인",
            "시술 동의서 서명",
            "시술 후 회복 일정 확보",
            "자외선 차단제 준비",
        ],
        "faq": [
            {"q": "시술 후 붓기는 얼마나 지속되나요?", "a": "시술 종류에 따라 다르지만, 보통 3-7일 내 상당 부분 가라앉습니다. 냉찜질이 도움됩니다. 의료 전문가와 상담하세요."},
            {"q": "시술 후 메이크업은 언제부터 가능한가요?", "a": "비침습 시술(보톡스, 필러)은 다음 날부터, 레이저 시술은 3-5일 후부터 가능합니다. 의료진 지시를 따르세요."},
            {"q": "시술 결과가 마음에 안 들면 어떻게 하나요?", "a": "대부분의 미용 시술은 수정이 가능합니다. 결과에 불만족스러우면 시술 의료진과 솔직하게 상담하세요."},
        ],
    },
}


def list_procedure_types() -> List[str]:
    """지원되는 시술 유형 목록을 반환합니다.

    Returns:
        시술 유형 ID 리스트 (예: ["general", "dental", ...])
    """
    return list(_PROCEDURE_DATA.keys())


def _extract_relevant_content(medical_content: str, procedure_type: str) -> List[str]:
    """의료 콘텐츠에서 시술 관련 키워드를 추출하여 추가 주의사항을 생성합니다."""
    additional_warnings = []

    # 알레르기 관련
    if any(kw in medical_content for kw in ['알레르기', '알러지', 'allergy']):
        additional_warnings.append(
            "알레르기 이력이 언급되었습니다. 모든 알레르기 정보를 의료진에게 반드시 전달하세요."
        )

    # 당뇨 관련
    if any(kw in medical_content for kw in ['당뇨', '혈당', 'diabetes']):
        additional_warnings.append(
            "당뇨 관련 내용이 포함되어 있습니다. 혈당 관리와 금식 조절에 대해 의료진과 상담하세요."
        )

    # 고혈압 관련
    if any(kw in medical_content for kw in ['고혈압', '혈압', 'hypertension']):
        additional_warnings.append(
            "고혈압 관련 내용이 포함되어 있습니다. 혈압약 복용 일정을 의료진과 확인하세요."
        )

    # 임신/수유 관련
    if any(kw in medical_content for kw in ['임신', '수유', '임산부', 'pregnancy']):
        additional_warnings.append(
            "임신/수유 관련 내용이 감지되었습니다. 시술 전 반드시 의료진에게 알리세요."
        )

    return additional_warnings


def generate_prehab_kit(
    medical_content: str,
    procedure_type: str = 'general',
) -> PrehabKit:
    """시술 유형별 수술 전 준비 키트를 생성합니다.

    Args:
        medical_content: 관련 의료 콘텐츠 텍스트 (영상 자막 등)
        procedure_type: 시술 유형 ("general", "dental", "orthopedic", "cardiac", "cosmetic")

    Returns:
        PrehabKit 데이터클래스 인스턴스
    """
    # 지원하지 않는 시술 유형이면 general 폴백
    if procedure_type not in _PROCEDURE_DATA:
        procedure_type = 'general'

    data = _PROCEDURE_DATA[procedure_type]

    # 기본 경고 — 면책조항 필수 포함
    warnings = [_MEDICAL_DISCLAIMER]

    # 콘텐츠 기반 추가 주의사항
    if medical_content:
        additional = _extract_relevant_content(medical_content, procedure_type)
        warnings.extend(additional)

    return PrehabKit(
        procedure_type=procedure_type,
        preparation_steps=list(data["steps"]),
        timeline=list(data["timeline"]),
        checklist=list(data["checklist"]),
        warnings=warnings,
        faq=list(data["faq"]),
    )
