'use client';

import { useState, useRef, useCallback } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface VoiceRecorderProps {
  onRecordingComplete: (file: File) => void;
  disabled?: boolean;
}

export default function VoiceRecorder({ onRecordingComplete, disabled }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const startRecording = useCallback(async () => {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });

      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        // 타이머 정리
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        // 스트림 트랙 중지
        stream.getTracks().forEach((t) => t.stop());

        const blob = new Blob(chunksRef.current, { type: mimeType });
        if (blob.size === 0) {
          setError('녹음 내용이 비어 있습니다.');
          return;
        }
        const ext = mimeType.includes('webm') ? 'webm' : 'wav';
        const file = new File([blob], `voice-memo-${Date.now()}.${ext}`, { type: mimeType });
        onRecordingComplete(file);
      };

      recorder.start(1000); // 1초마다 데이터 수집
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setDuration(0);

      // 타이머 시작
      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        setError('마이크 접근이 거부되었습니다. 브라우저 설정에서 마이크 권한을 허용해주세요.');
      } else {
        setError('마이크를 사용할 수 없습니다.');
      }
    }
  }, [onRecordingComplete]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }, []);

  return (
    <div>
      <div className="flex items-center gap-3">
        {recording ? (
          <>
            <Button
              variant="destructive"
              size="sm"
              className="gap-2"
              onClick={stopRecording}
              disabled={disabled}
            >
              <Square className="h-3.5 w-3.5" />
              녹음 중지
            </Button>
            <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite" role="status">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
              </span>
              <span className="font-mono tabular-nums">{formatDuration(duration)}</span>
            </div>
          </>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={startRecording}
            disabled={disabled}
          >
            <Mic className="h-3.5 w-3.5" />
            음성 녹음
          </Button>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </div>
  );
}
