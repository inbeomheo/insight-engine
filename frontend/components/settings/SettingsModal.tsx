'use client';

import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from '@/hooks/useTranslation';
import { Trash2, Bot, Brain, RotateCcw } from 'lucide-react';
import { clearCache, getStyleMemory, updateStyleMemory, resetStyleMemory, type StyleProfile } from '@/lib/api';
import { toast } from 'sonner';
import LanguageSwitcher from './LanguageSwitcher';
import SnippetLibrary from './SnippetLibrary';

const STYLE_LABELS: Record<string, string> = {
  blog_seo: '블로그+SEO',
  summary: '요약',
  tutorial: '튜토리얼',
  qna: 'Q&A',
  app_ideas: '앱 아이디어',
  yozm_it: '요즘IT',
  brunch_essay: '브런치 에세이',
  naver_popular: '네이버 인기글',
  sns_post: 'SNS 게시글',
  newsletter: '뉴스레터',
  show_notes: '쇼 노트',
  shorts_script: 'Shorts 스크립트',
  geo_seo: 'GEO SEO',
};

const LENGTH_LABELS: Record<string, string> = {
  short: '짧게',
  medium: '보통',
  long: '길게',
};

const WRITING_STYLE_LABELS: Record<string, string> = {
  conversational: '대화체',
  explanatory: '설명체',
  casual: '캐주얼',
  expert: '전문가체',
};

