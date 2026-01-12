"""
블로그 콘텐츠 생성 API 라우트
"""
import concurrent.futures
import json
import time
from typing import Dict

from flask import Blueprint, request, jsonify, current_app, render_template, g

from config import get_model_max_tokens
from services import ai_service, content_service
from services.content_service import clear_cache
from services.supabase_service import (
    require_auth, is_supabase_enabled, get_usage, decrement_usage
)

blog_bp = Blueprint('blog', __name__)
_CLIENT_TRACKER: Dict[str, float] = {}

DEFAULT_MODEL = 'gpt-4o'
DEFAULT_STYLE = 'detailed'
MAX_BATCH_URLS = 10
MAX_BATCH_WORKERS = 5
BATCH_CONTENT_TOKEN_LIMIT = 3000


def _extract_client_id(req) -> str:
    """요청에서 클라이언트 ID를 추출합니다."""
    data = req.get_json(silent=True)
    if isinstance(data, dict) and data.get('clientId'):
        return str(data['clientId'])

    form_id = req.form.get('clientId')
    if form_id:
        return str(form_id)

    raw = (req.get_data(cache=False, as_text=True) or '').strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get('clientId'):
                return str(parsed['clientId'])
        except json.JSONDecodeError:
            pass  # 잘못된 JSON은 무시하고 빈 문자열 반환

    return ''


def _get_request_data(req):
    """JSON 또는 form 데이터에서 공통 파라미터를 추출합니다.
    API 키는 서버 환경변수에서 관리되므로 요청에서 추출하지 않습니다.
    """
    data = req.get_json(silent=True)
    if isinstance(data, dict) and data:
        return {
            'url': data.get('url'),
            'urls': data.get('urls', []),
            'content': data.get('content'),
            'model': data.get('model', DEFAULT_MODEL),
            'style': data.get('style', DEFAULT_STYLE),
            'modifiers': data.get('modifiers'),
            'custom_prompt': data.get('customPrompt'),
        }

    return {
        'url': req.form.get('url'),
        'urls': [],
        'content': req.form.get('content'),
        'model': req.form.get('model', DEFAULT_MODEL),
        'style': req.form.get('style', DEFAULT_STYLE),
        'modifiers': None,
        'custom_prompt': None,
    }


def _get_style_prompt(style, custom_prompt=None):
    """스타일에 맞는 프롬프트를 반환합니다."""
    if custom_prompt and custom_prompt.strip():
        return custom_prompt.strip()[:2000]
    style_prompts = current_app.config.get('STYLE_PROMPTS', {})
    return style_prompts.get(style, '')


def _handle_error_response(error_msg):
    """에러 메시지에 따른 적절한 HTTP 상태 코드를 반환합니다."""
    if 'API 키' in error_msg or 'authentication' in error_msg.lower():
        return jsonify({'error': error_msg}), 401
    return jsonify({'error': error_msg}), 500


def _fetch_youtube_content(video_id):
    """YouTube 영상의 자막과 댓글을 가져옵니다.
    Supadata API 키는 환경변수에서 자동으로 로드됩니다.

    Returns:
        tuple: (combined_content, error, raw_transcript)
    """
    transcript = content_service.get_transcript(video_id)
    if isinstance(transcript, dict) and transcript.get('error'):
        return None, transcript['error'], None

    comments = content_service.get_top_comments(video_id)
    comments_text = '\n'.join(comments[:20]) if comments else '(댓글 없음)'

    final_content = f"[영상 자막]\n{transcript}\n\n[시청자 댓글]\n{comments_text}"
    return final_content, None, transcript


@blog_bp.route('/')
def home():
    """메인 페이지를 렌더링합니다."""
    return render_template('index.html')


@blog_bp.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """클라이언트 연결 상태를 추적합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    _CLIENT_TRACKER[client_id] = time.time()
    return jsonify({'ok': True})


@blog_bp.route('/api/close', methods=['POST'])
def api_close():
    """클라이언트 연결 종료를 처리합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    _CLIENT_TRACKER.pop(client_id, None)
    return jsonify({'ok': True})


@blog_bp.route('/api/providers', methods=['GET'])
def api_providers():
    """API 키가 설정된 AI 서비스 및 모델 목록을 반환합니다.
    환경변수에 API 키가 설정된 프로바이더만 반환됩니다.
    """
    from config import get_available_providers, SUPADATA_API_KEY

    providers = get_available_providers()
    styles = current_app.config.get('STYLE_OPTIONS', [])

    return jsonify({
        'providers': providers,
        'styles': [{'id': s[0], 'name': s[1]} for s in styles],
        'supadataConfigured': bool(SUPADATA_API_KEY)
    })


