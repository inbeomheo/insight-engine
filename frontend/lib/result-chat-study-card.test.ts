import { describe, expect, it } from 'vitest';
import { buildResultChatStudyCardMarkdown } from './result-chat-study-card';

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
});
