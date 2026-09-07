import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProtectedImage from './ProtectedImage';

const { authFetchMock } = vi.hoisted(() => ({ authFetchMock: vi.fn() }));

vi.mock('@/lib/auth-session', () => ({
  authFetch: authFetchMock,
}));

vi.mock('@/lib/api', () => ({
  apiUrl: (path: string) => `https://api.example.test${path}`,
}));

describe('ProtectedImage', () => {
  let container: HTMLDivElement;
  let root: Root;
  let createObjectUrl: ReturnType<typeof vi.fn>;
  let revokeObjectUrl: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    createObjectUrl = vi.fn(() => 'blob:protected-image');
    revokeObjectUrl = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrl,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrl,
    });
    authFetchMock.mockReset();
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it('상대 미디어 URL은 인증 fetch로 Blob을 받은 뒤 렌더링한다', async () => {
    authFetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      blob: vi.fn().mockResolvedValue(new Blob(['image'])),
    } as unknown as Response);

    await act(async () => {
      root.render(<ProtectedImage src="/api/video-deepdives/abc/media/shot.jpg" alt="shot" />);
    });
    await vi.waitFor(() => {
      expect(container.querySelector('img')?.getAttribute('src')).toBe('blob:protected-image');
    });

    expect(authFetchMock).toHaveBeenCalledWith(
      'https://api.example.test/api/video-deepdives/abc/media/shot.jpg',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(createObjectUrl).toHaveBeenCalledTimes(1);
  });

  it('외부 HTTPS 이미지는 직접 로드하고 인증 요청하지 않는다', async () => {
    await act(async () => {
      root.render(<ProtectedImage src="https://cdn.example.test/shot.jpg" alt="shot" />);
    });

    expect(container.querySelector('img')?.getAttribute('src')).toBe(
      'https://cdn.example.test/shot.jpg',
    );
    expect(authFetchMock).not.toHaveBeenCalled();
  });
});