@blog_bp.route('/api/cache', methods=['DELETE'])
def api_clear_cache():
    """캐시를 삭제합니다. video_id 파라미터가 있으면 해당 영상만, 없으면 전체 삭제."""
    data = request.get_json(silent=True) or {}
    video_id = data.get('videoId')

    # URL에서 video_id 추출 (URL이 전달된 경우)
    url = data.get('url')
    if url and not video_id:
        video_id = content_service.get_video_id(url)

    deleted = clear_cache(video_id)

    if video_id:
        return jsonify({
            'success': True,
            'message': f'영상 {video_id}의 캐시가 삭제되었습니다.',
            'deleted': deleted
        })
    return jsonify({
        'success': True,
        'message': '전체 캐시가 삭제되었습니다.',
        'deleted': deleted
    })


@blog_bp.route('/api/recommend-style', methods=['POST'])
def recommend_style():
    """YouTube 제목을 분석하여 최적의 스타일과 모디파이어를 AI로 추천합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    """
    try:
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        model = data.get('model', DEFAULT_MODEL)

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        title = content_service.get_content_title(url) or 'YouTube 영상'

        style_options = current_app.config.get('STYLE_OPTIONS', [])
        style_list = ', '.join([f"{s[0]}({s[1]})" for s in style_options])

        prompt = f"""다음 YouTube 영상 제목을 분석하여 가장 적합한 콘텐츠 스타일을 추천해주세요.

영상 제목: {title}

사용 가능한 스타일: {style_list}

다음 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{
    "style": "추천 스타일 ID",
    "reason": "추천 이유 (20자 이내)",
    "modifiers": {{
        "length": "short|medium|long",
        "tone": "professional|friendly|humorous",
        "emoji": "use|none"
    }}
}}"""

        response = ai_service.create_content(
            prompt,
            model,
            style_prompt=""
        )

        import re
        content = response.get('content', '')
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            recommendation = json.loads(json_match.group())
            recommendation['title'] = title
            return jsonify(recommendation)

        return jsonify({
            'style': 'detailed',
            'reason': '기본 추천',
            'modifiers': {'length': 'medium', 'tone': 'professional', 'emoji': 'none'},
            'title': title
        })

    except json.JSONDecodeError:
        return jsonify({
            'style': 'detailed',
            'reason': 'AI 응답 파싱 실패',
            'modifiers': {'length': 'medium', 'tone': 'professional', 'emoji': 'none'},
            'title': title if 'title' in dir() else 'YouTube 영상'
        })
    except Exception as e:
        current_app.logger.error(f"Recommend style failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/api/generate-style', methods=['POST'])
def generate_style():
    """YouTube 제목과 자막을 분석하여 맞춤형 프롬프트를 AI로 생성합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    """
    try:
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        model = data.get('model', DEFAULT_MODEL)

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        title = content_service.get_content_title(url) or 'YouTube 영상'

        transcript = content_service.get_transcript(video_id)
        if isinstance(transcript, dict) and transcript.get('error'):
            transcript_preview = "(자막 없음)"
        else:
            transcript_preview = transcript[:500] if len(transcript) > 500 else transcript

        prompt = f"""다음 YouTube 영상의 제목과 자막 일부를 분석하여, 이 영상 콘텐츠에 최적화된 블로그 작성 프롬프트를 생성해주세요.

영상 제목: {title}
자막 미리보기: {transcript_preview}

다음 JSON 형식으로만 응답해주세요:
{{
    "styleName": "이 스타일의 이름 (10자 이내, 예: '기술 분석', '리뷰 정리')",
    "stylePrompt": "AI가 블로그를 작성할 때 사용할 상세 프롬프트 (200-400자)",
    "description": "이 스타일이 왜 이 영상에 적합한지 (30자 이내)"
}}"""

        response = ai_service.create_content(
            prompt,
            model,
            style_prompt=""
        )

        import re
        content = response.get('content', '')
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            result['title'] = title
            return jsonify(result)

        return jsonify({
            'error': 'AI 응답을 파싱할 수 없습니다.',
            'title': title
        }), 500

    except json.JSONDecodeError:
        return jsonify({
            'error': 'AI 응답 JSON 파싱 실패',
            'title': title if 'title' in dir() else 'YouTube 영상'
        }), 500
    except Exception as e:
        current_app.logger.error(f"Generate style failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/generate', methods=['POST'])
@require_auth
def generate():
    """단일 YouTube URL에서 콘텐츠를 생성합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용.
    """
    try:
        # 사용량 체크
        usage = get_usage(g.user_id)
        if not usage['can_use']:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'usage': usage
            }), 429

        start_time = time.time()
        params = _get_request_data(request)
        url = params['url']

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        # YouTube 원본 제목 가져오기
        youtube_title = content_service.get_content_title(url) or 'YouTube 영상'

        content, error, raw_transcript = _fetch_youtube_content(video_id)
        if error:
            return jsonify({'error': error}), 400

        max_tokens = get_model_max_tokens(params['model'])
        truncated_content = content_service.truncate_text(content, max_tokens)

        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        result, used_prompt = ai_service.create_content(
            truncated_content,
            params['model'],
            style_prompt,
            return_prompt=True,
            modifiers=params['modifiers']
        )

        # 성공 시에만 사용량 차감
        decrement_usage(g.user_id)
        updated_usage = get_usage(g.user_id)

        elapsed_time = round(time.time() - start_time, 2)

        return jsonify({
            **result,
            "prompt": used_prompt,
            "elapsed_time": elapsed_time,
            "youtube_title": youtube_title,
            "transcript": raw_transcript,
            "usage": updated_usage
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Generate failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/regenerate', methods=['POST'])
@require_auth
def regenerate():
    """기존 콘텐츠를 새로운 스타일로 재생성합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용.
    """
    try:
        # 사용량 체크
        usage = get_usage(g.user_id)
        if not usage['can_use']:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'usage': usage
            }), 429

        params = _get_request_data(request)
        content = params['content']

        if not content:
            return jsonify({'error': '재생성할 콘텐츠가 없습니다'}), 400

        style_prompt = _get_style_prompt(params['style'])
        result, used_prompt = ai_service.create_content(
            content,
            params['model'],
            style_prompt,
            return_prompt=True
        )

        # 성공 시에만 사용량 차감
        decrement_usage(g.user_id)
        updated_usage = get_usage(g.user_id)

        return jsonify({**result, "prompt": used_prompt, "usage": updated_usage})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Regenerate failed: {e}")
        return _handle_error_response(str(e))


