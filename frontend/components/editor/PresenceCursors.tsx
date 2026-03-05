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

/** 다른 참가자의 커서 위치를 표시합니다 (F5-02) */
export default function PresenceCursors({ participants }: PresenceCursorsProps) {
  if (participants.length === 0) return null;

  return (
    <div className="absolute top-0 left-0 pointer-events-none" aria-hidden="true">
      {participants.map((p) => (
        <div
          key={p.user_id}
          className="absolute flex items-start gap-0"
          style={{
            // 커서 위치를 대략적으로 표시 (글자 수 기반 근사)
            top: `${Math.floor(p.cursor_position / 80) * 20 + 16}px`,
            left: `${(p.cursor_position % 80) * 7.8 + 16}px`,
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
