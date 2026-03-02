"""
내보내기 라우트 — DOCX 변환
"""
import io
import re as re_module

from flask import request, jsonify, current_app, send_file

from routes.blog_routes import blog_bp
from services.supabase_service import require_auth


@blog_bp.route('/api/export/docx', methods=['POST'])
@require_auth
def export_docx():
    """마크다운 콘텐츠를 DOCX 파일로 변환하여 반환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'AI 생성 결과')
        content = data.get('content', '')

        if not content:
            return jsonify({'error': '변환할 콘텐츠가 없습니다.'}), 400

        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # 기본 스타일 설정
        style = doc.styles['Normal']
        style.font.name = 'Malgun Gothic'
        style.font.size = Pt(11)
        style.paragraph_format.line_spacing = 1.5

        # 제목
        heading = doc.add_heading(title, level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 마크다운 → docx 변환
        _markdown_to_docx(doc, content)

        # BytesIO에 저장
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        safe_title = re_module.sub(r'[^\w\s가-힣-]', '', title)[:30].strip() or 'content'
        filename = f'{safe_title}.docx'

        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )

    except ImportError:
        return jsonify({'error': 'python-docx 패키지가 설치되지 않았습니다.'}), 500
    except Exception as e:
        current_app.logger.error(f"DOCX export failed: {e}")
        return jsonify({'error': 'DOCX 변환 중 오류가 발생했습니다.'}), 500


def _markdown_to_docx(doc, markdown_text):
    """마크다운 텍스트를 docx Document에 변환하여 추가합니다."""
    from docx.shared import Pt
    from docx.oxml.ns import qn

    lines = markdown_text.split('\n')
    i = 0
    in_list = False
    in_table = False
    table_rows = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 빈 줄
        if not stripped:
            if in_table and table_rows:
                _add_table_to_docx(doc, table_rows)
                table_rows = []
                in_table = False
            i += 1
            continue

        # 테이블 행 (| ... | 형식)
        if stripped.startswith('|') and stripped.endswith('|'):
            # 구분선 행 (|---|---|) 건너뛰기
            if re_module.match(r'^\|[\s\-:]+\|$', stripped):
                i += 1
                continue
            in_table = True
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            table_rows.append(cells)
            i += 1
            continue

        # 테이블 종료
        if in_table and table_rows:
            _add_table_to_docx(doc, table_rows)
            table_rows = []
            in_table = False

        # 헤딩
        if stripped.startswith('###'):
            text = stripped.lstrip('#').strip()
            doc.add_heading(_strip_markdown_formatting(text), level=3)
        elif stripped.startswith('##'):
            text = stripped.lstrip('#').strip()
            doc.add_heading(_strip_markdown_formatting(text), level=2)
        elif stripped.startswith('#'):
            text = stripped.lstrip('#').strip()
            doc.add_heading(_strip_markdown_formatting(text), level=2)

        # 수평선
        elif stripped in ('---', '***', '___'):
            p = doc.add_paragraph()
            p_format = p.paragraph_format
            p_format.space_before = Pt(6)
            p_format.space_after = Pt(6)

        # 인용문
        elif stripped.startswith('>'):
            text = stripped.lstrip('>').strip()
            p = doc.add_paragraph(style='Quote') if 'Quote' in [s.name for s in doc.styles] else doc.add_paragraph()
            _add_formatted_text(p, text)

        # 비순서 목록
        elif stripped.startswith(('- ', '* ', '+ ')):
            text = stripped[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            _add_formatted_text(p, text)

        # 순서 목록
        elif re_module.match(r'^\d+\.\s', stripped):
            text = re_module.sub(r'^\d+\.\s', '', stripped).strip()
            p = doc.add_paragraph(style='List Number')
            _add_formatted_text(p, text)

        # 일반 텍스트
        else:
            p = doc.add_paragraph()
            _add_formatted_text(p, stripped)

        i += 1

    # 남은 테이블 처리
    if in_table and table_rows:
        _add_table_to_docx(doc, table_rows)


def _strip_markdown_formatting(text):
    """마크다운 인라인 서식을 제거합니다."""
    text = re_module.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re_module.sub(r'\*(.+?)\*', r'\1', text)
    text = re_module.sub(r'`(.+?)`', r'\1', text)
    return text


def _add_formatted_text(paragraph, text):
    """마크다운 인라인 서식을 docx Run으로 변환하여 추가합니다."""
    # 볼드, 이탤릭, 코드 패턴 분리
    pattern = re_module.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)')
    last_end = 0

    for match in pattern.finditer(text):
        # 매치 전 일반 텍스트
        if match.start() > last_end:
            paragraph.add_run(text[last_end:match.start()])

        if match.group(2):  # 볼드
            run = paragraph.add_run(match.group(2))
            run.bold = True
        elif match.group(3):  # 이탤릭
            run = paragraph.add_run(match.group(3))
            run.italic = True
        elif match.group(4):  # 코드
            run = paragraph.add_run(match.group(4))
            run.font.name = 'Consolas'

        last_end = match.end()

    # 나머지 텍스트
    if last_end < len(text):
        paragraph.add_run(text[last_end:])


@blog_bp.route('/api/export/markdown', methods=['POST'])
@require_auth
def export_markdown():
    """마크다운 파일로 내보냅니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'AI 생성 결과')
        content = data.get('content', '')
        if not content:
            return jsonify({'error': '변환할 콘텐츠가 없습니다.'}), 400

        from services.export_service import export_markdown as _export_md
        buffer = _export_md(title, content)
        safe_title = re_module.sub(r'[^\w\s가-힣-]', '', title)[:30].strip() or 'content'

        return send_file(buffer, mimetype='text/markdown', as_attachment=True, download_name=f'{safe_title}.md')
    except Exception as e:
        current_app.logger.error(f"MD export failed: {e}")
        return jsonify({'error': '마크다운 내보내기 실패'}), 500


