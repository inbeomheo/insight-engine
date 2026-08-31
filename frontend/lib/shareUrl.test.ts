import { describe, expect, it } from 'vitest';
import { canonicalizeShareUrl } from './shareUrl';

describe('canonicalizeShareUrl', () => {
  it('기존 내부 서버 공유 링크를 현재 공개 origin으로 바꾼다', () => {
    expect(canonicalizeShareUrl(
      'https://heo-mini-surver.tailf0cfa8.ts.net/share/Abcdefgh1234',
      'https://insight.fiv.co.kr',
    )).toBe('https://insight.fiv.co.kr/share/Abcdefgh1234');
  });

  it('상대 공유 링크도 공개 절대 URL로 만든다', () => {
    expect(canonicalizeShareUrl('/share/Abcdefgh1234', 'https://insight.fiv.co.kr'))
      .toBe('https://insight.fiv.co.kr/share/Abcdefgh1234');
  });

  it('공유 페이지가 아닌 외부 URL은 변경하지 않는다', () => {
    const source = 'https://example.com/article';
    expect(canonicalizeShareUrl(source, 'https://insight.fiv.co.kr')).toBe(source);
  });
});
