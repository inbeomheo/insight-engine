import { describe, expect, it } from 'vitest';
import {
  RESULT_CHAT_STUDY_CARDS_STORAGE_KEY,
  buildResultChatStudyCard,
  buildResultChatStudyCardMarkdown,
  readResultChatStudyCards,
  saveResultChatStudyCard,
} from './result-chat-study-card';

describe('result-chat-study-card', () => {
  it('builds markdown for a grounded chat answer', () => {
    expect(buildResultChatStudyCardMarkdown({
      title: '  노트\n제목  ',
      question: '  핵심은?  ',
      answer: '  답변\n내용  ',
      sources: [
        { title: '  근거 노트  ', score: 0.87, snippet: '  인용\n스니펫  ' },
        { title: '', score: Number.NaN, snippet: '' },
      ],
    })).toBe([
      '# 근거 Q&A 복습 카드: 노트 제목',
      '',
      '## 질문',
      '핵심은?',
      '',
      '## 답변',
      '답변 내용',
      '',
      '## 근거',
      '1. 근거 노트 · 87% — 인용 스니펫',
      '2. 지식 노트',
    ].join('\n'));
  });

  it('uses safe fallbacks when chat content is empty', () => {
    expect(buildResultChatStudyCardMarkdown({})).toBe([
      '# 근거 Q&A 복습 카드: 근거 Q&A',
      '',
      '## 질문',
      '질문 없음',
      '',
      '## 답변',
      '답변 없음',
    ].join('\n'));
  });

  it('builds a reusable study card record', () => {
    expect(buildResultChatStudyCard({
      title: '노트',
      question: '질문',
      answer: '답',
      createdAt: '2026-07-10T00:00:00.000Z',
    })).toMatchObject({
      id: 'qna-2026-07-10T00%3A00%3A00.000Z-%EB%85%B8%ED%8A%B8-%EC%A7%88%EB%AC%B8',
      title: '노트',
      question: '질문',
      answer: '답',
      createdAt: '2026-07-10T00:00:00.000Z',
    });
  });

  it('saves and reads local study cards newest first', () => {
    const store = new Map<string, string>();
    const storage = {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
    };

    saveResultChatStudyCard(storage, {
      title: '이전 카드',
      question: '이전 질문',
      answer: '이전 답',
      createdAt: '2026-07-09T00:00:00.000Z',
    });
    saveResultChatStudyCard(storage, {
      title: '최근 카드',
      question: '최근 질문',
      answer: '최근 답',
      createdAt: '2026-07-10T00:00:00.000Z',
    });

    expect(JSON.parse(store.get(RESULT_CHAT_STUDY_CARDS_STORAGE_KEY) ?? '[]')).toHaveLength(2);
    expect(readResultChatStudyCards(storage).map((card) => card.title)).toEqual(['최근 카드', '이전 카드']);
  });

  it('ignores malformed local study card storage', () => {
    expect(readResultChatStudyCards({ getItem: () => '{bad json' })).toEqual([]);
    expect(readResultChatStudyCards({ getItem: () => JSON.stringify([{ title: '깨진 카드' }]) })).toEqual([]);
  });
});
