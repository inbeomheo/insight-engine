// 마크다운 → HTML 문자열 변환.
// 카드 본문과 동일한 react-markdown 파이프라인을 재사용하므로, 문서를 편집해 저장한 뒤에도
// report.html을 소비하는 경로(HTML 내보내기 / 서식 복사 / 공유 페이지)가 화면과 일치한다.
import { createElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const remarkPlugins = [remarkGfm];

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * 마크다운 문자열을 HTML로 렌더링한다.
 * react-dom/server는 초기 번들에서 제외하기 위해 동적 import 하고,
 * 실패 시 백엔드(share_page_service.html_from_content)와 동일하게 <pre> 폴백을 사용한다.
 */
export async function markdownToHtml(markdown: string): Promise<string> {
  try {
    const { renderToStaticMarkup } = await import('react-dom/server');
    return renderToStaticMarkup(
      createElement(ReactMarkdown, { remarkPlugins }, markdown),
    );
  } catch {
    return `<pre>${escapeHtml(markdown)}</pre>`;
  }
}
