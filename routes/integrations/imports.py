"""외부 소스 임포트 — Notion, Google Docs, 북마크, RSS, 이메일."""
import os

from flask import request, jsonify, current_app, g

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth
from utils.responses import handle_error


# ── Notion 연동 ──────────────────────────────────────


@blog_bp.route('/api/notion/import', methods=['POST'])
@require_auth
def notion_import():
    """Notion 페이지 URL → 콘텐츠 추출"""
    from services.export.notion_service import extract_notion_page

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    page_url = data.get('url', '').strip()
    if not page_url:
        return jsonify({'error': 'Notion 페이지 URL이 필요합니다.'}), 400

    # API 키: 요청 본문 > 환경변수
    api_key = data.get('api_key') or os.getenv('NOTION_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'Notion API 키가 설정되지 않았습니다.'}), 400

    try:
        result = extract_notion_page(page_url, api_key)
        return jsonify(result)
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f'Notion import failed: {e}')
        return jsonify({'error': 'Notion 페이지 가져오기 중 오류가 발생했습니다.'}), 500


@blog_bp.route('/api/notion/status', methods=['GET'])
def notion_status():
    """Notion API 키 설정 여부 확인"""
    configured = bool(os.getenv('NOTION_API_KEY', ''))
    return jsonify({'configured': configured})


# ── Google Docs 연동 ──────────────────────────────────────


@blog_bp.route('/api/gdocs/import', methods=['POST'])
@require_auth
def gdocs_import():
    """Google Docs URL → 콘텐츠 추출"""
    from services.export.gdocs_service import extract_google_doc

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    doc_url = data.get('url', '').strip()
    if not doc_url:
        return jsonify({'error': 'Google Docs URL이 필요합니다.'}), 400

    api_key = data.get('api_key') or os.getenv('GOOGLE_API_KEY', '')

    try:
        result = extract_google_doc(doc_url, api_key or None)
        return jsonify(result)
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f'Google Docs import failed: {e}')
        return jsonify({'error': 'Google Docs 가져오기 중 오류가 발생했습니다.'}), 500


# ── RSS 구독 ──────────────────────────────────────


@blog_bp.route('/api/rss/subscribe', methods=['POST'])
@require_auth
def rss_subscribe():
    """RSS 피드 구독 추가"""
    from services.platform.rss_subscription_service import subscribe

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    feed_url = data.get('feed_url')
    if not feed_url:
        return jsonify({'error': 'feed_url은 필수입니다.'}), 400

    title = data.get('title', '')
    user_id = getattr(g, 'user_id', None) or 'anonymous'

    try:
        sub = subscribe(user_id, feed_url, title)
        return jsonify(sub), 201
    except ValueError as e:
        return handle_error(str(e))


@blog_bp.route('/api/rss/list', methods=['GET'])
@require_auth
def rss_list():
    """구독 목록 조회"""
    from services.platform.rss_subscription_service import list_subscriptions

    user_id = getattr(g, 'user_id', None) or 'anonymous'
    subs = list_subscriptions(user_id)
    return jsonify({'subscriptions': subs})


@blog_bp.route('/api/rss/unsubscribe/<feed_id>', methods=['DELETE'])
@require_auth
def rss_unsubscribe(feed_id: str):
    """RSS 구독 해제"""
    from services.platform.rss_subscription_service import unsubscribe

    user_id = getattr(g, 'user_id', None) or 'anonymous'
    success = unsubscribe(user_id, feed_id)
    if not success:
        return jsonify({'error': '해당 구독을 찾을 수 없습니다.'}), 404
    return jsonify({'success': True})


# ── 북마크 가져오기 ──────────────────────────────────────


@blog_bp.route('/api/bookmarks/parse', methods=['POST'])
@require_auth
def bookmarks_parse():
    """북마크 HTML 파일 파싱"""
    from services.data.bookmark_import_service import parse_bookmarks

    if 'file' not in request.files:
        return jsonify({'error': '파일이 필요합니다.'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '파일명이 비어 있습니다.'}), 400

    # HTML 파일 검증
    if not file.filename.lower().endswith(('.html', '.htm')):
        return jsonify({'error': 'HTML 파일만 지원합니다.'}), 400

    try:
        html_content = file.read().decode('utf-8', errors='replace')
        bookmarks = parse_bookmarks(html_content)
        return jsonify({'bookmarks': bookmarks, 'count': len(bookmarks)})
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Bookmark parse failed: {e}")
        return jsonify({'error': '북마크 파싱 중 오류가 발생했습니다.'}), 500


# ── 이메일 뉴스레터 인제스트 ──────────────────────────────────────


@blog_bp.route('/api/email/ingest', methods=['POST'])
@require_auth
def email_ingest():
    """이메일 뉴스레터에서 콘텐츠를 추출합니다.

    - .eml 파일 업로드: multipart/form-data의 'file' 필드
    - 포워딩 텍스트: JSON의 'raw_text' 필드
    """
    from services.content.email_ingest_service import parse_email_file, parse_forwarded_email

    # 파일 업로드 모드
    if 'file' in request.files:
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': '파일명이 비어 있습니다.'}), 400
        if not file.filename.lower().endswith('.eml'):
            return jsonify({'error': '.eml 파일만 지원합니다.'}), 400

        try:
            result = parse_email_file(file)
            return jsonify(result)
        except ValueError as e:
            return handle_error(str(e))
        except Exception as e:
            current_app.logger.error(f'Email ingest failed: {e}')
            return jsonify({'error': '이메일 파싱 중 오류가 발생했습니다.'}), 500

    # 텍스트 모드 (포워딩된 이메일)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '.eml 파일 또는 raw_text가 필요합니다.'}), 400

    raw_text = data.get('raw_text', '').strip()
    if not raw_text:
        return jsonify({'error': 'raw_text가 비어 있습니다.'}), 400

    try:
        result = parse_forwarded_email(raw_text)
        return jsonify(result)
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f'Email ingest (text) failed: {e}')
        return jsonify({'error': '이메일 텍스트 파싱 중 오류가 발생했습니다.'}), 500
