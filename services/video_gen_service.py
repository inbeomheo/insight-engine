"""
텍스트→비디오 생성 서비스 (F10-06)
RunwayML / Pika / Sora API 연동 (폴백: 슬라이드쇼 FFmpeg)
"""
import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

RUNWAY_API_KEY = os.getenv('RUNWAY_API_KEY', '')
PIKA_API_KEY = os.getenv('PIKA_API_KEY', '')


def _generate_with_runway(prompt: str, duration: int = 4) -> bytes:
    """RunwayML Gen-3 텍스트→비디오 생성"""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx 패키지 필요")

    if not RUNWAY_API_KEY:
        raise RuntimeError("RUNWAY_API_KEY 미설정")

    headers = {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06",
    }

    # 태스크 생성
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://api.dev.runwayml.com/v1/text_to_video",
            json={
                "promptText": prompt[:1000],
                "duration": duration,
                "ratio": "1280:720",
                "watermark": False,
            },
            headers=headers,
        )
    resp.raise_for_status()
    task_id = resp.json()['id']

    # 폴링 (최대 3분)
    import time
    for _ in range(36):
        time.sleep(5)
        with httpx.Client(timeout=10) as client:
            status_resp = client.get(
                f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                headers=headers,
            )
        data = status_resp.json()
        status = data.get('status')
        if status == 'SUCCEEDED':
            video_url = data['output'][0]
            with httpx.Client(timeout=60) as client:
                video_resp = client.get(video_url)
            return video_resp.content
        elif status in ('FAILED', 'CANCELLED'):
            raise RuntimeError(f"RunwayML 생성 실패: {data.get('failure', status)}")

    raise TimeoutError("RunwayML 비디오 생성 타임아웃 (3분 초과)")


def _generate_slideshow_ffmpeg(
    images: list,
    audio_path: Optional[str] = None,
    fps: int = 24,
    duration_per_image: float = 3.0,
) -> bytes:
    """
    FFmpeg 슬라이드쇼 생성 (RunwayML 폴백)
    이미지 리스트 → MP4 비디오
    """
    if not images:
        raise ValueError("이미지 목록이 필요합니다")

    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("FFmpeg가 설치되지 않았습니다")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 이미지를 순서대로 저장
        concat_file = os.path.join(tmpdir, 'concat.txt')
        with open(concat_file, 'w') as f:
            for img_data in images:
                img_path = os.path.join(tmpdir, f"frame_{images.index(img_data):04d}.jpg")
                with open(img_path, 'wb') as img_f:
                    img_f.write(img_data if isinstance(img_data, bytes) else img_data.read())
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration_per_image}\n")

        output_path = os.path.join(tmpdir, 'output.mp4')
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-vf', f'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720',
            '-c:v', 'libx264', '-r', str(fps),
            '-preset', 'fast', '-crf', '23',
            '-pix_fmt', 'yuv420p',
        ]

        if audio_path and os.path.exists(audio_path):
            cmd += ['-i', audio_path, '-c:a', 'aac', '-shortest']

        cmd.append(output_path)
        subprocess.run(cmd, capture_output=True, check=True)

        with open(output_path, 'rb') as f:
            return f.read()


class VideoGenService:
    """텍스트→비디오 생성 서비스"""

    def generate_from_text(
        self,
        prompt: str,
        duration: int = 4,
        fallback_to_slideshow: bool = True,
    ) -> bytes:
        """
        텍스트 프롬프트로 비디오 생성

        Args:
            prompt: 비디오 설명 프롬프트
            duration: 비디오 길이 (초)
            fallback_to_slideshow: API 실패 시 슬라이드쇼 폴백

        Returns:
            비디오 바이트 (MP4)
        """
        if RUNWAY_API_KEY:
            try:
                logger.info("RunwayML 비디오 생성 시작")
                return _generate_with_runway(prompt, duration)
            except Exception as e:
                logger.warning("RunwayML 실패: %s", e)
                if not fallback_to_slideshow:
                    raise

        if fallback_to_slideshow:
            logger.info("슬라이드쇼 폴백 사용")
            # 빈 이미지 슬라이드쇼 (실제 구현에서는 이미지 생성 서비스 연동)
            raise RuntimeError(
                "슬라이드쇼 생성을 위해 이미지 목록이 필요합니다. "
                "generate_slideshow() 메서드를 직접 사용하세요."
            )

        raise RuntimeError("비디오 생성 서비스 미설정 (RUNWAY_API_KEY 필요)")

    def generate_slideshow(
        self,
        image_bytes_list: list,
        audio_bytes: Optional[bytes] = None,
        duration_per_slide: float = 3.0,
    ) -> bytes:
        """이미지 리스트로 슬라이드쇼 비디오 생성"""
        audio_path = None

        with tempfile.TemporaryDirectory() as tmpdir:
            if audio_bytes:
                audio_path = os.path.join(tmpdir, 'audio.mp3')
                with open(audio_path, 'wb') as f:
                    f.write(audio_bytes)

            return _generate_slideshow_ffmpeg(
                image_bytes_list,
                audio_path=audio_path,
                duration_per_image=duration_per_slide,
            )
