"""SEO 감사 서비스 -- 콘텐츠 기반 SEO 점수 분석"""
import re
from dataclasses import dataclass, field


@dataclass
class SEOIssue:
    """SEO 이슈"""
    category: str = ""
    description: str = ""
    severity: str = "info"       # info / warning / error
    suggestion: str = ""


@dataclass
class SEOAuditReport:
    """SEO 감사 리포트"""
    url: str = ""
    score: float = 0.0
    issues: list = field(default_factory=list)   # list[SEOIssue]
    passed: list = field(default_factory=list)    # list[str]
    grade: str = "F"


def _check_title(content: str) -> tuple[list[SEOIssue], list[str]]:
    """마크다운 H1 제목 검사."""
    issues, passed = [], []
    h1_matches = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)

    if not h1_matches:
        issues.append(SEOIssue(
            category="title",
            description="H1 제목이 없습니다",
            severity="error",
            suggestion="콘텐츠 최상단에 '# 제목' 형태의 H1 헤딩을 추가하세요.",
        ))
    elif len(h1_matches) > 1:
        issues.append(SEOIssue(
            category="title",
            description=f"H1 제목이 {len(h1_matches)}개입니다",
            severity="warning",
            suggestion="H1 제목은 페이지당 1개만 사용하세요.",
        ))
    else:
        title = h1_matches[0]
        if len(title) < 10:
            issues.append(SEOIssue(
                category="title",
                description=f"제목이 너무 짧습니다 ({len(title)}자)",
                severity="warning",
                suggestion="제목을 10자 이상으로 작성하세요.",
            ))
        elif len(title) > 60:
            issues.append(SEOIssue(
                category="title",
                description=f"제목이 너무 깁니다 ({len(title)}자)",
                severity="warning",
                suggestion="제목을 60자 이내로 줄이세요. 검색 결과에서 잘릴 수 있습니다.",
            ))
        else:
            passed.append("H1 제목 길이 적절")

    return issues, passed


def _check_headings(content: str) -> tuple[list[SEOIssue], list[str]]:
    """헤딩 구조 검사."""
    issues, passed = [], []
    headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)

    if len(headings) < 2:
        issues.append(SEOIssue(
            category="structure",
            description="헤딩이 부족합니다",
            severity="warning",
            suggestion="H2, H3 등의 소제목을 추가하여 콘텐츠를 구조화하세요.",
        ))
    else:
        passed.append(f"헤딩 {len(headings)}개 사용")

    # H2 건너뛰기 검사 (H1 → H3)
    levels = [len(h[0]) for h in headings]
    for i in range(1, len(levels)):
        if levels[i] - levels[i - 1] > 1:
            issues.append(SEOIssue(
                category="structure",
                description=f"H{levels[i-1]}에서 H{levels[i]}로 건너뛰었습니다",
                severity="info",
                suggestion="헤딩 레벨을 순차적으로 사용하세요 (H1→H2→H3).",
            ))
            break

    return issues, passed


def _check_content_length(content: str) -> tuple[list[SEOIssue], list[str]]:
    """콘텐츠 길이 검사."""
    issues, passed = [], []
    # 마크다운 기호 제거 후 글자 수
    text = re.sub(r'[#*\-\[\]\(\)\|`>]', '', content)
    char_count = len(text.strip())

    if char_count < 300:
        issues.append(SEOIssue(
            category="content",
            description=f"콘텐츠가 너무 짧습니다 ({char_count}자)",
            severity="error",
            suggestion="SEO를 위해 최소 300자 이상의 콘텐츠를 작성하세요.",
        ))
    elif char_count < 1000:
        issues.append(SEOIssue(
            category="content",
            description=f"콘텐츠가 다소 짧습니다 ({char_count}자)",
            severity="info",
            suggestion="더 상세한 설명을 추가하면 SEO에 유리합니다.",
        ))
    else:
        passed.append(f"콘텐츠 길이 충분 ({char_count}자)")

    return issues, passed


def _check_links(content: str) -> tuple[list[SEOIssue], list[str]]:
    """링크 검사."""
    issues, passed = [], []
    links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)

    if not links:
        issues.append(SEOIssue(
            category="links",
            description="링크가 하나도 없습니다",
            severity="info",
            suggestion="관련 내부/외부 링크를 추가하세요.",
        ))
    else:
        passed.append(f"링크 {len(links)}개 포함")

    # 빈 링크 텍스트 검사
    for text, url in links:
        if not text.strip():
            issues.append(SEOIssue(
                category="links",
                description=f"링크 텍스트가 비어있습니다: {url}",
                severity="warning",
                suggestion="링크에 설명적인 앵커 텍스트를 추가하세요.",
            ))

    return issues, passed


def _check_images(content: str) -> tuple[list[SEOIssue], list[str]]:
    """이미지 alt 텍스트 검사."""
    issues, passed = [], []
    images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)

    if images:
        no_alt = [url for alt, url in images if not alt.strip()]
        if no_alt:
            issues.append(SEOIssue(
                category="images",
                description=f"alt 텍스트 없는 이미지 {len(no_alt)}개",
                severity="warning",
                suggestion="모든 이미지에 설명적인 alt 텍스트를 추가하세요.",
            ))
        else:
            passed.append(f"이미지 {len(images)}개 alt 텍스트 있음")

    return issues, passed


def _check_meta_description(content: str) -> tuple[list[SEOIssue], list[str]]:
    """메타 설명 대용 — 첫 문단 길이 검사."""
    issues, passed = [], []
    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]

    if lines:
        first_para = lines[0]
        if len(first_para) < 50:
            issues.append(SEOIssue(
                category="meta",
                description="첫 문단이 너무 짧습니다 (메타 설명 대용)",
                severity="info",
                suggestion="첫 문단을 50~160자로 작성하면 검색 결과 미리보기에 유리합니다.",
            ))
        else:
            passed.append("첫 문단 길이 적절 (메타 설명 대용)")

    return issues, passed


def _calculate_grade(score: float) -> str:
    """점수를 등급으로 변환한다."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def run_seo_audit(content: str, url: str = "") -> SEOAuditReport:
    """콘텐츠의 SEO 감사를 수행한다.

    Args:
        content: 마크다운 콘텐츠
        url: 페이지 URL (선택)

    Returns:
        SEOAuditReport
    """
    if not content or not content.strip():
        return SEOAuditReport(url=url, score=0.0, grade="F")

    all_issues: list[SEOIssue] = []
    all_passed: list[str] = []

    checks = [
        _check_title,
        _check_headings,
        _check_content_length,
        _check_links,
        _check_images,
        _check_meta_description,
    ]

    for check in checks:
        issues, passed = check(content)
        all_issues.extend(issues)
        all_passed.extend(passed)

    # 점수 계산: 100점에서 이슈 심각도별 감점
    penalty_map = {"error": 20, "warning": 10, "info": 3}
    total_penalty = sum(penalty_map.get(i.severity, 0) for i in all_issues)
    score = max(0.0, min(100.0, 100.0 - total_penalty))

    grade = _calculate_grade(score)

    return SEOAuditReport(
        url=url,
        score=score,
        issues=all_issues,
        passed=all_passed,
        grade=grade,
    )
