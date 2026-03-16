"""
OpenAPI 3.0 스펙 생성 서비스 (F7-08)

Flask 앱의 주요 라우트를 기반으로 OpenAPI 3.0 문서를 생성합니다.
"""
from typing import Any
import logging

logger = logging.getLogger(__name__)


def build_openapi_spec(app_title: str = 'Insight Engine API',
                       version: str = '1.0.0',
                       server_url: str = 'http://localhost:5001') -> dict:
    """OpenAPI 3.0 스펙 dict 반환"""

    try:
        spec: dict[str, Any] = {
            'openapi': '3.0.3',
            'info': {
                'title': app_title,
                'version': version,
                'description': (
                    'YouTube 영상 URL로 AI 콘텐츠를 생성하는 Insight Engine API. '
                    'LiteLLM을 통해 Gemini, DeepSeek, Zhipu GLM, Ollama 등 다양한 '
                    'AI 프로바이더를 지원합니다.'
                ),
                'contact': {'name': 'Insight Engine', 'url': server_url},
                'license': {'name': 'MIT'},
            },
            'servers': [{'url': server_url, 'description': '기본 서버'}],
            'security': [{'BearerAuth': []}],
            'components': {
                'securitySchemes': {
                    'BearerAuth': {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'Supabase JWT',
                    }
                },
                'schemas': {
                    'GenerateRequest': {
                        'type': 'object',
                        'required': ['urls', 'style_id'],
                        'properties': {
                            'urls': {
                                'type': 'array',
                                'items': {'type': 'string', 'format': 'uri'},
                                'description': 'YouTube 영상 URL 목록',
                                'minItems': 1,
                            },
                            'style_id': {
                                'type': 'string',
                                'description': '콘텐츠 스타일 ID',
                                'example': 'blog_seo',
                            },
                            'modifiers': {
                                'type': 'object',
                                'properties': {
                                    'length': {
                                        'type': 'string',
                                        'enum': ['short', 'medium', 'long'],
                                        'default': 'medium',
                                    },
                                    'language': {
                                        'type': 'string',
                                        'enum': ['ko', 'en', 'ja'],
                                        'default': 'ko',
                                    },
                                    'writing_style': {
                                        'type': 'string',
                                        'enum': ['conversational', 'explanatory', 'casual', 'expert'],
                                        'default': 'conversational',
                                    },
                                },
                            },
                            'provider': {'type': 'string', 'description': 'AI 프로바이더'},
                            'model': {'type': 'string', 'description': 'AI 모델 ID'},
                        },
                    },
                    'GenerateResponse': {
                        'type': 'object',
                        'properties': {
                            'title': {'type': 'string'},
                            'content': {'type': 'string', 'description': '마크다운 콘텐츠'},
                            'html': {'type': 'string', 'description': 'HTML 변환 콘텐츠'},
                            'usage': {
                                'type': 'object',
                                'properties': {
                                    'prompt_tokens': {'type': 'integer'},
                                    'completion_tokens': {'type': 'integer'},
                                    'total_tokens': {'type': 'integer'},
                                },
                            },
                            'comment_summary_included': {'type': 'boolean'},
                        },
                    },
                    'ErrorResponse': {
                        'type': 'object',
                        'properties': {
                            'error': {'type': 'string', 'description': '오류 메시지'},
                        },
                    },
                    'PluginInfo': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'description': {'type': 'string'},
                        },
                    },
                },
            },
            'paths': {
                '/generate': {
                    'post': {
                        'summary': 'AI 콘텐츠 생성',
                        'operationId': 'generateContent',
                        'tags': ['Content'],
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/GenerateRequest'}
                                }
                            },
                        },
                        'responses': {
                            '200': {
                                'description': '생성 성공',
                                'content': {
                                    'application/json': {
                                        'schema': {'$ref': '#/components/schemas/GenerateResponse'}
                                    }
                                },
                            },
                            '400': {
                                'description': '잘못된 요청',
                                'content': {
                                    'application/json': {
                                        'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                                    }
                                },
                            },
                            '401': {'description': '인증 실패'},
                            '429': {'description': '사용량 초과'},
                        },
                    }
                },
                '/api/mcp/plugins': {
                    'get': {
                        'summary': 'MCP 플러그인 목록',
                        'operationId': 'listPlugins',
                        'tags': ['Plugins'],
                        'security': [],
                        'responses': {
                            '200': {
                                'description': '플러그인 목록',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'plugins': {
                                                    'type': 'array',
                                                    'items': {'$ref': '#/components/schemas/PluginInfo'},
                                                }
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                '/api/mcp/publish': {
                    'post': {
                        'summary': 'MCP 플러그인으로 콘텐츠 발행',
                        'operationId': 'publishContent',
                        'tags': ['Plugins'],
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'required': ['plugin_id', 'title', 'content'],
                                        'properties': {
                                            'plugin_id': {'type': 'string'},
                                            'title': {'type': 'string'},
                                            'content': {'type': 'string'},
                                        },
                                    }
                                }
                            },
                        },
                        'responses': {
                            '200': {
                                'description': '발행 성공',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'success': {'type': 'boolean'},
                                                'message': {'type': 'string'},
                                                'url': {'type': 'string', 'nullable': True},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                '/api/schedule': {
                    'get': {
                        'summary': '예약 발행 목록 조회',
                        'operationId': 'listSchedules',
                        'tags': ['Schedule'],
                        'responses': {
                            '200': {
                                'description': '예약 목록',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'schedules': {'type': 'array', 'items': {'type': 'object'}}
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    },
                    'post': {
                        'summary': '예약 발행 생성',
                        'operationId': 'createSchedule',
                        'tags': ['Schedule'],
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'required': ['title', 'content', 'target_plugin', 'scheduled_at'],
                                        'properties': {
                                            'title': {'type': 'string'},
                                            'content': {'type': 'string'},
                                            'html': {'type': 'string'},
                                            'target_plugin': {'type': 'string'},
                                            'scheduled_at': {'type': 'string', 'format': 'date-time'},
                                        },
                                    }
                                }
                            },
                        },
                        'responses': {
                            '201': {'description': '예약 생성 성공'},
                            '400': {'description': '잘못된 요청'},
                        },
                    },
                },
                '/api/zapier/trigger': {
                    'post': {
                        'summary': 'Zapier 트리거 — 콘텐츠 생성 완료 이벤트',
                        'operationId': 'zapierTrigger',
                        'tags': ['Integrations'],
                        'security': [],
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'url': {'type': 'string'},
                                            'style_id': {'type': 'string'},
                                        },
                                    }
                                }
                            },
                        },
                        'responses': {'200': {'description': '트리거 성공'}},
                    }
                },
                '/api/webhooks/slack': {
                    'post': {
                        'summary': 'Slack 이벤트 웹훅',
                        'operationId': 'slackWebhook',
                        'tags': ['Integrations'],
                        'security': [],
                        'responses': {'200': {'description': '처리 완료'}},
                    }
                },
                '/api/webhooks/discord': {
                    'post': {
                        'summary': 'Discord Interactions 웹훅',
                        'operationId': 'discordWebhook',
                        'tags': ['Integrations'],
                        'security': [],
                        'responses': {'200': {'description': '처리 완료'}},
                    }
                },
                '/api/webhooks/telegram': {
                    'post': {
                        'summary': 'Telegram 웹훅',
                        'operationId': 'telegramWebhook',
                        'tags': ['Integrations'],
                        'security': [],
                        'responses': {'200': {'description': '처리 완료'}},
                    }
                },
            },
            'tags': [
                {'name': 'Content', 'description': 'AI 콘텐츠 생성'},
                {'name': 'Plugins', 'description': 'MCP 플러그인 발행'},
                {'name': 'Schedule', 'description': '예약 발행'},
                {'name': 'Integrations', 'description': '외부 서비스 통합'},
            ],
        }

        return spec
    except Exception as e:
        logger.error("build_openapi_spec 실패: %s", e, exc_info=True)
        return {}
