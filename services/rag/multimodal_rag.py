"""
멀티모달 RAG 서비스 (F10-14)
이미지, PDF, 오디오 등 다양한 입력에서 지식 추출 후 RAG에 통합
"""
import base64
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _encode_image_base64(image_path: str) -> str:
    """이미지를 base64 인코딩"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def _extract_text_from_image_gemini(image_path: str) -> str:
    """Gemini Vision으로 이미지에서 텍스트/내용 추출"""
    try:
        import google.generativeai as genai

        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY 미설정")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-lite')

        with open(image_path, 'rb') as f:
            image_data = f.read()

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png', '.webp': 'image/webp'}
        mime = mime_map.get(ext, 'image/jpeg')

        response = model.generate_content([
            "이 이미지의 내용을 상세히 설명하세요. 텍스트, 표, 도표, 주요 시각적 요소를 포함하여 설명하세요.",
            {'inline_data': {'mime_type': mime, 'data': base64.b64encode(image_data).decode()}}
        ])
        return response.text

    except ImportError:
        raise RuntimeError("google-generativeai 패키지 필요: pip install google-generativeai")


def _extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트 추출"""
    # PyMuPDF 시도
    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        texts = [page.get_text() for page in doc]
        return '\n\n'.join(texts)
    except ImportError:
        pass

    # pdfplumber 폴백
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return '\n\n'.join(
                page.extract_text() or '' for page in pdf.pages
            )
    except ImportError:
        raise RuntimeError("PDF 추출을 위해 pymupdf 또는 pdfplumber 필요")


def _extract_text_from_audio(audio_path: str) -> str:
    """오디오에서 Whisper로 텍스트 추출"""
    try:
        from services.whisper_service import WhisperService
        svc = WhisperService()
        result = svc.transcribe(audio_path)
        return result.get('text', '')
    except Exception as e:
        raise RuntimeError(f"오디오 전사 실패: {e}") from e


class MultimodalRAG:
    """
    멀티모달 RAG

    지원 입력 타입:
    - text: 일반 텍스트
    - image: 이미지 (JPG/PNG/WEBP)
    - pdf: PDF 문서
    - audio: 오디오 파일 (MP3/WAV)

    처리 흐름:
    1. 파일 타입 감지
    2. 적절한 추출기로 텍스트 변환
    3. RAG 벡터 스토어에 인덱싱
    """

    SUPPORTED_EXTENSIONS = {
        'image': {'.jpg', '.jpeg', '.png', '.webp', '.gif'},
        'pdf': {'.pdf'},
        'audio': {'.mp3', '.wav', '.m4a', '.ogg', '.flac'},
        'text': {'.txt', '.md', '.csv', '.json', '.html'},
    }

    def __init__(self):
        self._vector_store = None
        self._init_vector_store()

    def _init_vector_store(self):
        try:
            from services.rag.vector_store import VectorStore
            self._vector_store = VectorStore()
        except Exception as e:
            logger.warning("벡터 스토어 초기화 실패: %s", e)

    def detect_file_type(self, file_path: str) -> str:
        """파일 확장자로 타입 감지"""
        ext = os.path.splitext(file_path)[1].lower()
        for file_type, extensions in self.SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        return 'text'  # 기본값

    def extract_text(self, file_path: str, file_type: Optional[str] = None) -> str:
        """
        파일에서 텍스트 추출

        Args:
            file_path: 파일 경로
            file_type: 파일 타입 (None이면 자동 감지)

        Returns:
            추출된 텍스트
        """
        ftype = file_type or self.detect_file_type(file_path)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일 없음: {file_path}")

        if ftype == 'image':
            return _extract_text_from_image_gemini(file_path)
        elif ftype == 'pdf':
            return _extract_text_from_pdf(file_path)
        elif ftype == 'audio':
            return _extract_text_from_audio(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

    def ingest_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        file_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        파일을 RAG 시스템에 통합

        Returns:
            {'success': bool, 'text_length': int, 'chunks_added': int, 'file_type': str}
        """
        ftype = file_type or self.detect_file_type(file_path)

        try:
            text = self.extract_text(file_path, file_type=ftype)
        except Exception as e:
            logger.error("텍스트 추출 실패: %s", e)
            return {'success': False, 'error': str(e)}

        if not text or not text.strip():
            return {'success': False, 'error': '추출된 텍스트 없음'}

        meta = metadata or {}
        meta.update({
            'file_path': file_path,
            'file_type': ftype,
            'file_name': os.path.basename(file_path),
        })

        # 벡터 스토어에 추가
        chunks_added = 0
        if self._vector_store:
            try:
                chunks_added = self._vector_store.add_text(text, metadata=meta)
            except Exception as e:
                logger.warning("벡터 스토어 추가 실패: %s", e)

        logger.info("멀티모달 파일 인제스트 완료: %s (%s, %d자)",
                    os.path.basename(file_path), ftype, len(text))

        return {
            'success': True,
            'file_type': ftype,
            'text_length': len(text),
            'chunks_added': chunks_added,
        }

    def query_multimodal(
        self,
        query: str,
        image_path: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        멀티모달 쿼리 (텍스트 + 이미지)

        이미지가 있으면 Gemini Vision으로 이미지 설명 생성 후 텍스트 쿼리에 통합
        """
        effective_query = query

        if image_path and os.path.exists(image_path):
            try:
                image_text = _extract_text_from_image_gemini(image_path)
                effective_query = f"{query}\n[이미지 컨텍스트]: {image_text[:500]}"
                logger.info("이미지 컨텍스트 통합: %d자", len(image_text))
            except Exception as e:
                logger.warning("이미지 처리 실패: %s", e)

        # 벡터 스토어 검색
        if not self._vector_store:
            return {'results': [], 'error': '벡터 스토어 미초기화'}

        try:
            results = self._vector_store.search(effective_query, top_k=top_k)
            return {
                'query': query,
                'effective_query_length': len(effective_query),
                'results': results,
            }
        except Exception as e:
            return {'results': [], 'error': str(e)}
