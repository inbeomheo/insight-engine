import type { ResultChatSource } from './api';

export interface ResultChatStudyCardInput {
  title?: string;
  question?: string;
  answer?: string;
  sources?: Pick<ResultChatSource, 'title' | 'score' | 'snippet'>[];
}

function cleanMarkdownValue(value: string | undefined, fallback = '-'): string {
  const cleaned = (value ?? '').replace(/\s+/g, ' ').trim();
  return cleaned || fallback;
}

export function buildResultChatStudyCardMarkdown(input: ResultChatStudyCardInput): string {
  const title = cleanMarkdownValue(input.title, '근거 Q&A');
  const question = cleanMarkdownValue(input.question, '질문 없음');
  const answer = cleanMarkdownValue(input.answer, '답변 없음');
  const sources = input.sources ?? [];

  return [
    `# 근거 Q&A 복습 카드: ${title}`,
    '',
    '## 질문',
    question,
    '',
    '## 답변',
    answer,
    ...(sources.length > 0
      ? [
          '',
          '## 근거',
          ...sources.map((source, index) => {
            const sourceTitle = cleanMarkdownValue(source.title, '지식 노트');
            const score =
              typeof source.score === 'number' && Number.isFinite(source.score)
                ? ` · ${Math.round(source.score * 100)}%`
                : '';
            const snippet = source.snippet?.trim()
              ? ` — ${cleanMarkdownValue(source.snippet)}`
              : '';
            return `${index + 1}. ${sourceTitle}${score}${snippet}`;
          }),
        ]
      : []),
  ].join('\n');
}