export default function SettingsModal() {
  const { activeModal, setSettingsModalOpen } = useUIStore();
  const settingsModalOpen = activeModal === 'settings';
  const {
    providers,
    selectedProvider,
    selectedModel,
    setSelectedProvider,
    setSelectedModel,
  } = useSettingsStore();

  const providerIds = Object.keys(providers);
  const currentModels = selectedProvider ? providers[selectedProvider]?.models || [] : [];
  const { t } = useTranslation();

  // 스타일 메모리 상태
  const [profile, setProfile] = useState<StyleProfile | null>(null);
  const [avoidInput, setAvoidInput] = useState('');
  const [customInstructions, setCustomInstructions] = useState('');
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false);

  // 모달이 열릴 때 프로필 로드
  const loadProfile = useCallback(async () => {
    try {
      const res = await getStyleMemory();
      setProfile(res.profile);
      setAvoidInput((res.profile.avoid_keywords || []).join(', '));
      setCustomInstructions(res.profile.custom_instructions || '');
      setMemoryEnabled(res.profile.style_memory_enabled !== false);
    } catch {
      // Supabase 비활성화 또는 미로그인 시 무시
    }
  }, []);

  useEffect(() => {
    if (settingsModalOpen) loadProfile();
  }, [settingsModalOpen, loadProfile]);

  async function handleClearCache() {
    try {
      await clearCache();
      toast.success(t('settings.cacheCleared'));
    } catch {
      toast.error(t('settings.cacheClearFailed'));
    }
  }

  async function handleSaveMemory() {
    setIsSaving(true);
    try {
      const keywords = avoidInput
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean)
        .slice(0, 20);
      await updateStyleMemory({
        avoid_keywords: keywords,
        custom_instructions: customInstructions.trim().slice(0, 500),
        style_memory_enabled: memoryEnabled,
      });
      toast.success('스타일 메모리가 저장되었습니다.');
      await loadProfile();
    } catch {
      toast.error('저장에 실패했습니다.');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleResetMemory() {
    setResetConfirmOpen(false);
    try {
      await resetStyleMemory();
      toast.success('스타일 메모리가 초기화되었습니다.');
      await loadProfile();
      setAvoidInput('');
      setCustomInstructions('');
      setMemoryEnabled(true);
    } catch {
      toast.error('초기화에 실패했습니다.');
    }
  }

  const topStyles = (profile?.preferred_styles || [])
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);

  const closeSettingsModal = useCallback(() => {
    setSettingsModalOpen(false);
    setResetConfirmOpen(false);
    requestAnimationFrame(() => {
      const trigger = document.querySelector("[data-testid='header-settings-trigger']");
      if (trigger instanceof HTMLButtonElement) trigger.focus();
    });
  }, [setSettingsModalOpen]);

  return (
    <>
    <Dialog
      open={settingsModalOpen}
      onOpenChange={(open) => {
        if (open) setSettingsModalOpen(true);
        else closeSettingsModal();
      }}
    >
      <DialogContent
        id="settings-dialog"
        aria-labelledby="settings-dialog-title"
        aria-describedby="settings-dialog-description"
        showCloseButton={false}
        className="max-w-md max-h-[85vh] overflow-y-auto"
      >
        <DialogHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-2 text-left">
              <DialogTitle id="settings-dialog-title" data-testid="settings-dialog-title" className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary" />
                {t('settings.title')}
              </DialogTitle>
              <DialogDescription id="settings-dialog-description" data-testid="settings-dialog-description">
                {t('settings.aiServiceDescription')}
              </DialogDescription>
            </div>
            <Button
              data-testid="settings-dialog-close"
              aria-label="설정 닫기"
              type="button"
              variant="ghost"
              size="sm"
              onClick={closeSettingsModal}
            >
              닫기
            </Button>
          </div>
        </DialogHeader>

        {/* 언어 설정 */}
        <section
          data-testid="settings-language-section"
          role="region"
          aria-labelledby="settings-language-title"
          aria-describedby="settings-language-description"
          className="space-y-2"
        >
          <div className="space-y-1">
            <h3 id="settings-language-title" data-testid="settings-language-title" className="text-sm font-semibold">{t('language.label')}</h3>
            <p id="settings-language-description" data-testid="settings-language-description" className="text-xs text-muted-foreground">
              앱 인터페이스에 표시할 언어를 선택합니다.
            </p>
          </div>
          <LanguageSwitcher />
        </section>

        {/* AI 서비스 */}
        <section
          data-testid="settings-ai-service-section"
          role="region"
          aria-labelledby="settings-ai-service-title"
          aria-describedby="settings-ai-service-description"
          className="space-y-3 pt-4 border-t"
        >
          <div className="space-y-1">
            <h3 id="settings-ai-service-title" data-testid="settings-ai-service-title" className="text-sm font-semibold flex items-center gap-2">
              {t('settings.aiService')}
            </h3>
            <p id="settings-ai-service-description" data-testid="settings-ai-service-description" className="text-xs text-muted-foreground">
              AI 제공자와 모델을 선택해 콘텐츠 생성에 사용할 실행 환경을 설정합니다.
            </p>
          </div>

          {providerIds.length === 0 ? (
            <p role="status" aria-live="polite" className="text-xs text-muted-foreground">
              {t('settings.noProviders')}
            </p>
          ) : (
            <div className="space-y-3">
              <div className="space-y-1">
                <label id="settings-ai-provider-label" className="text-xs font-medium">AI 제공자</label>
                <p id="settings-ai-provider-help" data-testid="settings-ai-provider-help" className="sr-only">
                  사용할 AI API 제공자를 선택합니다.
                </p>
                <Select
                  value={selectedProvider}
                  onValueChange={(v) => {
                    setSelectedProvider(v);
                    const first = providers[v]?.models[0];
                    if (first) setSelectedModel(first.id);
                  }}
                >
                  <SelectTrigger
                    data-testid="settings-ai-provider-select"
                    aria-label="AI 제공자 선택"
                    aria-describedby="settings-ai-service-description settings-ai-provider-help"
                    className="w-full text-sm"
                  >
                    <SelectValue placeholder={t('settings.selectProvider')} />
                  </SelectTrigger>
                  <SelectContent>
                    {providerIds.map((id) => (
                      <SelectItem key={id} value={id}>
                        {providers[id].name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <label id="settings-ai-model-label" className="text-xs font-medium">AI 모델</label>
                <p id="settings-ai-model-help" data-testid="settings-ai-model-help" className="sr-only">
                  콘텐츠 생성에 사용할 모델을 선택합니다.
                </p>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger
                    data-testid="settings-ai-model-select"
                    aria-label="AI 모델 선택"
                    aria-describedby="settings-ai-service-description settings-ai-model-help"
                    className="w-full text-sm"
                  >
                    <SelectValue placeholder={t('settings.selectModel')} />
                  </SelectTrigger>
                  <SelectContent>
                    {currentModels.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </section>

        {/* 스타일 메모리 */}
        <section
          data-testid="settings-style-memory-section"
          role="region"
          aria-labelledby="settings-style-memory-title"
          aria-describedby="settings-style-memory-description"
          className="pt-4 border-t space-y-3"
        >
          <div className="flex items-center justify-between">
            <h3 id="settings-style-memory-title" data-testid="settings-style-memory-title" className="text-sm font-semibold flex items-center gap-2">
              <Brain className="h-4 w-4 text-primary" />
              스타일 메모리
            </h3>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-muted-foreground">활성화</span>
              <input
                data-testid="settings-style-memory-switch"
                type="checkbox"
                role="switch"
                aria-label="스타일 메모리 활성화"
                aria-checked={memoryEnabled}
                aria-describedby="settings-style-memory-description settings-style-memory-status"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                className="w-4 h-4 accent-primary"
              />
            </label>
          </div>

          <p id="settings-style-memory-description" data-testid="settings-style-memory-description" className="text-xs text-muted-foreground">
            생성 패턴을 학습하여 AI 프롬프트에 개인 선호도를 자동 반영합니다.
          </p>
          <p id="settings-style-memory-status" data-testid="settings-style-memory-status" role="status" aria-live="polite" className="text-[10px] font-medium text-muted-foreground">
            스타일 메모리 {memoryEnabled ? '켜짐' : '꺼짐'}
          </p>

          {/* 학습된 선호도 */}
          {profile && profile.generation_count > 0 && (
            <section
              data-testid="settings-style-memory-learned"
              role="region"
              aria-labelledby="settings-style-memory-learned-title"
              aria-describedby="settings-style-memory-learned-description"
              className="rounded-md bg-muted/50 p-3 space-y-2 text-xs"
            >
              <p id="settings-style-memory-learned-title" data-testid="settings-style-memory-learned-title" className="font-medium text-muted-foreground">
                학습된 선호도 ({profile.generation_count}회 생성)
              </p>
              <p id="settings-style-memory-learned-description" data-testid="settings-style-memory-learned-description" className="sr-only">
                최근 생성 패턴을 바탕으로 자주 사용한 스타일, 선호 길이, 선호 문체를 요약합니다.
              </p>
              <div data-testid="settings-style-memory-learned-list" role="list" aria-label="학습된 스타일 메모리 요약" className="space-y-1">
                <p
                  data-testid="settings-style-memory-learned-style"
                  role="listitem"
                  aria-label={`자주 사용한 스타일: ${topStyles.length > 0 ? topStyles.map((s) => `${STYLE_LABELS[s.style_id] || s.style_id} ${s.count}회`).join(', ') : '없음'}`}
                >
                  자주 사용: {topStyles.length > 0 ? topStyles.map((s) => `${STYLE_LABELS[s.style_id] || s.style_id} ${s.count}회`).join(', ') : '없음'}
                </p>
                <p
                  data-testid="settings-style-memory-learned-length"
                  role="listitem"
                  aria-label={`선호 길이: ${LENGTH_LABELS[profile.preferred_length] || profile.preferred_length}`}
                >
                  선호 길이: {LENGTH_LABELS[profile.preferred_length] || profile.preferred_length}
                </p>
                <p
                  data-testid="settings-style-memory-learned-tone"
                  role="listitem"
                  aria-label={`선호 문체: ${WRITING_STYLE_LABELS[profile.preferred_writing_style] || profile.preferred_writing_style}`}
                >
                  선호 문체: {WRITING_STYLE_LABELS[profile.preferred_writing_style] || profile.preferred_writing_style}
                </p>
              </div>
            </section>
          )}

          {/* 피하고 싶은 표현 */}
          <div className="space-y-1">
            <label id="settings-style-memory-avoid-label" htmlFor="settings-style-memory-avoid-input" className="text-xs font-medium">피하고 싶은 표현</label>
            <input
              id="settings-style-memory-avoid-input"
              data-testid="settings-style-memory-avoid-input"
              type="text"
              aria-label="피하고 싶은 표현"
              aria-labelledby="settings-style-memory-avoid-label"
              aria-describedby="settings-style-memory-avoid-help"
              value={avoidInput}
              onChange={(e) => setAvoidInput(e.target.value)}
              placeholder="예: 혁신적, 획기적, 놀라운 (쉼표로 구분)"
              className="w-full text-xs rounded-md border px-3 py-2 bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <p id="settings-style-memory-avoid-help" data-testid="settings-style-memory-avoid-help" className="text-[10px] text-muted-foreground">최대 20개, 각 20자 이내</p>
          </div>

          {/* 커스텀 지시사항 */}
          <div className="space-y-1">
            <label id="settings-style-memory-custom-label" htmlFor="settings-style-memory-custom-input" className="text-xs font-medium">커스텀 지시사항</label>
            <textarea
              id="settings-style-memory-custom-input"
              data-testid="settings-style-memory-custom-input"
              aria-label="커스텀 지시사항"
              aria-labelledby="settings-style-memory-custom-label"
              aria-describedby="settings-style-memory-custom-count"
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder="예: 항상 결론 먼저 작성, 소제목 3개 이상 사용"
              rows={3}
              maxLength={500}
              className="w-full text-xs rounded-md border px-3 py-2 bg-background resize-none focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <p id="settings-style-memory-custom-count" data-testid="settings-style-memory-custom-count" aria-live="polite" className="text-[10px] text-muted-foreground text-right">{customInstructions.length}/500</p>
          </div>

          <div className="flex gap-2">
            <Button
              data-testid="settings-style-memory-save"
              aria-label="스타일 메모리 저장"
              size="sm"
              className="flex-1 text-xs"
              onClick={handleSaveMemory}
              disabled={isSaving}
            >
              {isSaving ? '저장 중...' : '저장'}
            </Button>
            <Button
              data-testid="settings-style-memory-reset"
              aria-label="스타일 메모리 초기화 확인 열기"
              size="sm"
              variant="outline"
              className="text-xs text-destructive border-destructive/30 hover:bg-destructive/10"
              onClick={() => setResetConfirmOpen(true)}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              초기화
            </Button>
          </div>
        </section>

        <SnippetLibrary />

        {/* 캐시 관리 */}
        <section
          data-testid="settings-cache-section"
          role="region"
          aria-labelledby="settings-cache-title"
          aria-describedby="settings-cache-description"
          className="pt-4 border-t space-y-2"
        >
          <h3 id="settings-cache-title" data-testid="settings-cache-title" className="text-sm font-semibold">{t('settings.cacheManagement')}</h3>
          <p id="settings-cache-description" data-testid="settings-cache-description" className="text-xs text-muted-foreground">
            {t('settings.cacheDescription')}
          </p>
          <Button
            data-testid="settings-cache-clear"
            aria-label="저장된 자막/댓글 캐시 전체 삭제"
            aria-describedby="settings-cache-description"
            variant="outline"
            className="w-full text-destructive border-destructive/30 hover:bg-destructive/10"
            onClick={handleClearCache}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {t('settings.clearCache')}
          </Button>
        </section>
      </DialogContent>
    </Dialog>
    <Dialog open={resetConfirmOpen} onOpenChange={setResetConfirmOpen}>
      <DialogContent
        data-testid="settings-style-memory-reset-dialog"
        aria-labelledby="settings-style-memory-reset-title"
        aria-describedby="settings-style-memory-reset-description"
        className="max-w-sm"
      >
        <DialogHeader>
          <DialogTitle id="settings-style-memory-reset-title" data-testid="settings-style-memory-reset-title" className="text-destructive">
            스타일 메모리 초기화
          </DialogTitle>
          <DialogDescription id="settings-style-memory-reset-description" data-testid="settings-style-memory-reset-description">
            학습된 선호도와 스타일 메모리를 모두 삭제합니다. 이 작업은 되돌릴 수 없습니다.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            data-testid="settings-style-memory-reset-cancel"
            aria-label="스타일 메모리 초기화 취소"
            type="button"
            variant="outline"
            onClick={() => setResetConfirmOpen(false)}
          >
            취소
          </Button>
          <Button
            data-testid="settings-style-memory-reset-confirm"
            aria-label="스타일 메모리 영구 초기화"
            type="button"
            variant="destructive"
            onClick={handleResetMemory}
          >
            초기화
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
}
