/**
 * HTML 다운로드용 독립 문서 스타일.
 *
 * 다운로드 파일은 부모 페이지의 globals.css 토큰이 적용되지 않는 독립 문서이므로
 * Signal 디자인 토큰의 hex 값을 직접 사용한다.
 * globals.css 토큰 값이 바뀌면 여기도 함께 갱신할 것.
 */

// 다운로드 HTML — useExport.downloadHtml + ResultCard.handleExportHtml 공유
export const EXPORT_HTML_STYLE = `body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#15171F}
h1,h2,h3{margin-top:1.5rem}a{color:#2F54EB}blockquote{border-left:3px solid #2F54EB;padding-left:1rem;color:#6A6E78}
table{border-collapse:collapse;width:100%}th,td{border:1px solid #E0E3EB;padding:8px;text-align:left}
th{background:#E8EBF1}.katex-display{display:block;max-width:100%;margin:1em 0;overflow-x:auto;text-align:center}
.katex{font-size:1.05em}math{font-family:"STIX Two Math","Cambria Math",serif}`;
