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
    <div className="flex items-center gap-2">
      <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
      <Select value={locale} onValueChange={(v) => setLocale(v as Locale)}>
        <SelectTrigger className="text-sm h-9 w-[130px]" aria-label={t('language.label')}>
          <SelectValue placeholder={t('language.label')} />
        </SelectTrigger>
        <SelectContent>
          {LOCALES.map(({ value, label, flag }) => (
            <SelectItem key={value} value={value}>
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
