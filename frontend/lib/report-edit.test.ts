import { describe, expect, it } from 'vitest';
import {
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
