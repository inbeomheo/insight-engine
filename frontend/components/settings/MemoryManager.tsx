'use client';

import { useState, useCallback, useEffect } from 'react';
import { useListManager } from '@/hooks/useListManager';
import { apiUrl } from '@/lib/api';

interface UserMemory {
  preferred_topics?: string[];
  preferred_tone?: string;
  avoid_topics?: string[];
  custom_instructions?: string;
  language?: string;
  feedback_history?: string[];
}

export default function MemoryManager() {
  const [memory, setMemory] = useState<UserMemory>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // 리스트 관리 — useListManager로 add/remove 보일러플레이트 제거
  const topics = useListManager<string>();
  const avoids = useListManager<string>();

  // 편집용 상태
  const [topicInput, setTopicInput] = useState('');
  const [avoidInput, setAvoidInput] = useState('');
  const [toneInput, setToneInput] = useState('');
  const [instructionsInput, setInstructionsInput] = useState('');

  const fetchMemory = useCallback(async () => {
    try {
      const res = await fetch(apiUrl('/api/memory'));
      if (res.ok) {
        const data = await res.json();
        const mem = data.memory || {};
        setMemory(mem);
        topics.set(mem.preferred_topics || []);
        avoids.set(mem.avoid_topics || []);
        setToneInput(mem.preferred_tone || '');
        setInstructionsInput(mem.custom_instructions || '');
      }
    } catch {
      // 메모리 미사용 시 무시
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchMemory();
  }, [fetchMemory]);

  const updateKey = useCallback(async (key: string, value: unknown) => {
    setIsSaving(true);
    try {
      const res = await fetch(apiUrl('/api/memory'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value }),
      });
      if (res.ok) {
        const data = await res.json();
        const mem = data.memory || {};
        setMemory(mem);
        // 서버 응답으로 리스트 동기화
        topics.set(mem.preferred_topics || []);
        avoids.set(mem.avoid_topics || []);
      }
    } catch {
      // 무시
    } finally {
      setIsSaving(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearMemory = useCallback(async () => {
    if (!confirm('메모리를 전체 초기화하시겠습니까?')) return;
    try {
      const res = await fetch(apiUrl('/api/memory'), { method: 'DELETE' });
      if (res.ok) {
        setMemory({});
        topics.clear();
        avoids.clear();
        setToneInput('');
        setInstructionsInput('');
      }
    } catch {
      // 무시
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addTopic = () => {
    if (!topicInput.trim()) return;
    const newTopics = [...topics.items, topicInput.trim()];
    updateKey('preferred_topics', newTopics);
    setTopicInput('');
  };

  const removeTopic = (topic: string) => {
    const newTopics = topics.items.filter((t) => t !== topic);
    updateKey('preferred_topics', newTopics);
  };

  const addAvoid = () => {
    if (!avoidInput.trim()) return;
    const newAvoids = [...avoids.items, avoidInput.trim()];
    updateKey('avoid_topics', newAvoids);
    setAvoidInput('');
  };

  const removeAvoid = (topic: string) => {
    const newAvoids = avoids.items.filter((t) => t !== topic);
    updateKey('avoid_topics', newAvoids);
  };

  if (isLoading) {
    return <div className="text-sm text-muted-foreground p-4">메모리 로딩 중...</div>;
  }

  return (
    <div className="space-y-5">
      {/* 선호 주제 */}
      <section className="space-y-2">
        <h4 className="text-sm font-medium">선호 주제</h4>
        <div className="flex gap-2">
          <input
            type="text"
            value={topicInput}
            onChange={(e) => setTopicInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTopic()}
            placeholder="주제 추가..."
            className="flex-1 rounded-md border px-3 py-1.5 text-sm"
          />
          <button onClick={addTopic} aria-label="선호 주제 추가" className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground">
            추가
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {topics.items.map((topic) => (
            <span key={topic} className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
              {topic}
              <button onClick={() => removeTopic(topic)} aria-label={`${topic} 주제 제거`} className="hover:text-red-500">x</button>
            </span>
          ))}
        </div>
      </section>

      {/* 선호 톤 */}
      <section className="space-y-2">
        <h4 className="text-sm font-medium">선호 톤</h4>
        <div className="flex gap-2">
          <input
            type="text"
            value={toneInput}
            onChange={(e) => setToneInput(e.target.value)}
            placeholder="예: 전문적, 친근한, 간결한..."
            className="flex-1 rounded-md border px-3 py-1.5 text-sm"
          />
          <button
            onClick={() => updateKey('preferred_tone', toneInput.trim())}
            aria-label="선호 톤 저장"
            className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground"
          >
            저장
          </button>
        </div>
      </section>

      {/* 피하는 주제 */}
      <section className="space-y-2">
        <h4 className="text-sm font-medium">피하는 주제</h4>
        <div className="flex gap-2">
          <input
            type="text"
            value={avoidInput}
            onChange={(e) => setAvoidInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addAvoid()}
            placeholder="피할 주제..."
            className="flex-1 rounded-md border px-3 py-1.5 text-sm"
          />
          <button onClick={addAvoid} aria-label="피하는 주제 추가" className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground">
            추가
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {avoids.items.map((topic) => (
            <span key={topic} className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-400">
              {topic}
              <button onClick={() => removeAvoid(topic)} aria-label={`${topic} 주제 제거`} className="hover:text-red-700">x</button>
            </span>
          ))}
        </div>
      </section>

      {/* 커스텀 지시사항 */}
      <section className="space-y-2">
        <h4 className="text-sm font-medium">커스텀 지시사항</h4>
        <textarea
          value={instructionsInput}
          onChange={(e) => setInstructionsInput(e.target.value)}
          placeholder="AI에게 추가할 지시사항..."
          rows={3}
          className="w-full rounded-md border px-3 py-2 text-sm"
        />
        <button
          onClick={() => updateKey('custom_instructions', instructionsInput.trim())}
          disabled={isSaving}
          aria-label="커스텀 지시사항 저장"
          className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground disabled:opacity-50"
        >
          저장
        </button>
      </section>

      {/* 최근 피드백 */}
      {(memory.feedback_history || []).length > 0 && (
        <section className="space-y-2">
          <h4 className="text-sm font-medium">최근 피드백</h4>
          <div className="space-y-1 text-xs text-muted-foreground max-h-32 overflow-y-auto">
            {(memory.feedback_history || []).slice(-5).map((fb, idx) => (
              <div key={idx} className="pl-2 border-l-2 border-muted">{fb}</div>
            ))}
          </div>
        </section>
      )}

      {/* 초기화 */}
      <div className="pt-2 border-t">
        <button
          onClick={clearMemory}
          aria-label="메모리 전체 초기화"
          className="text-xs text-red-500 hover:text-red-700"
        >
          메모리 전체 초기화
        </button>
      </div>
    </div>
  );
}