@blog_bp.route('/api/export/txt', methods=['POST'])
@require_auth
def export_txt():
    """텍스트 파일로 내보냅니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'AI 생성 결과')
        content = data.get('content', '')
        if not content:
            return jsonify({'error': '변환할 콘텐츠가 없습니다.'}), 400

        from services.export_service import export_txt as _export_txt
        buffer = _export_txt(title, content)
        safe_title = re_module.sub(r'[^\w\s가-힣-]', '', title)[:30].strip() or 'content'

        return send_file(buffer, mimetype='text/plain', as_attachment=True, download_name=f'{safe_title}.txt')
    except Exception as e:
        current_app.logger.error(f"TXT export failed: {e}")
        return jsonify({'error': '텍스트 내보내기 실패'}), 500


@blog_bp.route('/api/export/zip', methods=['POST'])
@require_auth
def export_zip():
    """ZIP 패키지 (DOCX+MD+TXT+meta.json)로 내보냅니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'AI 생성 결과')
        content = data.get('content', '')
        if not content:
            return jsonify({'error': '변환할 콘텐츠가 없습니다.'}), 400

        from services.export_service import export_zip as _export_zip
        buffer = _export_zip(title, content)
        safe_title = re_module.sub(r'[^\w\s가-힣-]', '', title)[:30].strip() or 'content'

        return send_file(buffer, mimetype='application/zip', as_attachment=True, download_name=f'{safe_title}.zip')
    except Exception as e:
        current_app.logger.error(f"ZIP export failed: {e}")
        return jsonify({'error': 'ZIP 내보내기 실패'}), 500


def _add_table_to_docx(doc, rows):
    """테이블 데이터를 docx Table로 추가합니다."""
    if not rows:
        return

    num_cols = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=num_cols)
    table.style = 'Table Grid'

    for i, row in enumerate(rows):
        for j, cell_text in enumerate(row):
            if j < num_cols:
                cell = table.cell(i, j)
                cell.text = _strip_markdown_formatting(cell_text)
                # 첫 행(헤더) 볼드
                if i == 0:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True
