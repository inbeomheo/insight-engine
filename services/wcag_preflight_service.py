"""
WCAG 프리플라이트 서비스.

웹 접근성(WCAG) 사전 검사를 수행한다.
"""

from dataclasses import dataclass, field
import re
import uuid
import math


@dataclass
class WCAGIssue:
    """WCAG 이슈"""
    issue_id: str = ""
    criterion: str = ""  # 예: "1.1.1"
    level: str = "A"     # A / AA / AAA
    description: str = ""
    element: str = ""
    suggestion: str = ""


@dataclass
class PreflightReport:
    """프리플라이트 보고서"""
    url: str = ""
    issues: list = field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    score: float = 100.0


def check_alt_text(html_content: str) -> list:
    """
    img 태그 alt 속성 누락 검사.

    WCAG 1.1.1: 모든 비텍스트 콘텐츠에 대체 텍스트 제공.
    """
    issues = []

    # <img> 태그 찾기
    img_pattern = re.compile(r'<img\b([^>]*)/?>', re.IGNORECASE)
    alt_pattern = re.compile(r'alt\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)

    for match in img_pattern.finditer(html_content):
        attrs = match.group(1)
        alt_match = alt_pattern.search(attrs)

        if not alt_match:
            issues.append(WCAGIssue(
                issue_id=str(uuid.uuid4()),
                criterion="1.1.1",
                level="A",
                description="img 태그에 alt 속성이 없습니다",
                element=match.group(0)[:100],
                suggestion="alt 속성을 추가하여 이미지 내용을 설명하세요",
            ))
        elif alt_match.group(1).strip() == "":
            # 빈 alt는 장식용 이미지에는 허용, 하지만 경고
            issues.append(WCAGIssue(
                issue_id=str(uuid.uuid4()),
                criterion="1.1.1",
                level="A",
                description="img 태그의 alt 속성이 비어 있습니다 (장식용이 아니라면 내용 추가 필요)",
                element=match.group(0)[:100],
                suggestion="장식용 이미지가 아니면 의미 있는 대체 텍스트를 추가하세요",
            ))

    return issues


def check_heading_hierarchy(html_content: str) -> list:
    """
    헤딩 순서 검사.

    WCAG 1.3.1: h1 → h2 → h3 순서로 사용해야 한다 (레벨 건너뛰기 금지).
    """
    issues = []

    heading_pattern = re.compile(r'<h([1-6])\b[^>]*>', re.IGNORECASE)
    headings = [(int(m.group(1)), m.start()) for m in heading_pattern.finditer(html_content)]

    if not headings:
        return issues

    # 첫 헤딩이 h1이 아닌 경우
    if headings[0][0] != 1:
        issues.append(WCAGIssue(
            issue_id=str(uuid.uuid4()),
            criterion="1.3.1",
            level="A",
            description=f"문서의 첫 헤딩이 h{headings[0][0]}입니다 (h1이어야 함)",
            element=f"h{headings[0][0]}",
            suggestion="문서 시작을 h1으로 변경하세요",
        ))

    # 레벨 건너뛰기 검사
    for i in range(1, len(headings)):
        prev_level = headings[i - 1][0]
        curr_level = headings[i][0]

        if curr_level > prev_level + 1:
            issues.append(WCAGIssue(
                issue_id=str(uuid.uuid4()),
                criterion="1.3.1",
                level="A",
                description=f"헤딩 레벨이 h{prev_level}에서 h{curr_level}로 건너뛰었습니다",
                element=f"h{curr_level}",
                suggestion=f"h{prev_level + 1}을 사용하세요",
            ))

    return issues


def _parse_hex_color(color: str) -> tuple:
    """16진수 색상을 RGB 튜플로 변환"""
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    if len(color) != 6:
        raise ValueError(f"잘못된 색상 형식: {color}")
    return (
        int(color[0:2], 16),
        int(color[2:4], 16),
        int(color[4:6], 16),
    )


def _relative_luminance(r: int, g: int, b: int) -> float:
    """상대 휘도 계산 (WCAG 2.0 공식)"""

    def linearize(c):
        c_srgb = c / 255.0
        if c_srgb <= 0.04045:
            return c_srgb / 12.92
        return ((c_srgb + 0.055) / 1.055) ** 2.4

    r_lin = linearize(r)
    g_lin = linearize(g)
    b_lin = linearize(b)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def check_color_contrast(foreground: str, background: str) -> "WCAGIssue | None":
    """
    명도비 검사.

    WCAG 1.4.3: 일반 텍스트 최소 4.5:1 대비.
    """
    try:
        fg_rgb = _parse_hex_color(foreground)
        bg_rgb = _parse_hex_color(background)
    except ValueError:
        return WCAGIssue(
            issue_id=str(uuid.uuid4()),
            criterion="1.4.3",
            level="AA",
            description="색상 형식을 파싱할 수 없습니다",
            element=f"fg={foreground}, bg={background}",
            suggestion="올바른 16진수 색상 코드를 사용하세요",
        )

    lum_fg = _relative_luminance(*fg_rgb)
    lum_bg = _relative_luminance(*bg_rgb)

    lighter = max(lum_fg, lum_bg)
    darker = min(lum_fg, lum_bg)

    contrast_ratio = (lighter + 0.05) / (darker + 0.05)

    if contrast_ratio < 4.5:
        return WCAGIssue(
            issue_id=str(uuid.uuid4()),
            criterion="1.4.3",
            level="AA",
            description=f"명도비 {contrast_ratio:.2f}:1 (최소 4.5:1 필요)",
            element=f"fg={foreground}, bg={background}",
            suggestion="전경색이나 배경색을 조정하여 대비를 높이세요",
        )

    return None


def run_preflight(html_content: str) -> PreflightReport:
    """전체 WCAG 프리플라이트 검사"""
    all_issues = []

    # alt 텍스트 검사
    all_issues.extend(check_alt_text(html_content))

    # 헤딩 순서 검사
    all_issues.extend(check_heading_hierarchy(html_content))

    # 검사 항목 수 (alt + heading + contrast = 3개 기본 검사)
    total_checks = 3
    fail_count = min(total_checks, len(all_issues))
    pass_count = total_checks - fail_count

    score = (pass_count / total_checks) * 100 if total_checks > 0 else 100.0

    return PreflightReport(
        url="",
        issues=all_issues,
        pass_count=pass_count,
        fail_count=fail_count,
        score=round(score, 1),
    )
