import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { NotebookLmArtifact } from '@/lib/types';
import { NotebookLmSection } from './NotebookLmSection';

const mocks = vi.hoisted(() => ({
  authUserId: 'user-a' as string | null,
  download: vi.fn(),
}));

vi.mock('@/hooks/useAuthUserId', () => ({
  useAuthUserId: () => mocks.authUserId,
}));
vi.mock('@/lib/api', () => ({
  downloadNotebookLmArtifact: mocks.download,
}));
vi.mock('sonner', () => ({
  toast: { error: vi.fn() },
}));

const AUDIO: NotebookLmArtifact = {
  artifact_id: 'shared-looking-id',
  content_type: 'audio',
  status: 'completed',
};

describe('NotebookLmSection protected audio', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    mocks.authUserId = 'user-a';
    mocks.download.mockReset();
    mocks.download.mockResolvedValue(new Blob(['audio']));
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:protected-audio');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.restoreAllMocks();
  });

  it('사용자가 요청하기 전에는 보호 파일을 가져오지 않는다', () => {
    act(() => root.render(<NotebookLmSection artifacts={[AUDIO]} />));

    expect(mocks.download).not.toHaveBeenCalled();
    expect(container.querySelector('audio')).toBeNull();
  });

  it('같은 artifact ID도 계정이 바뀌면 이전 계정 Blob 캐시를 재사용하지 않는다', async () => {
    act(() => root.render(<NotebookLmSection artifacts={[AUDIO]} />));
    await act(async () => {
      (container.querySelector('button[aria-label="오디오 불러오기"]') as HTMLButtonElement).click();
    });
    expect(mocks.download).toHaveBeenCalledTimes(1);

    mocks.authUserId = 'user-b';
    act(() => root.render(<NotebookLmSection artifacts={[AUDIO]} />));
    expect(container.querySelector('audio')).toBeNull();

    await act(async () => {
      (container.querySelector('button[aria-label="오디오 불러오기"]') as HTMLButtonElement).click();
    });
    expect(mocks.download).toHaveBeenCalledTimes(2);
  });
});
