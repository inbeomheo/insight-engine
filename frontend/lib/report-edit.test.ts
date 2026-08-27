import { describe, expect, it } from 'vitest';
import {
  createDownloadFilename,
  escapeHtmlText,
  getNotebookLmTerminalStatus,
  hasReportChanges,
  normalizeReportDraft,
  validateReportDraft,
} from './report-edit';

describe('normalizeReportDraft', () => {
  it('제목의 앞뒤 공백을 제거한다', () => {
    expect(normalizeReportDraft({ title: '  제목  ', content: '본문' }).title).toBe('제목');
  });

  it('본문 끝 공백만 제거하고 들여쓰기는 보존한다', () => {
    const { content } = normalizeReportDraft({
      title: '제목',
      content: '# 제목\n\n  들여쓰기 유지\n\n\n',
    });
    expect(content).toBe('# 제목\n\n  들여쓰기 유지');
  });
});

describe('내보내기 보안 유틸리티', () => {
  it('편집 제목을 title 태그 텍스트로 안전하게 이스케이프한다', () => {
    const title = '</title><script>alert("x")</script> & \'quote\'';
    expect(`<title>${escapeHtmlText(title)}</title>`).toBe(
      '<title>&lt;/title&gt;&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &#39;quote&#39;</title>',
    );
  });

  it('다운로드 파일명에서 제어문자와 경로문자를 제거한다', () => {
    expect(createDownloadFilename('../폴더\\제목:\u0000*?"<>|', 'html')).toBe('_폴더_제목________.html');
    expect(createDownloadFilename('  ...  ', 'md')).toBe('report.md');
  });
});

describe('getNotebookLmTerminalStatus', () => {
  it('not_found를 실패 종료 상태로 정규화한다', () => {
    expect(getNotebookLmTerminalStatus('not_found')).toBe('failed');
    expect(getNotebookLmTerminalStatus('failed')).toBe('failed');
    expect(getNotebookLmTerminalStatus('completed')).toBe('completed');
    expect(getNotebookLmTerminalStatus('in_progress')).toBeNull();
  });
});

describe('validateReportDraft', () => {
  it('제목이 비어 있으면 emptyTitle', () => {
    expect(validateReportDraft({ title: '   ', content: '본문' })).toBe('emptyTitle');
  });

  it('본문이 비어 있으면 emptyContent', () => {
    expect(validateReportDraft({ title: '제목', content: '  \n ' })).toBe('emptyContent');
  });

  it('둘 다 있으면 null', () => {
    expect(validateReportDraft({ title: '제목', content: '본문' })).toBeNull();
  });
});

describe('hasReportChanges', () => {
  const report = { title: '원본 제목', content: '원본 본문' };

  it('정규화 후 동일하면 false', () => {
    expect(hasReportChanges(report, { title: ' 원본 제목 ', content: '원본 본문\n\n' })).toBe(false);
  });

  it('제목만 바뀌어도 true', () => {
    expect(hasReportChanges(report, { title: '새 제목', content: '원본 본문' })).toBe(true);
  });

  it('본문만 바뀌어도 true', () => {
    expect(hasReportChanges(report, { title: '원본 제목', content: '수정된 본문' })).toBe(true);
  });
});
