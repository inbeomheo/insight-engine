'use client';

// LanguageSwitcher — 언어 전환 드롭다운 컴포넌트
import { Globe } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTranslation } from '@/hooks/useTranslation';
import type { Locale } from '@/lib/i18n';

const LOCALES: { value: Locale; label: string; flag: string }[] = [
  { value: 'ko', label: '한국어', flag: '🇰🇷' },
  { value: 'en', label: 'English', flag: '🇺🇸' },
  { value: 'ja', label: '日本語', flag: '🇯🇵' },
];

export default function LanguageSwitcher() {
  const { locale, setLocale, t } = useTranslation();

  return (
    <div data-testid="settings-language-control" className="flex items-center gap-2">
      <Globe aria-hidden="true" className="h-4 w-4 text-muted-foreground shrink-0" />
      <p id="settings-language-help" data-testid="settings-language-help" className="sr-only">
        언어를 변경하면 앱 인터페이스 문구가 즉시 업데이트됩니다.
      </p>
      <Select value={locale} onValueChange={(v) => setLocale(v as Locale)}>
        <SelectTrigger
          data-testid="settings-language-select"
          aria-label="앱 언어 선택"
          aria-describedby="settings-language-description settings-language-help"
          className="text-sm h-9 w-[130px]"
        >
          <SelectValue placeholder={t('language.label')} />
        </SelectTrigger>
        <SelectContent>
          {LOCALES.map(({ value, label, flag }) => (
            <SelectItem key={value} value={value} data-testid={`settings-language-option-${value}`}>
              <span className="flex items-center gap-2">
                <span>{flag}</span>
                <span>{label}</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
