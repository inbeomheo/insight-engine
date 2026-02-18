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

export const STORAGE_KEYS = {
  REPORTS: 'insight-engine-reports',
  PROVIDER: 'insight-engine-selected-provider',
  MODEL: 'insight-engine-selected-model',
  CUSTOM_STYLES: 'insight-engine-custom-styles',
  ONBOARDING_DONE: 'insight-engine-onboarding-done',
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
