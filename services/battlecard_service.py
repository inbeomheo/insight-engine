"""
세일즈 배틀카드 + 성과 포스트 재작성 서비스

영상 자막에서 규칙 기반으로 핵심 주장/증거/반론을 추출하고,
콘텐츠를 성과 데이터 기반으로 재작성합니다.
외부 AI API 호출 없이 순수 Python 로직만 사용합니다.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


# ── 타임스탬프 패턴 ──
_TIMESTAMP_PATTERN = re.compile(
    r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
)

# ── 주장 신호어 (한국어/영어) ──
_CLAIM_SIGNALS = [
    '핵심은', '중요한 점은', '결론은', '요약하면', '강조하면',
    '주장하는', '말하자면', '포인트는', '사실은', '증명하',
    '확실한', '분명한', '입증된', '검증된', '실험 결과',
    'the key is', 'importantly', 'the point is', 'in conclusion',
    'the fact is', 'research shows', 'data shows', 'proven',
]

# ── 반론/반대 의견 신호어 ──
_OBJECTION_SIGNALS = [
    '하지만', '그러나', '반면에', '문제는', '단점은', '비판',
    '우려', '걱정', '의문', '반론', '반대', '한계',
    '위험', '리스크', '약점', '불리한', '부정적',
    'however', 'but', 'on the other hand', 'the problem is',
    'the downside', 'critics say', 'the risk', 'concern',
    'limitation', 'weakness', 'drawback',
]

# ── 차별화 포인트 신호어 ──
_DIFFERENTIATOR_SIGNALS = [
    '차별화', '유일한', '독보적', '특별한', '차이점',
    '다른 점은', '장점은', '강점은', '경쟁 우위', '최초',
    'unique', 'different', 'advantage', 'stand out', 'unlike',
    'competitive edge', 'first', 'only',
]

# ── 증거 신호어 ──
_EVIDENCE_SIGNALS = [
    '예를 들', '실제로', '사례', '데이터', '통계',
    '수치', '결과', '%', '연구', '조사',
    'for example', 'actually', 'case study', 'data', 'statistics',
    'percent', 'research', 'study', 'survey',
]


@dataclass
class BattleCard:
    """세일즈 배틀카드 데이터 구조"""
    video_id: str
    claims: list = field(default_factory=list)
    # [{"claim": "...", "evidence": "...", "timestamp": "MM:SS"}]
    objections: list = field(default_factory=list)
    # [{"objection": "...", "response": "...", "source": "..."}]
    key_differentiators: list = field(default_factory=list)
    elevator_pitch: str = ''
    competitive_advantages: list = field(default_factory=list)


@dataclass
class RewrittenPost:
    """재작성된 콘텐츠 데이터 구조"""
    original_summary: str
    rewritten_content: str
    changes_made: list = field(default_factory=list)
    expected_improvement: str = ''


def _timestamp_to_display(ts: str) -> str:
    """타임스탬프 문자열을 MM:SS 표시 형식으로 정규화합니다."""
    parts = ts.split(':')
    if len(parts) == 3:
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        total_min = h * 60 + m
        return f'{total_min:02d}:{s:02d}'
    elif len(parts) == 2:
        return f'{int(parts[0]):02d}:{int(parts[1]):02d}'
    return '00:00'


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리합니다."""
    # 한국어/영어 문장 종결 패턴
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _find_nearby_timestamp(text: str, position: int) -> str:
    """텍스트에서 주어진 위치 근처의 타임스탬프를 찾습니다."""
    # 위치 앞쪽 200자 범위에서 가장 가까운 타임스탬프 탐색
    search_start = max(0, position - 200)
    search_text = text[search_start:position + 50]
    matches = list(_TIMESTAMP_PATTERN.finditer(search_text))
    if matches:
        return _timestamp_to_display(matches[-1].group(1))
    return '00:00'


def _contains_signal(text: str, signals: list[str]) -> bool:
    """텍스트에 신호어가 포함되어 있는지 확인합니다."""
    text_lower = text.lower()
    return any(sig.lower() in text_lower for sig in signals)


def _find_evidence_for_claim(sentences: list[str], claim_idx: int) -> str:
    """주장 문장 이후에서 증거를 찾습니다."""
    # 주장 다음 3문장 내에서 증거 신호어 탐색
    for i in range(claim_idx + 1, min(claim_idx + 4, len(sentences))):
        if _contains_signal(sentences[i], _EVIDENCE_SIGNALS):
            return sentences[i]
    # 증거 없으면 다음 문장을 근거로 사용
    if claim_idx + 1 < len(sentences):
        return sentences[claim_idx + 1]
    return ''


