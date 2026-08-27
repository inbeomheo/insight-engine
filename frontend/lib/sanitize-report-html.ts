import DOMPurify from 'dompurify';

const ALLOWED_TAGS = [
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's',
  'ul', 'ol', 'li', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'blockquote', 'pre', 'code', 'span', 'div', 'hr', 'sup', 'sub', 'mark',
  // rehype-katex의 self-contained MathML 출력. 실행 가능한 SVG/foreignObject는
  // 허용하지 않고 수식 의미·배치에 필요한 MathML 요소만 보존한다.
  'math', 'semantics', 'annotation', 'annotation-xml', 'mrow', 'mi', 'mn', 'mo',
  'ms', 'mtext', 'mspace', 'msup', 'msub', 'msubsup', 'mfrac', 'msqrt', 'mroot',
  'mstyle', 'merror', 'mpadded', 'mphantom', 'mfenced', 'menclose', 'mtable', 'mtr',
  'mtd', 'maligngroup', 'malignmark', 'mover', 'munder', 'munderover',
  'mmultiscripts', 'mprescripts', 'none',
];

const ALLOWED_ATTR = [
  'href', 'src', 'alt', 'title', 'class', 'style', 'target', 'rel', 'colspan', 'rowspan',
  'aria-hidden', 'xmlns', 'display', 'encoding', 'mathvariant', 'mathsize', 'mathcolor',
  'mathbackground', 'displaystyle', 'scriptlevel', 'stretchy', 'symmetric', 'fence',
  'separator', 'form', 'accent', 'accentunder', 'lspace', 'rspace', 'maxsize', 'minsize',
  'movablelimits', 'largeop', 'width', 'height', 'depth', 'voffset', 'rowalign',
  'columnalign', 'rowspacing', 'columnspacing', 'rowlines', 'columnlines', 'frame',
  'framespacing', 'equalrows', 'equalcolumns', 'columnspan',
];

/** 생성 결과의 HTML/MathML을 다운로드·클립보드에 넣기 전에 정화한다. */
export function sanitizeReportHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  });
}
