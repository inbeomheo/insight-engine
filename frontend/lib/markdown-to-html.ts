// 마크다운 → HTML 문자열 변환.
// 카드 본문과 동일한 react-markdown 파이프라인을 재사용하므로, 문서를 편집해 저장한 뒤에도
// report.html을 소비하는 경로(HTML 내보내기 / 서식 복사 / 공유 페이지)가 화면과 일치한다.
import { createElement } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import type { PluggableList } from 'unified';

const remarkPlugins: PluggableList = [remarkGfm, remarkMath];
// report.html은 독립 다운로드/공유 페이지에서도 렌더된다. KaTeX의 HTML 출력은
// 20KB+ 전용 CSS와 폰트가 필요하므로, 브라우저가 자체 렌더할 수 있는 MathML만
// 저장해 결과 파일을 self-contained 상태로 유지한다.
const rehypePlugins: PluggableList = [[rehypeKatex, { output: 'mathml' }]];

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
export function injectTimestampLinks(markdown: string, videoUrl?: string): string {
  if (!videoUrl) return markdown;
  let parsed: URL;
  try {
    parsed = new URL(videoUrl);
    if (!['http:', 'https:'].includes(parsed.protocol)) return markdown;
  } catch {
    return markdown;
  }

  const linkedPositions = new Set<number>();
  for (const match of markdown.matchAll(
    /\[\[(\d{1,2}:\d{2}(?::\d{2})?)\]\]\(https?:\/\/[^)]+\)/g,
  )) {
    if (match.index !== undefined) linkedPositions.add(match.index + 1);
  }

  return markdown.replace(
    /\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g,
    (marker, timestamp: string, offset: number) => {
      if (linkedPositions.has(offset)) return marker;
      const suffix = markdown.slice(offset + marker.length, offset + marker.length + 5);
      if (suffix.startsWith('(http')) return marker;

      const parts = timestamp.split(':').map(Number);
      const [hours, minutes, seconds] = parts.length === 3
        ? parts
        : [0, parts[0], parts[1]];
      if (
        parts.some((part) => !Number.isInteger(part) || part < 0)
        || seconds >= 60
        || (parts.length === 3 && minutes >= 60)
      ) {
        return marker;
      }

      const deeplink = new URL(parsed);
      deeplink.searchParams.set('t', String(hours * 3600 + minutes * 60 + seconds));
      return `[[${timestamp}]](${deeplink.toString()})`;
    },
  );
}

export async function markdownToHtml(markdown: string, videoUrl?: string): Promise<string> {
  const processed = injectTimestampLinks(markdown, videoUrl);
  try {
    const { renderToStaticMarkup } = await import('react-dom/server');
    return renderToStaticMarkup(
      createElement(
        ReactMarkdown,
        { remarkPlugins, rehypePlugins },
        processed,
      ),
    );
  } catch {
    return `<pre>${escapeHtml(processed)}</pre>`;
  }
}
