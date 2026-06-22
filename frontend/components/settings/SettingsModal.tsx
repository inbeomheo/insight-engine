'use client';

import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
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
import { formatModelSize } from '@/lib/utils';
import { useTranslation } from '@/hooks/useTranslation';
import { Trash2, Bot, Brain, RotateCcw } from 'lucide-react';
import { clearCache, getStyleMemory, updateStyleMemory, resetStyleMemory, type StyleProfile } from '@/lib/api';
import { toast } from 'sonner';
import LanguageSwitcher from './LanguageSwitcher';

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
    if (!confirm('스타일 메모리를 초기화하시겠습니까? 학습된 선호도가 모두 삭제됩니다.')) return;
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

  return (
    <Dialog open={settingsModalOpen} onOpenChange={setSettingsModalOpen}>
      <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            {t('settings.title')}
          </DialogTitle>
          <DialogDescription>{t('settings.aiServiceDescription')}</DialogDescription>
        </DialogHeader>

        {/* 언어 설정 */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">{t('language.label')}</h3>
          <LanguageSwitcher />
        </div>

        {/* AI 서비스 */}
        <div className="space-y-3 pt-4 border-t">
          <h3 className="text-sm font-semibold flex items-center gap-2">{t('settings.aiService')}</h3>

          {providerIds.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {t('settings.noProviders')}
            </p>
          ) : (
            <div className="space-y-2">
              <Select
                value={selectedProvider}
                onValueChange={(v) => {
                  setSelectedProvider(v);
                  const first = providers[v]?.models[0];
                  if (first) setSelectedModel(first.id);
                }}
              >
                <SelectTrigger className="text-sm">
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

              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="text-sm">
                  <SelectValue placeholder={t('settings.selectModel')} />
                </SelectTrigger>
                <SelectContent>
                  {currentModels.map((m) => {
                    const size = formatModelSize(m.size_bytes);
                    return (
                      <SelectItem key={m.id} value={m.id}>
                        {m.name}
                        {size && <span className="ml-2 text-xs text-muted-foreground">{size}</span>}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        {/* 스타일 메모리 */}
        <div className="pt-4 border-t space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Brain className="h-4 w-4 text-primary" />
              스타일 메모리
            </h3>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-muted-foreground">활성화</span>
              <input
                type="checkbox"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                className="w-4 h-4 accent-primary"
              />
            </label>
          </div>

          <p className="text-xs text-muted-foreground">
            생성 패턴을 학습하여 AI 프롬프트에 개인 선호도를 자동 반영합니다.
          </p>

          {/* 학습된 선호도 */}
          {profile && profile.generation_count > 0 && (
            <div className="rounded-md bg-muted/50 p-3 space-y-1 text-xs">
              <p className="font-medium text-muted-foreground mb-2">학습된 선호도 ({profile.generation_count}회 생성)</p>
              {topStyles.length > 0 && (
                <p>
                  자주 사용: {topStyles.map((s) => STYLE_LABELS[s.style_id] || s.style_id).join(', ')}
                </p>
              )}
              <p>선호 길이: {LENGTH_LABELS[profile.preferred_length] || profile.preferred_length}</p>
              <p>선호 문체: {WRITING_STYLE_LABELS[profile.preferred_writing_style] || profile.preferred_writing_style}</p>
            </div>
          )}

          {/* 피하고 싶은 표현 */}
          <div className="space-y-1">
            <label className="text-xs font-medium">피하고 싶은 표현</label>
            <input
              type="text"
              value={avoidInput}
              onChange={(e) => setAvoidInput(e.target.value)}
              placeholder="예: 혁신적, 획기적, 놀라운 (쉼표로 구분)"
              className="w-full text-xs rounded-md border px-3 py-2 bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <p className="text-[10px] text-muted-foreground">최대 20개, 각 20자 이내</p>
          </div>

          {/* 커스텀 지시사항 */}
          <div className="space-y-1">
            <label className="text-xs font-medium">커스텀 지시사항</label>
            <textarea
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder="예: 항상 결론 먼저 작성, 소제목 3개 이상 사용"
              rows={3}
              maxLength={500}
              className="w-full text-xs rounded-md border px-3 py-2 bg-background resize-none focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <p className="text-[10px] text-muted-foreground text-right">{customInstructions.length}/500</p>
          </div>

          <div className="flex gap-2">
            <Button
              size="sm"
              className="flex-1 text-xs"
              onClick={handleSaveMemory}
              disabled={isSaving}
            >
              {isSaving ? '저장 중...' : '저장'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-xs text-destructive border-destructive/30 hover:bg-destructive/10"
              onClick={handleResetMemory}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              초기화
            </Button>
          </div>
        </div>

        {/* 캐시 관리 */}
        <div className="pt-4 border-t space-y-2">
          <h3 className="text-sm font-semibold">{t('settings.cacheManagement')}</h3>
          <p className="text-xs text-muted-foreground">
            {t('settings.cacheDescription')}
          </p>
          <Button
            variant="outline"
            className="w-full text-destructive border-destructive/30 hover:bg-destructive/10"
            onClick={handleClearCache}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {t('settings.clearCache')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
