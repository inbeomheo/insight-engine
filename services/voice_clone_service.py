"""
음성 복제 TTS 서비스 (F10-03)
ElevenLabs / Coqui XTTS 기반 화자 복제
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')


def _synthesize_elevenlabs(
    text: str,
    voice_id: str,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> bytes:
    """
    ElevenLabs API로 음성 복제 합성

    Args:
        voice_id: ElevenLabs 음성 ID (복제된 음성)
        stability: 음성 안정성 (0~1)
        similarity_boost: 원본 유사도 (0~1)
    """
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx 패키지가 필요합니다: pip install httpx")

    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY가 설정되지 않았습니다")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        }
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"ElevenLabs API 오류: {resp.status_code} {resp.text[:200]}")

    return resp.content


def _synthesize_coqui_xtts(
    text: str,
    speaker_wav_path: str,
    language: str = 'ko',
) -> bytes:
    """
    Coqui XTTS-v2 로컬 음성 복제
    pip install TTS 필요
    """
    try:
        from TTS.api import TTS
    except ImportError:
        raise RuntimeError("TTS 패키지가 필요합니다: pip install TTS")

    import io
    import tempfile

    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav_path,
            language=language,
            file_path=tmp_path,
        )
        with open(tmp_path, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


class VoiceCloneService:
    """
    음성 복제 TTS 서비스

    백엔드 우선순위:
    1. ElevenLabs (ELEVENLABS_API_KEY 설정 시)
    2. Coqui XTTS (로컬, speaker_wav 필요)
    """

    def __init__(self):
        self.backend = 'elevenlabs' if ELEVENLABS_API_KEY else 'coqui'
        logger.info("VoiceCloneService 초기화: backend=%s", self.backend)

    def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speaker_wav: Optional[str] = None,
        language: str = 'ko',
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> bytes:
        """
        음성 복제로 텍스트 합성

        Args:
            text: 합성할 텍스트
            voice_id: ElevenLabs 음성 ID (ElevenLabs 백엔드)
            speaker_wav: 참조 음성 파일 경로 (Coqui 백엔드)
            language: 언어 코드 (ko/en/ja)
            stability: 안정성 (ElevenLabs)
            similarity_boost: 유사도 (ElevenLabs)

        Returns:
            오디오 바이트 (MP3 또는 WAV)
        """
        if not text or not text.strip():
            raise ValueError("합성할 텍스트가 필요합니다")

        if self.backend == 'elevenlabs':
            if not voice_id:
                raise ValueError("ElevenLabs 백엔드는 voice_id가 필요합니다")
            return _synthesize_elevenlabs(text, voice_id, stability, similarity_boost)
        else:
            if not speaker_wav:
                raise ValueError("Coqui 백엔드는 speaker_wav 파일이 필요합니다")
            if not os.path.exists(speaker_wav):
                raise FileNotFoundError(f"참조 음성 파일 없음: {speaker_wav}")
            return _synthesize_coqui_xtts(text, speaker_wav, language)

    def clone_voice_from_url(
        self,
        name: str,
        audio_url: str,
        description: str = '',
    ) -> str:
        """
        ElevenLabs에 새 음성 등록 후 voice_id 반환

        Args:
            name: 음성 이름
            audio_url: 참조 오디오 URL

        Returns:
            voice_id
        """
        if self.backend != 'elevenlabs':
            raise RuntimeError("음성 등록은 ElevenLabs 백엔드만 지원")

        try:
            import httpx
            import io

            # 오디오 다운로드
            with httpx.Client(timeout=30) as client:
                audio_resp = client.get(audio_url)
            audio_resp.raise_for_status()

            # ElevenLabs IVC API
            with httpx.Client(timeout=60) as client:
                files = {'files': ('sample.mp3', audio_resp.content, 'audio/mpeg')}
                data = {'name': name, 'description': description}
                resp = client.post(
                    "https://api.elevenlabs.io/v1/voices/add",
                    headers={"xi-api-key": ELEVENLABS_API_KEY},
                    data=data,
                    files=files,
                )
            resp.raise_for_status()
            voice_id = resp.json()['voice_id']
            logger.info("음성 복제 등록 완료: voice_id=%s", voice_id)
            return voice_id

        except Exception as e:
            raise RuntimeError(f"음성 복제 등록 실패: {e}") from e
