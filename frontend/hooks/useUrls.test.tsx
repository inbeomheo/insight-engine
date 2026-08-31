import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { useUrls } from './useUrls';

type UrlHook = ReturnType<typeof useUrls>;
let root: Root | null = null;
let currentHook: UrlHook | null = null;

function Harness() {
  const hook = useUrls();
  useEffect(() => { currentHook = hook; }, [hook]);
  return null;
}

async function renderHook() {
  const el = document.createElement('div');
  document.body.appendChild(el);
  root = createRoot(el);
  await act(async () => { root!.render(<Harness />); });
  return {
    get hook() {
      if (!currentHook) throw new Error('hook not rendered');
      return currentHook;
    },
  };
}

describe('useUrls 동일 링크 중복 방지', () => {
  beforeEach(() => { currentHook = null; });
  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    root = null;
    currentHook = null;
    document.body.innerHTML = '';
  });

  it('호스트 대소문자·끝 슬래시·fragment·추적 파라미터가 달라도 같은 링크로 본다', async () => {
    const rendered = await renderHook();
    let first: string | null = null;
    let duplicate: string | null = null;

    await act(async () => {
      first = rendered.hook.addUrl('https://EXAMPLE.com/article/?utm_source=telegram#section');
      duplicate = rendered.hook.addUrl('https://example.com/article');
    });

    expect(first).toBeNull();
    expect(duplicate).toBe('이미 추가된 URL입니다.');
    expect(rendered.hook.urls).toEqual(['https://example.com/article']);
  });

  it('같은 링크를 한 이벤트 루프에서 연속 호출해도 한 번만 추가한다', async () => {
    const rendered = await renderHook();
    const results: Array<string | null> = [];

    await act(async () => {
      results.push(rendered.hook.addUrl('https://example.com/repeat'));
      results.push(rendered.hook.addUrl('https://example.com/repeat'));
      results.push(rendered.hook.addUrl('https://example.com/repeat/'));
    });

    expect(results).toEqual([null, '이미 추가된 URL입니다.', '이미 추가된 URL입니다.']);
    expect(rendered.hook.urls).toEqual(['https://example.com/repeat']);
  });

  it('다중 추가에서도 기존 목록·배치 내부 중복을 제거한다', async () => {
    const rendered = await renderHook();
    await act(async () => { rendered.hook.addUrl('https://example.com/a'); });

    let result!: { added: number; errors: string[] };
    await act(async () => {
      result = rendered.hook.addUrls([
        'https://example.com/a/',
        'https://example.com/b?utm_campaign=x',
        'https://EXAMPLE.com/b#top',
      ]);
    });

    expect(result).toEqual({ added: 1, errors: [] });
    expect(rendered.hook.urls).toEqual([
      'https://example.com/a',
      'https://example.com/b',
    ]);
  });
});
