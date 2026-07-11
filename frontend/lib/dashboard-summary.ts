import { getStyleLabel } from './helpers';
import type { Report } from './types';

export interface DashboardActivityDay {
  key: string;
  label: string;
  count: number;
}

export interface LocalDashboardStats {
  totalTokens: number;
  avgLength: number;
  topStyles: Array<[string, number]>;
  recent: Report[];
  pinned: Report[];
  linkedNoteCount: number;
  linkedNotes: Report[];
  activityDays: DashboardActivityDay[];
  maxActivityCount: number;
  storagePct: number;
  storageStatus: '여유 있음' | '여유 적음' | '가득 참';
}

export function cleanMarkdownLine(value: string | undefined, fallback = '-') {
  const text = value?.replace(/\s+/g, ' ').trim();
  return text || fallback;
}

export function formatDayKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function formatDayLabel(date: Date) {
  return date.toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' });
}

export function buildLocalDashboardStats(
  reports: Report[],
  pinnedIds: Set<string>,
  maxReports: number,
  now = new Date()
): LocalDashboardStats {
  const totalTokens = reports.reduce((sum, report) => sum + (report.usage?.total_tokens ?? 0), 0);
  const avgLength = reports.length
    ? Math.round(reports.reduce((sum, report) => sum + report.content.length, 0) / reports.length)
    : 0;
  const styleCounts = new Map<string, number>();
  for (const report of reports) {
    styleCounts.set(report.style, (styleCounts.get(report.style) ?? 0) + 1);
  }
  const topStyles = Array.from(styleCounts.entries())
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4);
  const recent = [...reports]
    .sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0))
    .slice(0, 4);
  const pinned = reports.filter((report) => pinnedIds.has(report.id)).slice(0, 4);
  const allLinkedNotes = reports.filter((report) => Boolean(report.knowledge_note_id));
  const linkedNotes = [...allLinkedNotes]
    .sort((a, b) => {
      const savedA = Date.parse(a.knowledge_note_saved_at ?? '');
      const savedB = Date.parse(b.knowledge_note_saved_at ?? '');
      const timeA = Number.isFinite(savedA) ? savedA : (a.createdAt ?? 0);
      const timeB = Number.isFinite(savedB) ? savedB : (b.createdAt ?? 0);
      return timeB - timeA;
    })
    .slice(0, 4);
  const activityDays = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(now);
    day.setHours(0, 0, 0, 0);
    day.setDate(day.getDate() - (6 - index));
    return {
      key: formatDayKey(day),
      label: formatDayLabel(day),
      count: 0,
    };
  });
  const activityIndex = new Map(activityDays.map((day, index) => [day.key, index]));
  for (const report of reports) {
    if (!report.createdAt) continue;
    const index = activityIndex.get(formatDayKey(new Date(report.createdAt)));
    if (index !== undefined) activityDays[index].count += 1;
  }
  const maxActivityCount = Math.max(1, ...activityDays.map((day) => day.count));
  const storagePct = Math.round((reports.length / maxReports) * 100);
  const storageStatus =
    reports.length >= maxReports
      ? '가득 참'
      : reports.length >= Math.floor(maxReports * 0.8)
        ? '여유 적음'
        : '여유 있음';

  return {
    totalTokens,
    avgLength,
    topStyles,
    recent,
    pinned,
    linkedNoteCount: allLinkedNotes.length,
    linkedNotes,
    activityDays,
    maxActivityCount,
    storagePct,
    storageStatus,
  };
}

export function buildLocalDashboardMarkdown(
  stats: LocalDashboardStats,
  reportCount: number,
  maxReports: number,
  copiedAt = new Date()
) {
  const styleLines = stats.topStyles.length
    ? stats.topStyles.map(([style, count]) => `- ${getStyleLabel(style)}: ${count}건`).join('\n')
    : '- 아직 생성 결과가 없습니다.';
  const recentLines = stats.recent.length
    ? stats.recent
        .map((report, index) =>
          [
            `${index + 1}. ${cleanMarkdownLine(report.title || report.youtube_title, '제목 없음')}`,
            `   - 스타일: ${getStyleLabel(report.style)}`,
            `   - 생성: ${cleanMarkdownLine(report.time)}`,
            `   - 길이: ${report.content.length.toLocaleString()}자`,
            report.url ? `   - 원본: ${report.url}` : null,
          ]
            .filter(Boolean)
            .join('\n')
        )
        .join('\n')
    : '1. 아직 생성 결과가 없습니다.';
  const pinnedLines = stats.pinned.length
    ? stats.pinned
        .map((report, index) => {
          const title = cleanMarkdownLine(report.title || report.youtube_title, '제목 없음');
          return `${index + 1}. ${title} (${getStyleLabel(report.style)})`;
        })
        .join('\n')
    : '1. 고정한 결과가 없습니다.';
  const linkedNoteLines = stats.linkedNotes.length
    ? stats.linkedNotes
        .map((report, index) => {
          const title = cleanMarkdownLine(report.knowledge_note_title || report.title || report.youtube_title, '제목 없음');
          return `${index + 1}. ${title} — /notes/${encodeURIComponent(report.knowledge_note_id ?? '')}`;
        })
        .join('\n')
    : '1. 연결된 학습 노트가 없습니다.';
  const activityLines = stats.activityDays.map((day) => `- ${day.label}: ${day.count}건`).join('\n');

  return [
    '# 내 작업 요약',
    '',
    `- 복사 시각: ${copiedAt.toLocaleString('ko-KR')}`,
    `- 저장된 결과: ${reportCount}/${maxReports}개`,
    `- 저장 공간: ${stats.storageStatus} · ${stats.storagePct}% 사용 중`,
    `- 누적 토큰: ${stats.totalTokens.toLocaleString()}`,
    `- 평균 길이: ${stats.avgLength.toLocaleString()}자`,
    '',
    '## 로컬 스타일 분포',
    styleLines,
    '',
    '## 최근 7일 생성 흐름',
    activityLines,
    '',
    '## 고정 결과',
    pinnedLines,
    '',
    '## 연결된 학습 노트',
    linkedNoteLines,
    '',
    '## 최근 로컬 결과',
    recentLines,
  ].join('\n');
}
