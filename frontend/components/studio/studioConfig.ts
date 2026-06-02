import { CalendarDays, Download, FileText, Settings, Sparkles, Wand2 } from 'lucide-react';

export const STUDIO_STEPS = [
  { id: 'source', label: '소스 입력', description: 'URL, 텍스트, 파일, 음성을 준비합니다.' },
  { id: 'blueprint', label: '산출물 설계', description: '스타일, 톤, 길이, 제작 모드를 고릅니다.' },
  { id: 'generate', label: 'AI 생성', description: '선택 모델로 콘텐츠를 생성합니다.' },
  { id: 'workbench', label: '후처리', description: 'NLM, 변환, 내보내기, 예약을 처리합니다.' },
] as const;

export const QUICK_ACTIONS = [
  { id: 'export', label: '내보내기', icon: Download },
  { id: 'schedule', label: '예약', icon: CalendarDays },
  { id: 'nlm', label: 'NLM 산출물', icon: Sparkles },
  { id: 'rewrite', label: '플랫폼 변환', icon: Wand2 },
  { id: 'prompt', label: '프롬프트', icon: FileText },
  { id: 'settings', label: '설정', icon: Settings },
] as const;

export function getGenerateLabel(sourceCount: number, mode: string): string {
  if (sourceCount <= 0) return '소스를 추가하면 생성할 수 있습니다';
  if (mode === 'combined') return `${sourceCount}개 소스 통합 콘텐츠 생성`;
  if (mode === 'fusion') return `${sourceCount}개 소스 퓨전 분석 시작`;
  if (sourceCount === 1) return '1개 소스로 콘텐츠 생성';
  return `${sourceCount}개 소스 각각 생성`;
}
