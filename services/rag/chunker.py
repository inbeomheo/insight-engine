"""문서 텍스트 분할 (청킹)"""
import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    """텍스트를 chunk_size 단위로 분할, overlap 문자 겹침"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """파일에서 텍스트 추출 (.txt, .md, .pdf)"""
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''

    try:
        if ext in ('txt', 'md'):
            return file_bytes.decode('utf-8', errors='ignore')

        if ext == 'pdf':
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(file_bytes))
            sep = '\n'
            return sep.join(page.extract_text() or '' for page in reader.pages)

        raise ValueError(f"지원하지 않는 파일 형식: {ext}")
    except ValueError:
        raise
    except Exception as e:
        logger.error('파일 텍스트 추출 실패 (%s): %s', filename, e)
        raise RuntimeError(f'파일 텍스트 추출 실패: {e}') from e
