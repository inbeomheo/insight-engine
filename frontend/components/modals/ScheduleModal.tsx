'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Calendar, Clock, Send } from 'lucide-react';
import { useMcpPlugins } from '@/hooks/useMcpPlugins';
import { useSettingsStore } from '@/stores/settingsStore';

type ScheduleOptions = Record<string, unknown>;

interface ScheduleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  content: string;
  html?: string;
  onSchedule: (data: { target_plugin: string; scheduled_at: string; options?: ScheduleOptions }) => boolean | void | Promise<boolean | void>;
  isLoading?: boolean;
}

export default function ScheduleModal({
  open,
  onOpenChange,
  title,
  content,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  html,
  onSchedule,
  isLoading,
}: ScheduleModalProps) {
  const plugins = useMcpPlugins(open);
  const webhookUrl = useSettingsStore((s) => s.webhookUrl);
  const wordpressDefaults = useSettingsStore((s) => s.wordpressDefaults);
  const naverDefaults = useSettingsStore((s) => s.naverDefaults);
  const [selectedPlugin, setSelectedPlugin] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [validationNow, setValidationNow] = useState(() => Date.now());
  const [submitError, setSubmitError] = useState('');
  const [wordpressOptions, setWordpressOptions] = useState({
    site_url: '',
    username: '',
    app_password: '',
    status: 'draft',
  });
  const [naverOptions, setNaverOptions] = useState({
    webhook_url: '',
    blog_id: '',
    category: '',
    tags: '',
  });

  const isWordPress = selectedPlugin === 'wordpress';
  const isNaver = selectedPlugin === 'naver_blog' || selectedPlugin === 'naver';

  function formatLocalDatetime(date: Date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${d}T${h}:${min}`;
  }

  /* eslint-disable react-hooks/set-state-in-effect */
  // 플러그인 로드 후 기본 선택
  useEffect(() => {
    if (plugins.length > 0 && !selectedPlugin) {
      setSelectedPlugin(plugins[0].id);
    }
  }, [plugins, selectedPlugin]);

  // 모달 열릴 때 기본값 초기화: 내일 오전 9시
  useEffect(() => {
    if (!open) return;
    setSubmitError('');
    setValidationNow(Date.now());
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(9, 0, 0, 0);
    setScheduledAt(formatLocalDatetime(tomorrow));
    setWordpressOptions({
      site_url: wordpressDefaults.site_url,
      username: wordpressDefaults.username,
      app_password: '',
      status: wordpressDefaults.status || 'draft',
    });
    setNaverOptions({
      webhook_url: naverDefaults.webhook_url || webhookUrl,
      blog_id: naverDefaults.blog_id,
      category: naverDefaults.category,
      tags: naverDefaults.tags,
    });
  }, [open, webhookUrl, wordpressDefaults, naverDefaults]);
  /* eslint-enable react-hooks/set-state-in-effect */

  function compactOptions(values: Record<string, string>) {
    return Object.fromEntries(
      Object.entries(values)
        .map(([key, value]) => [key, value.trim()])
        .filter(([, value]) => value)
    );
  }

  function buildPluginOptions(): ScheduleOptions {
    if (isWordPress) return compactOptions(wordpressOptions);
    if (isNaver) return compactOptions(naverOptions);
    return {};
  }

  function clearSubmitError() {
    if (submitError) setSubmitError('');
  }

  function getValidationMessage() {
    if (isWordPress) {
      if (!wordpressOptions.site_url.trim()) return 'WordPress 사이트 URL을 입력해주세요.';
      if (!wordpressOptions.username.trim()) return 'WordPress 사용자명을 입력해주세요.';
      if (!wordpressOptions.app_password.trim()) return 'WordPress Application Password를 입력해주세요.';
    }
    if (isNaver && !naverOptions.webhook_url.trim()) {
      return '네이버 발행 웹훅 URL은 필수입니다.';
    }
    if (scheduledAt) {
      const scheduledTime = new Date(scheduledAt).getTime();
      if (!Number.isFinite(scheduledTime) || scheduledTime <= validationNow) {
        return '예약 시간은 미래 시간이어야 합니다.';
      }
    }
    return '';
  }

  const validationMessage = getValidationMessage();

  async function handleSubmit() {
    if (!selectedPlugin || !scheduledAt || validationMessage) return;
    const isoDate = new Date(scheduledAt).toISOString();
    const options = buildPluginOptions();
    setSubmitError('');
    try {
      const ok = await onSchedule({
        target_plugin: selectedPlugin,
        scheduled_at: isoDate,
        ...(Object.keys(options).length ? { options } : {}),
      });
      if (ok === false) {
        setSubmitError('예약 등록 실패 · 연결값을 확인한 뒤 다시 시도해주세요.');
      }
    } catch {
      setSubmitError('예약 등록 실패 · 연결값을 확인한 뒤 다시 시도해주세요.');
    }
  }

  const canSubmit = Boolean(selectedPlugin && scheduledAt && !isLoading && !validationMessage);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary" />
            예약 발행
          </DialogTitle>
          <DialogDescription>콘텐츠를 지정 시간에 자동 발행합니다</DialogDescription>
        </DialogHeader>

        {/* 미리보기 */}
        <div className="rounded-lg bg-muted p-3">
          <p className="text-sm font-medium truncate">{title}</p>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
            {content.slice(0, 150)}...
          </p>
        </div>

        {/* 플러그인 선택 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">발행 대상</label>
          {plugins.length === 0 ? (
            <p className="text-sm text-muted-foreground">등록된 플러그인이 없습니다</p>
          ) : (
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={selectedPlugin}
              onChange={(e) => {
                clearSubmitError();
                setSelectedPlugin(e.target.value);
              }}
            >
              {plugins.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {isWordPress && (
          <div data-testid="schedule-options-wordpress" className="space-y-2 rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-xs font-semibold text-muted-foreground">WordPress 연결 설정</p>
            <input
              data-testid="schedule-option-wordpress-site-url"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="https://example.com"
              value={wordpressOptions.site_url}
              onChange={(e) => {
                clearSubmitError();
                setWordpressOptions((prev) => ({ ...prev, site_url: e.target.value }));
              }}
            />
            <input
              data-testid="schedule-option-wordpress-username"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="사용자명"
              value={wordpressOptions.username}
              onChange={(e) => {
                clearSubmitError();
                setWordpressOptions((prev) => ({ ...prev, username: e.target.value }));
              }}
            />
            <input
              data-testid="schedule-option-wordpress-app-password"
              type="password"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="Application Password"
              value={wordpressOptions.app_password}
              onChange={(e) => {
                clearSubmitError();
                setWordpressOptions((prev) => ({ ...prev, app_password: e.target.value }));
              }}
            />
            <select
              data-testid="schedule-option-wordpress-status"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={wordpressOptions.status}
              onChange={(e) => {
                clearSubmitError();
                setWordpressOptions((prev) => ({ ...prev, status: e.target.value }));
              }}
            >
              <option value="draft">임시글</option>
              <option value="publish">즉시 공개</option>
              <option value="pending">검토 대기</option>
              <option value="private">비공개</option>
            </select>
          </div>
        )}

        {isNaver && (
          <div data-testid="schedule-options-naver" className="space-y-2 rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-xs font-semibold text-muted-foreground">네이버 블로그 연결 설정</p>
            <input
              data-testid="schedule-option-naver-webhook-url"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="네이버 발행 웹훅 URL"
              value={naverOptions.webhook_url}
              onChange={(e) => {
                clearSubmitError();
                setNaverOptions((prev) => ({ ...prev, webhook_url: e.target.value }));
              }}
            />
            <input
              data-testid="schedule-option-naver-blog-id"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="블로그 ID"
              value={naverOptions.blog_id}
              onChange={(e) => {
                clearSubmitError();
                setNaverOptions((prev) => ({ ...prev, blog_id: e.target.value }));
              }}
            />
            <input
              data-testid="schedule-option-naver-category"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="카테고리"
              value={naverOptions.category}
              onChange={(e) => {
                clearSubmitError();
                setNaverOptions((prev) => ({ ...prev, category: e.target.value }));
              }}
            />
            <input
              data-testid="schedule-option-naver-tags"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="태그, 쉼표로 구분"
              value={naverOptions.tags}
              onChange={(e) => {
                clearSubmitError();
                setNaverOptions((prev) => ({ ...prev, tags: e.target.value }));
              }}
            />
          </div>
        )}

        {/* 날짜/시간 선택 */}
        <div className="space-y-2">
          <label className="text-sm font-medium flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            예약 시간
          </label>
          <input
            type="datetime-local"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            value={scheduledAt}
            onChange={(e) => {
              clearSubmitError();
              setScheduledAt(e.target.value);
            }}
          />
        </div>

        {validationMessage && (
          <p
            data-testid="schedule-validation-message"
            className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700"
          >
            {validationMessage}
          </p>
        )}

        {submitError && (
          <p
            data-testid="schedule-submit-error"
            className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
          >
            {submitError}
          </p>
        )}

        {/* 제출 */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            취소
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            <Send className="h-4 w-4 mr-1.5" />
            {isLoading ? '등록 중...' : '예약 등록'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