def _process_single_url(app, url, model, style, modifiers, custom_prompt):
    """배치 처리에서 단일 URL을 처리하는 헬퍼 함수입니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    """
    with app.app_context():
        try:
            current_app.logger.info(f"Processing URL: {url}")

            if not content_service.is_youtube_url(url):
                return {
                    'success': False,
                    'url': url,
                    'title': 'URL 오류',
                    'error': '유효한 YouTube URL이 아닙니다.'
                }

            video_id = content_service.get_video_id(url)
            if not video_id:
                return {
                    'success': False,
                    'url': url,
                    'title': 'YouTube 영상',
                    'error': '유효하지 않은 YouTube URL입니다'
                }

            title = content_service.get_content_title(url) or 'YouTube 영상'
            current_app.logger.info(f"Content title: {title}")

            content, error, raw_transcript = _fetch_youtube_content(video_id)
            if error:
                return {
                    'success': False,
                    'url': url,
                    'title': title,
                    'error': error
                }

            max_tokens = get_model_max_tokens(model)
            content = content_service.truncate_text(content, max_tokens)
            style_prompt = _get_style_prompt(style, custom_prompt)

            result, used_prompt = ai_service.create_content(
                content, model, style_prompt,
                return_prompt=True, modifiers=modifiers
            )

            return {
                'success': True,
                'url': url,
                'title': result.get('title', title),
                'content': result.get('content', ''),
                'html': result.get('html', ''),
                'prompt': used_prompt
            }

        except Exception as e:
            current_app.logger.error(f"Error processing URL {url}: {e}")
            return {
                'success': False,
                'url': url,
                'title': '오류 발생',
                'error': f'처리 중 오류 발생: {str(e)}'
            }


