"""문서 텍스트 분할 (청킹)"""
import logging
import os
import tempfile

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
            from services.content.document_ingest_service import extract_text

            file_descriptor = None
            temp_path = None
            try:
                file_descriptor, temp_path = tempfile.mkstemp(
                    prefix='rag_pdf_', suffix='.pdf'
                )
                os.fchmod(file_descriptor, 0o600)
                with os.fdopen(file_descriptor, 'wb') as temp_file:
                    file_descriptor = None
                    temp_file.write(file_bytes)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                result = extract_text(temp_path, 'application/pdf')
                return str(result.get('content') or '')
            finally:
                if file_descriptor is not None:
                    os.close(file_descriptor)
                if temp_path:
                    try:
                        os.remove(temp_path)
                    except FileNotFoundError:
                        pass

        raise ValueError(f"지원하지 않는 파일 형식: {ext}")
    except ValueError:
        raise
    except Exception as e:
        logger.error('파일 텍스트 추출 실패 (%s): %s', filename, e)
        raise RuntimeError(f'파일 텍스트 추출 실패: {e}') from e
