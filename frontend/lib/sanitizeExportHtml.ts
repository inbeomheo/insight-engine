import DOMPurify from 'dompurify';

const FORBIDDEN_TAGS = [
  'script',
  'style',
  'iframe',
  'object',
  'embed',
  'form',
  'input',
  'button',
  'meta',
  'base',
  'svg',
  'math',
];

/** AI 생성 HTML을 독립 파일로 저장하기 전에 실행 가능한 표면을 제거한다. */
export function sanitizeExportHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    FORBID_TAGS: FORBIDDEN_TAGS,
    FORBID_ATTR: ['style', 'srcdoc'],
    ALLOW_DATA_ATTR: false,
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i,
  });
}

/** 텍스트를 HTML 문맥에 안전하게 삽입한다. */
export function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char] as string);
}