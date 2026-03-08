import { useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';

/**
 * UIStore 모달 상태를 래핑하는 편의 훅.
 * 컴포넌트에서 `const settings = useModal('settings')` 처럼 사용.
 */
type SimpleModalType = 'settings' | 'onboarding' | 'playlist' | 'workspaceSettings' | 'templateGallery';

export function useModal(type: SimpleModalType) {
  const activeModal = useUIStore((s) => s.activeModal);
  const isOpen = activeModal === type;

  const setters: Record<SimpleModalType, (v: boolean) => void> = {
    settings: useUIStore((s) => s.setSettingsModalOpen),
    onboarding: useUIStore((s) => s.setOnboardingOpen),
    playlist: useUIStore((s) => s.setPlaylistModalOpen),
    workspaceSettings: useUIStore((s) => s.setWorkspaceSettingsOpen),
    templateGallery: useUIStore((s) => s.setTemplateGalleryOpen),
  };

  const setter = setters[type];
  const open = useCallback(() => setter(true), [setter]);
  const close = useCallback(() => setter(false), [setter]);
  const toggle = useCallback(() => setter(!isOpen), [setter, isOpen]);

  return { isOpen, open, close, toggle } as const;
}
