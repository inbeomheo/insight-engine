import type { StyleOption } from './types';

export const STYLE_OPTIONS: StyleOption[] = [
  { id: 'blog_seo', label: 'Blog+SEO', emoji: '🔍' },
  { id: 'summary', label: '요약', emoji: '⚡' },
  { id: 'tutorial', label: '튜토리얼', emoji: '📚' },
  { id: 'qna', label: 'Q&A', emoji: '❓' },
  { id: 'app_ideas', label: '앱 아이디어', emoji: '💡' },
  { id: 'yozm_it', label: '요즘IT', emoji: '💻' },
  { id: 'brunch_essay', label: '브런치', emoji: '✍️' },
  { id: 'naver_popular', label: '네이버', emoji: '💚' },
  { id: 'sns_post', label: 'SNS', emoji: '📱' },
  { id: 'newsletter', label: '뉴스레터', emoji: '📧' },
  { id: 'show_notes', label: '쇼노트', emoji: '🎙️' },
  { id: 'shorts_script', label: 'Shorts', emoji: '🎬' },
  { id: 'geo_seo', label: 'GEO', emoji: '🧭' },
  { id: 'course', label: 'AI 코스', emoji: '🎓' },
];

export const LENGTH_OPTIONS = [
  { value: 'short' as const, label: '짧게', desc: '500~800자' },
  { value: 'medium' as const, label: '보통', desc: '1,000~1,500자' },
  { value: 'long' as const, label: '길게', desc: '2,000~3,000자' },
];

export const WRITING_STYLE_OPTIONS = [
  { value: 'conversational' as const, label: '대화체' },
  { value: 'explanatory' as const, label: '설명체' },
  { value: 'casual' as const, label: '캐주얼' },
  { value: 'expert' as const, label: '전문가' },
];

export const LANGUAGE_OPTIONS = [
  { value: 'ko' as const, label: '한국어' },
  { value: 'en' as const, label: 'English' },
  { value: 'ja' as const, label: '日本語' },
];

export const STORAGE_KEYS = {
  REPORTS: 'insight-engine-reports',
  PROVIDER: 'insight-engine-selected-provider',
  MODEL: 'insight-engine-selected-model',
  CUSTOM_STYLES: 'insight-engine-custom-styles',
  ONBOARDING_DONE: 'insight-engine-onboarding-done',
  OLLAMA_BASE_URL: 'insight-engine-ollama-base-url',
  WEBHOOK_URL: 'insight-engine-webhook-url',
} as const;

export const YOUTUBE_URL_REGEX =
  /^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)[\w-]+/;

export function extractVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([\w-]+)/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}

// 지원하는 소스 타입
export type SourceType = 'youtube' | 'arxiv' | 'rss' | 'webpage' | 'podcast';

// 소스 타입별 배지 레이블
export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  youtube: 'YouTube',
  arxiv: 'arXiv',
  rss: 'RSS',
  webpage: 'Web',
  podcast: 'Podcast',
};

const _RSS_PATTERN =
  /\/feed\/?$|\/rss\/?$|\/atom\/?$|\.rss$|\.atom$|\.xml$|\/feed\.xml$|type=rss|format=rss|feed=rss/i;

const _ARXIV_ID_PATTERN = /^\d{4}\.\d{4,5}(v\d+)?$|^[a-z-]+(\.[A-Z]{2})?\/\d{7}$/i;

/**
 * URL을 분석하여 소스 타입을 자동 감지합니다.
 */
export function detectSourceType(url: string): SourceType {
  const trimmed = url.trim();

  // 팟캐스트 (Spotify 에피소드, Apple Podcasts, 일반 오디오)
  if (/open\.spotify\.com\/episode\//i.test(trimmed)) return 'podcast';
  if (/podcasts\.apple\.com\/.+\/podcast\//i.test(trimmed)) return 'podcast';
  if (/\.(mp3|m4a|ogg|wav|flac|aac)(\?|$)/i.test(trimmed)) return 'podcast';
  if (/anchor\.fm|podbean\.com|soundcloud\.com/i.test(trimmed)) return 'podcast';

  // YouTube
  if (/youtube\.com|youtu\.be/i.test(trimmed)) return 'youtube';

  // arXiv
  if (/arxiv\.org\/(abs|pdf|html)\//i.test(trimmed)) return 'arxiv';

  // 순수 arXiv ID
  const bare = trimmed.replace(/^https?:\/\//, '').replace(/\/$/, '');
  if (_ARXIV_ID_PATTERN.test(bare)) return 'arxiv';

  // RSS
  if (_RSS_PATTERN.test(trimmed)) return 'rss';

  // 기본: 웹페이지
  return 'webpage';
}
