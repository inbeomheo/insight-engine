"""YouTube 자막 4단계 폴백 모듈 패키지.

폴백 순서:
1. youtube-transcript-api (youtube_api)
2. Watch 페이지 HTML 파싱 (watch_page)
3. yt-dlp / NotebookLM (content_service 내부)
4. Supadata API (supadata)
+ Whisper 음성인식 (services/transcript/whisper_service.py)
"""
