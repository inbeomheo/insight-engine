'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Play, Pause, Download, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';

interface AudioPlayerProps {
  audioBlob: Blob;
  title?: string;
  onClose?: () => void;
}

const SPEED_OPTIONS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

/** 초를 mm:ss 형식으로 변환합니다. */
function formatTime(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ audioBlob, title, onClose }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState(1.0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  // audioBlob이 바뀌면 Object URL 재생성
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const url = URL.createObjectURL(audioBlob);
    setAudioUrl(url);
    setPlaying(false);
    setCurrentTime(0);
    return () => URL.revokeObjectURL(url);
  }, [audioBlob]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // 오디오 이벤트 등록
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;

    audio.src = audioUrl;
    audio.playbackRate = speed;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => setDuration(audio.duration);
    const onEnded = () => setPlaying(false);

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
    };
  }, [audioUrl, speed]);

  // 재생 속도 변경
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
    }
  }, [speed]);

  const togglePlay = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      await audio.play();
      setPlaying(true);
    }
  }, [playing]);

  const handleSeek = useCallback((values: number[]) => {
    const audio = audioRef.current;
    if (!audio) return;
    const t = values[0];
    audio.currentTime = t;
    setCurrentTime(t);
  }, []);

  function handleDownload() {
    if (!audioUrl) return;
    const a = document.createElement('a');
    a.href = audioUrl;
    a.download = `${(title ?? 'podcast').slice(0, 50)}.mp3`;
    a.click();
  }

  // 파형 애니메이션 바 (CSS-only)
  const bars = Array.from({ length: 5 }, (_, i) => i);

  return (
    <div className="mt-4 rounded-xl border border-border/50 bg-muted/30 p-4 space-y-3">
      {/* 숨겨진 오디오 엘리먼트 */}
      <audio ref={audioRef} preload="metadata" />

      {/* 상단: 제목 + 닫기 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          {/* 파형 애니메이션 */}
          <div className="flex items-end gap-[2px] h-5 shrink-0">
            {bars.map((i) => (
              <span
                key={i}
                className={`block w-[3px] rounded-full bg-primary transition-all ${
                  playing ? 'animate-pulse' : ''
                }`}
                style={{
                  height: playing ? `${55 + ((i * 17) % 45)}%` : '30%',
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>
          <span className="text-sm font-medium truncate text-foreground/80">
            {title ?? '팟캐스트'}
          </span>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleDownload}
            title="MP3 다운로드"
          >
            <Download className="h-3.5 w-3.5" />
          </Button>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onClose}
              title="닫기"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* 진행 바 */}
      <div className="space-y-1">
        <Slider
          min={0}
          max={duration || 1}
          step={0.1}
          value={[currentTime]}
          onValueChange={handleSeek}
          className="w-full"
        />
        <div className="flex justify-between text-[11px] text-muted-foreground">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* 컨트롤 */}
      <div className="flex items-center justify-between">
        {/* 재생/일시정지 */}
        <Button
          variant="default"
          size="sm"
          className="gap-1.5"
          onClick={togglePlay}
        >
          {playing ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {playing ? '일시정지' : '재생'}
        </Button>

        {/* 속도 선택 */}
        <div className="flex items-center gap-1">
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSpeed(s)}
              aria-label={`재생 속도 ${s}배`}
              className={`px-1.5 py-0.5 rounded text-xs font-mono transition-colors ${
                speed === s
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
