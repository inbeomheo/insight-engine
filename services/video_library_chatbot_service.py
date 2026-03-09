"""
비디오 라이브러리 챗봇 서비스 — 비디오 컬렉션에 대한 자연어 질의 처리
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class VideoEntry:
    """비디오 항목"""
    video_id: str
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    duration_sec: int = 0
    transcript_preview: str = ""


@dataclass
class ChatResponse:
    """챗봇 응답"""
    answer: str
    relevant_videos: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class VideoLibrary:
    """비디오 라이브러리"""
    library_id: str
    videos: list[VideoEntry] = field(default_factory=list)


def _create_library(library_id: str | None = None) -> VideoLibrary:
    """빈 비디오 라이브러리 생성"""
    return VideoLibrary(
        library_id=library_id or str(uuid.uuid4()),
        videos=[],
    )


def add_video(library: VideoLibrary, video_config: dict) -> VideoLibrary:
    """비디오 추가

    Args:
        library: 대상 라이브러리
        video_config: video_id, title, description 등 비디오 설정

    Returns:
        업데이트된 라이브러리
    """
    video = VideoEntry(
        video_id=video_config.get("video_id", str(uuid.uuid4())),
        title=video_config.get("title", ""),
        description=video_config.get("description", ""),
        tags=video_config.get("tags", []),
        duration_sec=video_config.get("duration_sec", 0),
        transcript_preview=video_config.get("transcript_preview", ""),
    )
    library.videos.append(video)
    return library


def search_library(library: VideoLibrary, query: str) -> list[VideoEntry]:
    """키워드 매칭 검색 (제목/설명/태그)

    Args:
        library: 검색 대상 라이브러리
        query: 검색어

    Returns:
        매칭된 비디오 목록 (관련도 순)
    """
    if not query.strip():
        return []

    query_lower = query.lower()
    query_terms = query_lower.split()
    scored: list[tuple[float, VideoEntry]] = []

    for video in library.videos:
        score = 0.0
        title_lower = video.title.lower()
        desc_lower = video.description.lower()
        tags_lower = [t.lower() for t in video.tags]
        transcript_lower = video.transcript_preview.lower()

        for term in query_terms:
            # 제목 매칭 (가중치 높음)
            if term in title_lower:
                score += 3.0
            # 태그 매칭
            for tag in tags_lower:
                if term in tag:
                    score += 2.0
                    break
            # 설명 매칭
            if term in desc_lower:
                score += 1.0
            # 자막 미리보기 매칭
            if term in transcript_lower:
                score += 0.5

        if score > 0:
            scored.append((score, video))

    # 점수 내림차순 정렬
    scored.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in scored]


def answer_query(library: VideoLibrary, query: str) -> ChatResponse:
    """질의 응답 — 관련 비디오 검색 후 설명 기반 답변 조합

    Args:
        library: 대상 라이브러리
        query: 자연어 질의

    Returns:
        답변 + 관련 비디오 ID + 신뢰도
    """
    if not query.strip():
        return ChatResponse(
            answer="질문을 입력해 주세요.",
            relevant_videos=[],
            confidence=0.0,
        )

    results = search_library(library, query)

    if not results:
        return ChatResponse(
            answer=f"'{query}'에 대한 관련 비디오를 찾지 못했습니다.",
            relevant_videos=[],
            confidence=0.0,
        )

    # 상위 결과로 답변 구성
    top_results = results[:3]
    video_ids = [v.video_id for v in top_results]

    # 답변 텍스트 조합
    answer_parts = [f"'{query}'에 대해 {len(results)}개의 관련 비디오를 찾았습니다."]
    for i, video in enumerate(top_results, 1):
        desc_preview = video.description[:100] if video.description else "설명 없음"
        answer_parts.append(f"{i}. [{video.title}] - {desc_preview}")

    # 신뢰도 계산 (결과 수 기반)
    confidence = min(1.0, len(results) * 0.2)

    return ChatResponse(
        answer="\n".join(answer_parts),
        relevant_videos=video_ids,
        confidence=round(confidence, 2),
    )


def suggest_related(
    library: VideoLibrary, video_id: str, top_k: int = 5
) -> list[VideoEntry]:
    """태그 유사도 기반 관련 비디오 추천

    Args:
        library: 대상 라이브러리
        video_id: 기준 비디오 ID
        top_k: 반환할 최대 수

    Returns:
        유사한 비디오 목록
    """
    # 기준 비디오 찾기
    target = None
    for video in library.videos:
        if video.video_id == video_id:
            target = video
            break

    if target is None:
        return []

    target_tags = set(t.lower() for t in target.tags)
    if not target_tags:
        return []

    # 태그 유사도 계산 (Jaccard 유사도)
    scored: list[tuple[float, VideoEntry]] = []
    for video in library.videos:
        if video.video_id == video_id:
            continue
        video_tags = set(t.lower() for t in video.tags)
        if not video_tags:
            continue
        intersection = len(target_tags & video_tags)
        union = len(target_tags | video_tags)
        similarity = intersection / union if union > 0 else 0.0
        if similarity > 0:
            scored.append((similarity, video))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in scored[:top_k]]
