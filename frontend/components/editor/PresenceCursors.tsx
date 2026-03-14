'use client';

interface Participant {
  user_id: string;
  name: string;
  cursor_position: number;
  color: string;
}

interface PresenceCursorsProps {
  participants: Participant[];
}

/**
 * 다른 참가자의 커서 위치를 표시합니다 (F5-02)
 *
 * 제한사항: 텍스트 리플로우를 추적하지 않으므로 실제 커서와 오차 발생 가능.
 * 정확한 동기화는 contentEditable + Range API 기반 리팩토링 필요.
 */
export default function PresenceCursors({ participants }: PresenceCursorsProps) {
  if (participants.length === 0) return null;

  // em 기반 근사치 (가변폭 폰트 대응)
  // 한글: ~1.0em, 영문/숫자: ~0.6em → 평균 0.7em으로 근사
  const avgCharWidth = 0.7; // em 단위
  const lineHeight = 1.5; // leading-relaxed (tailwind)
  const fontSize = 14; // text-sm = 14px
  const charsPerLine = 80;
  const padding = 16; // p-4 = 16px

  return (
    <div className="absolute top-0 left-0 pointer-events-none" aria-hidden="true">
      {participants.map((p) => (
        <div
          key={p.user_id}
          className="absolute flex items-start gap-0"
          style={{
            top: `${Math.floor(p.cursor_position / charsPerLine) * (fontSize * lineHeight) + padding}px`,
            left: `${(p.cursor_position % charsPerLine) * (fontSize * avgCharWidth) + padding}px`,
          }}
        >
          {/* 커서 라인 */}
          <div
            className="w-0.5 h-5 rounded-full animate-pulse"
            style={{ backgroundColor: p.color }}
          />
          {/* 이름 라벨 */}
          <div
            className="px-1.5 py-0.5 rounded text-[9px] font-medium text-white -mt-4 ml-0.5 whitespace-nowrap"
            style={{ backgroundColor: p.color }}
          >
            {p.name}
          </div>
        </div>
      ))}
    </div>
  );
}
