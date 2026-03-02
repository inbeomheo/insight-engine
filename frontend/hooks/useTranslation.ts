// useTranslation 훅 — I18nContext에서 t(), locale, setLocale을 제공
import { useI18nContext } from '@/lib/i18n/I18nProvider';

/**
 * 다국어 번역 훅
 *
 * 사용 예:
 * ```tsx
 * const { t, locale, setLocale } = useTranslation();
 * t('sidebar.newAnalysis')              // → "새 분석" / "New Analysis" / "新しい分析"
 * t('generateButton.multipleUrls', { count: 3 }) // → "3개 URL 각각 분석"
 * setLocale('en')                       // 영어로 전환
 * ```
 */
export function useTranslation() {
  return useI18nContext();
}