def _find_response_for_objection(sentences: list[str], obj_idx: int) -> str:
    """반론 문장 이후에서 대응 문구를 찾습니다."""
    # 반론 다음 2문장 내에서 긍정적/대응적 문장 탐색
    response_signals = [
        '해결', '대안', '오히려', '그럼에도', '극복',
        '보완', '대응', '개선', '그래서', '따라서',
        'solution', 'instead', 'nevertheless', 'therefore', 'however',
    ]
    for i in range(obj_idx + 1, min(obj_idx + 3, len(sentences))):
        if _contains_signal(sentences[i], response_signals):
            return sentences[i]
    # 대응 문장 없으면 다음 문장 사용
    if obj_idx + 1 < len(sentences):
        return sentences[obj_idx + 1]
    return '추가 검토 필요'


def _generate_elevator_pitch(claims: list[dict], differentiators: list[str]) -> str:
    """핵심 주장과 차별화 포인트로 30초 엘리베이터 피치를 생성합니다."""
    parts = []

    # 가장 강력한 주장 1개
    if claims:
        parts.append(claims[0]['claim'])

    # 차별화 포인트 최대 2개
    for diff in differentiators[:2]:
        parts.append(diff)

    if not parts:
        return '이 콘텐츠의 핵심 가치를 요약할 수 있는 정보가 부족합니다.'

    pitch = ' '.join(parts)
    # 30초 피치 = 약 150자 이내
    if len(pitch) > 150:
        pitch = pitch[:147] + '...'
    return pitch


def extract_battlecard(video_id: str, transcript: str) -> BattleCard:
    """자막에서 세일즈 배틀카드를 규칙 기반으로 추출합니다.

    Args:
        video_id: YouTube 영상 ID
        transcript: 자막 전체 텍스트 (타임스탬프 [MM:SS] 포함 가능)

    Returns:
        BattleCard 데이터클래스
    """
    if not transcript or not transcript.strip():
        return BattleCard(video_id=video_id)

    card = BattleCard(video_id=video_id)
    sentences = _split_sentences(transcript)

    # ── 1. 핵심 주장 + 증거 추출 ──
    for idx, sentence in enumerate(sentences):
        if _contains_signal(sentence, _CLAIM_SIGNALS):
            evidence = _find_evidence_for_claim(sentences, idx)
            timestamp = _find_nearby_timestamp(transcript, transcript.find(sentence))
            card.claims.append({
                'claim': sentence,
                'evidence': evidence,
                'timestamp': timestamp,
            })

    # ── 2. 반론/반대 의견 + 대응 추출 ──
    for idx, sentence in enumerate(sentences):
        if _contains_signal(sentence, _OBJECTION_SIGNALS):
            response = _find_response_for_objection(sentences, idx)
            card.objections.append({
                'objection': sentence,
                'response': response,
                'source': 'transcript',
            })

    # 최소 3개 반론 보장: 부족하면 일반 문장에서 잠재적 반론 생성
    if len(card.objections) < 3:
        fallback_objections = [
            {'objection': '가격 대비 가치가 불분명할 수 있다.',
             'response': '구체적인 ROI 데이터와 사례를 제시하여 설득력을 높인다.',
             'source': 'generated'},
            {'objection': '기존 솔루션 대비 전환 비용이 발생할 수 있다.',
             'response': '단계적 도입 방안과 마이그레이션 지원을 안내한다.',
             'source': 'generated'},
            {'objection': '장기적인 지속 가능성에 대한 의문이 있을 수 있다.',
             'response': '로드맵과 지속적 업데이트 계획을 공유한다.',
             'source': 'generated'},
        ]
        needed = 3 - len(card.objections)
        card.objections.extend(fallback_objections[:needed])

    # ── 3. 차별화 포인트 추출 ──
    for sentence in sentences:
        if _contains_signal(sentence, _DIFFERENTIATOR_SIGNALS):
            # 중복 방지
            if sentence not in card.key_differentiators:
                card.key_differentiators.append(sentence)

    # ── 4. 경쟁 우위 (차별화 + 증거 있는 주장에서 도출) ──
    for claim in card.claims:
        if claim['evidence']:
            advantage = f"{claim['claim']} ({claim['evidence'][:50]}...)" \
                if len(claim['evidence']) > 50 else f"{claim['claim']} ({claim['evidence']})"
            if advantage not in card.competitive_advantages:
                card.competitive_advantages.append(advantage)

    # ── 5. 엘리베이터 피치 ──
    card.elevator_pitch = _generate_elevator_pitch(card.claims, card.key_differentiators)

    return card