@blog_bp.route('/generate-batch', methods=['POST'])
@require_auth
def generate_batch():
    """여러 URL을 배치로 처리합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (배치 전체가 1회로 계산).
    """
    try:
        # 사용량 체크
        usage = get_usage(g.user_id)
        if not usage['can_use']:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'usage': usage
            }), 429

        current_app.logger.info("Batch generate request received")

        data = request.get_json()
        current_app.logger.info(f"Request data: {data}")

        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({'error': 'JSON 데이터가 제공되지 않았습니다'}), 400

        urls = data.get('urls', [])
        model = data.get('model', DEFAULT_MODEL)
        style = data.get('style', DEFAULT_STYLE)
        modifiers = data.get('modifiers')
        custom_prompt = data.get('customPrompt')

        current_app.logger.info(f"URLs to process: {urls}, Model: {model}, Style: {style}")

        if not urls or not isinstance(urls, list):
            return jsonify({'error': 'URL 목록이 제공되지 않았습니다'}), 400
        if len(urls) > MAX_BATCH_URLS:
            return jsonify({'error': f'최대 {MAX_BATCH_URLS}개의 URL만 처리할 수 있습니다'}), 400

        app = current_app._get_current_object()
        results = [None] * len(urls)
        combined_content = []

        current_app.logger.info(f"Starting to process {len(urls)} URLs concurrently")

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_BATCH_WORKERS) as executor:
            future_to_index = {
                executor.submit(
                    _process_single_url, app, url, model, style,
                    modifiers, custom_prompt
                ): i for i, url in enumerate(urls)
            }

            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                    current_app.logger.info(f"Completed processing URL {index + 1}: {result.get('success', False)}")

                    if result['success'] and isinstance(result.get('content', ''), str):
                        combined_content.append(result['content'])
                except Exception as e:
                    current_app.logger.error(f"Exception in future for URL {index + 1}: {e}")
                    results[index] = {
                        'success': False,
                        'url': urls[index],
                        'title': '오류 발생',
                        'error': f'처리 중 예외 발생: {str(e)}'
                    }

        url_to_result = {result['url']: result for result in results if result}
        ordered_results = [
            url_to_result.get(url, {'success': False, 'url': url, 'error': '처리 실패'})
            for url in urls
        ]

        final_combined_content = "\n\n=== 다음 콘텐츠 ===\n\n".join(combined_content) if combined_content else ""
        success_count = sum(1 for r in ordered_results if r.get('success'))
        fail_count = len(ordered_results) - success_count

        current_app.logger.info(f"Batch processing completed. Success: {success_count}, Failed: {fail_count}")

        # 성공한 결과가 1개 이상이면 사용량 차감 (배치 전체가 1회로 계산)
        if success_count > 0:
            decrement_usage(g.user_id)

        updated_usage = get_usage(g.user_id)

        return jsonify({
            'success': True,
            'results': ordered_results,
            'content': final_combined_content,
            'total_processed': len(urls),
            'successful': success_count,
            'failed': fail_count,
            'usage': updated_usage
        })

    except ValueError as e:
        current_app.logger.error(f"ValueError in batch generate: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Batch generate failed: {e}", exc_info=True)
        return _handle_error_response(f'배치 처리 중 오류: {str(e)}')


@blog_bp.route('/api/mindmap', methods=['POST'])
@require_auth
def generate_mindmap():
    """기존 콘텐츠를 마인드맵 형식의 마크다운으로 변환합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용.
    """
    try:
        # 사용량 체크
        usage = get_usage(g.user_id)
        if not usage['can_use']:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'usage': usage
            }), 429

        start_time = time.time()
        data = request.get_json(silent=True) or {}
        content = data.get('content')
        model = data.get('model', DEFAULT_MODEL)

        if not content:
            return jsonify({'error': '마인드맵으로 변환할 콘텐츠가 필요합니다.'}), 400

        # MINDMAP_PROMPT 가져오기
        style_prompts = current_app.config.get('STYLE_PROMPTS', {})
        mindmap_prompt = style_prompts.get('mindmap', '')

        if not mindmap_prompt:
            return jsonify({'error': '마인드맵 프롬프트가 설정되지 않았습니다.'}), 500

        # 콘텐츠 길이 제한 (토큰 절약)
        max_tokens = get_model_max_tokens(model)
        truncated_content = content_service.truncate_text(content, min(max_tokens, 50000))

        result = ai_service.create_content(
            truncated_content,
            model,
            mindmap_prompt
        )

        # 성공 시에만 사용량 차감
        decrement_usage(g.user_id)
        updated_usage = get_usage(g.user_id)

        elapsed_time = round(time.time() - start_time, 2)

        # 마인드맵용 마크다운 콘텐츠 반환
        return jsonify({
            'success': True,
            'markdown': result.get('content', ''),
            'elapsed_time': elapsed_time,
            'usage': updated_usage
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Mindmap generation failed: {e}")
        return _handle_error_response(str(e))
