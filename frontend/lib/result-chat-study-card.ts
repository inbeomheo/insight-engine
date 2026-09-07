import type { ResultChatSource } from './api';
import { getAccountStorageKey } from './storage';

export const RESULT_CHAT_STUDY_CARDS_STORAGE_KEY = 'ie:result-chat-study-cards:v1';

export function getResultChatStudyCardsStorageKey(namespace?: string): string {
  return getAccountStorageKey(RESULT_CHAT_STUDY_CARDS_STORAGE_KEY, namespace);
}

export interface ResultChatStudyCardInput {
  title?: string;
  question?: string;
  answer?: string;
  sources?: Pick<ResultChatSource, 'title' | 'score' | 'snippet'>[];
  createdAt?: string;
  sourceHref?: string;
}

export interface ResultChatStudyCard {
  id: string;
  title: string;
  question: string;
  answer: string;
  sources: Array<{
    title: string;
    score?: number;
    snippet?: string;
  }>;
  markdown: string;
  createdAt: string;
  sourceHref?: string;
}

function cleanMarkdownValue(value: string | undefined, fallback = '-'): string {
  const cleaned = (value ?? '').replace(/\s+/g, ' ').trim();
  return cleaned || fallback;
}

function normalizeSources(sources: ResultChatStudyCardInput['sources'] = []): ResultChatStudyCard['sources'] {
  return sources.map((source) => ({
    title: cleanMarkdownValue(source.title, '지식 노트'),
    score: typeof source.score === 'number' && Number.isFinite(source.score) ? source.score : undefined,
    snippet: source.snippet?.trim() ? cleanMarkdownValue(source.snippet) : undefined,
  }));
}

function buildCardId(input: Pick<ResultChatStudyCard, 'title' | 'question' | 'createdAt'>): string {
  return `qna-${encodeURIComponent(input.createdAt)}-${encodeURIComponent(input.title).slice(0, 24)}-${encodeURIComponent(input.question).slice(0, 24)}`;
}

function cleanSourceHref(value: string | undefined): string | undefined {
  const cleaned = value?.trim();
  if (!cleaned) return undefined;
  if (cleaned.startsWith('/notes/')) return cleaned;
  return undefined;
}

function buildSourceMarkdownLine(source: ResultChatStudyCard['sources'][number], index: number): string {
  const score =
    typeof source.score === 'number' && Number.isFinite(source.score)
      ? ` · ${Math.round(source.score * 100)}%`
      : '';
  const snippet = source.snippet ? ` — ${source.snippet}` : '';
  return `${index + 1}. ${source.title}${score}${snippet}`;
}

function parseStudyCard(value: unknown): ResultChatStudyCard | null {
  if (!value || typeof value !== 'object') return null;
  const raw = value as Partial<ResultChatStudyCard>;
  if (!raw.id || !raw.createdAt || !raw.markdown) return null;
  return {
    id: String(raw.id),
    title: cleanMarkdownValue(raw.title, '근거 Q&A'),
    question: cleanMarkdownValue(raw.question, '질문 없음'),
    answer: cleanMarkdownValue(raw.answer, '답변 없음'),
    sources: normalizeSources(raw.sources),
    markdown: String(raw.markdown),
    createdAt: String(raw.createdAt),
    sourceHref: cleanSourceHref(raw.sourceHref),
  };
}

export function buildResultChatStudyCardMarkdown(input: ResultChatStudyCardInput): string {
  const title = cleanMarkdownValue(input.title, '근거 Q&A');
  const question = cleanMarkdownValue(input.question, '질문 없음');
  const answer = cleanMarkdownValue(input.answer, '답변 없음');
  const sources = normalizeSources(input.sources);
  const sourceHref = cleanSourceHref(input.sourceHref);

  return [
    `# 근거 Q&A 복습 카드: ${title}`,
    ...(sourceHref ? ['', `원본 노트: ${sourceHref}`] : []),
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
          ...sources.map(buildSourceMarkdownLine),
        ]
      : []),
  ].join('\n');
}

export function buildResultChatStudyCardsMarkdown(
  cards: ResultChatStudyCard[],
  title = 'Q&A 복습 카드함'
): string {
  const heading = cleanMarkdownValue(title, 'Q&A 복습 카드함');
  if (cards.length === 0) {
    return [
      `# ${heading}`,
      '',
      '저장된 Q&A 복습 카드가 없습니다.',
    ].join('\n');
  }

  const cardBlocks = cards.map((card, index) => {
    const sources = normalizeSources(card.sources);
    const sourceHref = cleanSourceHref(card.sourceHref);
    return [
      `## ${index + 1}. ${cleanMarkdownValue(card.title, '근거 Q&A')}`,
      `- 생성: ${cleanMarkdownValue(card.createdAt, '생성일 없음')}`,
      ...(sourceHref ? [`- 원본 노트: ${sourceHref}`] : []),
      '',
      '### 질문',
      cleanMarkdownValue(card.question, '질문 없음'),
      '',
      '### 답변',
      cleanMarkdownValue(card.answer, '답변 없음'),
      ...(sources.length > 0
        ? [
            '',
            '### 근거',
            ...sources.map(buildSourceMarkdownLine),
          ]
        : []),
    ].join('\n');
  });

  return [
    `# ${heading}`,
    '',
    `- 카드 수: ${cards.length}`,
    '',
    cardBlocks.join('\n\n'),
  ].join('\n');
}

export function buildResultChatStudyCard(input: ResultChatStudyCardInput): ResultChatStudyCard {
  const createdAt = input.createdAt ?? new Date().toISOString();
  const title = cleanMarkdownValue(input.title, '근거 Q&A');
  const question = cleanMarkdownValue(input.question, '질문 없음');
  const answer = cleanMarkdownValue(input.answer, '답변 없음');
  const sources = normalizeSources(input.sources);
  const sourceHref = cleanSourceHref(input.sourceHref);
  const markdown = buildResultChatStudyCardMarkdown({ title, question, answer, sources, sourceHref });
  return {
    id: buildCardId({ title, question, createdAt }),
    title,
    question,
    answer,
    sources,
    markdown,
    createdAt,
    sourceHref,
  };
}

export function readResultChatStudyCards(storage: Pick<Storage, 'getItem'>): ResultChatStudyCard[] {
  try {
    const raw = storage.getItem(getResultChatStudyCardsStorageKey());
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(parseStudyCard)
      .filter((card): card is ResultChatStudyCard => Boolean(card))
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  } catch {
    return [];
  }
}

export function saveResultChatStudyCard(
  storage: Pick<Storage, 'getItem' | 'setItem'>,
  input: ResultChatStudyCardInput
): ResultChatStudyCard {
  const card = buildResultChatStudyCard(input);
  const existing = readResultChatStudyCards(storage);
  const next = [card, ...existing.filter((item) => item.id !== card.id)];
  storage.setItem(getResultChatStudyCardsStorageKey(), JSON.stringify(next));
  return card;
}