def rewrite_top_post(
    content: str,
    performance_data: Optional[dict] = None,
) -> RewrittenPost:
    """성과 데이터 기반으로 콘텐츠를 규칙 기반으로 재작성합니다.

    Args:
        content: 원본 콘텐츠 텍스트
        performance_data: 성과 지표 dict (선택)
            - views: 조회수
            - engagement_rate: 참여율 (0~1)
            - avg_watch_time: 평균 시청 시간(초)
            - bounce_rate: 이탈률 (0~1)
            - top_sections: 인기 섹션 목록

    Returns:
        RewrittenPost 데이터클래스
    """
    if not content or not content.strip():
        return RewrittenPost(
            original_summary='',
            rewritten_content='',
            changes_made=[],
            expected_improvement='원본 콘텐츠가 없어 재작성할 수 없습니다.',
        )

    perf = performance_data or {}
    changes = []
    rewritten = content

    # ── 원본 요약 생성 (첫 200자) ──
    original_summary = content[:200].strip()
    if len(content) > 200:
        original_summary += '...'

    # ── 1. 도입부 강화: 첫 문장에 훅 추가 ──
    sentences = _split_sentences(rewritten)
    if sentences:
        first = sentences[0]
        if not first.endswith('?') and not first.startswith('왜') and not first.startswith('어떻게'):
            hook_prefix = '핵심 인사이트: '
            new_first = hook_prefix + first
            rewritten = rewritten.replace(first, new_first, 1)
            changes.append('도입부에 "핵심 인사이트:" 훅 추가')

    # ── 2. 이탈률 높으면 단락 분리 강화 ──
    bounce_rate = perf.get('bounce_rate', 0)
    if bounce_rate > 0.5:
        # 긴 단락(200자 이상)을 분리
        paragraphs = rewritten.split('\n\n')
        new_paragraphs = []
        for para in paragraphs:
            if len(para) > 200:
                mid = len(para) // 2
                # 가장 가까운 마침표에서 분리
                split_pos = para.rfind('.', 0, mid + 50)
                if split_pos == -1:
                    split_pos = para.rfind('。', 0, mid + 50)
                if split_pos > 0:
                    new_paragraphs.append(para[:split_pos + 1].strip())
                    new_paragraphs.append(para[split_pos + 1:].strip())
                else:
                    new_paragraphs.append(para)
            else:
                new_paragraphs.append(para)
        rewritten = '\n\n'.join(p for p in new_paragraphs if p)
        changes.append('높은 이탈률 대응: 긴 단락을 분리하여 가독성 향상')

    # ── 3. 참여율 낮으면 CTA(행동 유도) 추가 ──
    engagement_rate = perf.get('engagement_rate', 0.5)
    if engagement_rate < 0.3:
        cta = '\n\n---\n이 내용이 도움이 되셨나요? 의견을 댓글로 남겨주세요!'
        rewritten += cta
        changes.append('낮은 참여율 대응: 댓글 유도 CTA 추가')

    # ── 4. 인기 섹션 강조 ──
    top_sections = perf.get('top_sections', [])
    for section in top_sections[:3]:
        if section in rewritten:
            emphasized = f'**{section}**'
            rewritten = rewritten.replace(section, emphasized, 1)
            changes.append(f'인기 섹션 강조: "{section[:20]}..." 볼드 처리')

    # ── 5. 평균 시청 시간 짧으면 핵심 요약 박스 추가 ──
    avg_watch = perf.get('avg_watch_time', 300)
    if avg_watch < 120:
        # 핵심 문장 3개 추출
        key_sentences = [s for s in sentences if _contains_signal(s, _CLAIM_SIGNALS)][:3]
        if key_sentences:
            summary_box = '\n\n> **핵심 요약**\n' + '\n'.join(
                f'> - {s}' for s in key_sentences
            )
            # 도입부 바로 뒤에 삽입
            first_break = rewritten.find('\n\n')
            if first_break > 0:
                rewritten = rewritten[:first_break] + summary_box + rewritten[first_break:]
            else:
                rewritten = summary_box + '\n\n' + rewritten
            changes.append('짧은 시청 시간 대응: 핵심 요약 박스 추가')

    # ── 6. 제목/소제목에 숫자/리스트 형식 강화 ──
    lines = rewritten.split('\n')
    new_lines = []
    heading_count = 0
    for line in lines:
        if line.startswith('#') and not re.search(r'\d', line):
            heading_count += 1
            # 숫자 접두사 추가
            heading_match = re.match(r'(#+)\s*(.*)', line)
            if heading_match:
                prefix = heading_match.group(1)
                title = heading_match.group(2)
                line = f'{prefix} {heading_count}. {title}'
                if heading_count == 1:
                    changes.append('소제목에 번호 매기기 적용')
        new_lines.append(line)
    rewritten = '\n'.join(new_lines)

    # ── 7. 변경 없으면 기본 개선 ──
    if not changes:
        rewritten = f'**[개선판]** {rewritten}'
        changes.append('기본 개선: 제목에 [개선판] 태그 추가')

    # ── 개선 기대치 산정 ──
    improvement_parts = []
    if bounce_rate > 0.5:
        improvement_parts.append('이탈률 10-15% 감소 예상')
    if engagement_rate < 0.3:
        improvement_parts.append('참여율 20-30% 증가 예상')
    if avg_watch < 120:
        improvement_parts.append('평균 체류 시간 30초+ 증가 예상')
    if not improvement_parts:
        improvement_parts.append('가독성 및 구조 개선으로 전반적 품질 향상 예상')

    expected_improvement = '; '.join(improvement_parts)

    return RewrittenPost(
        original_summary=original_summary,
        rewritten_content=rewritten,
        changes_made=changes,
        expected_improvement=expected_improvement,
    )
