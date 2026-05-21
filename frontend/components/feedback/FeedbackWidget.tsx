'use client';

/**
 * 앱 내 피드백 위젯 (F7-24)
 *
 * 사용자가 별점 + 코멘트를 남길 수 있는 플로팅 위젯.
 * 우측 하단에 고정 표시, 토글로 열기/닫기.
 */

import { useState } from 'react';

type FeedbackType = 'bug' | 'feature' | 'general';

interface FeedbackPayload {
  type: FeedbackType;
  rating: number;
  comment: string;
  page: string;
}

interface FeedbackWidgetProps {
  /** 피드백 수신 API 엔드포인트 (기본: /api/app-feedback) */
  apiEndpoint?: string;
  /** 위젯 제목 */
  title?: string;
}

export default function FeedbackWidget({
  apiEndpoint = '/api/app-feedback',
  title = '피드백 남기기',
}: FeedbackWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [type, setType] = useState<FeedbackType>('general');
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const feedbackTypes: { value: FeedbackType; label: string; emoji: string }[] = [
    { value: 'bug', label: '버그 신고', emoji: '🐛' },
    { value: 'feature', label: '기능 제안', emoji: '💡' },
    { value: 'general', label: '일반 의견', emoji: '💬' },
  ];

  const handleSubmit = async () => {
    if (rating === 0) {
      setErrorMsg('별점을 선택해주세요.');
      return;
    }
    if (!comment.trim()) {
      setErrorMsg('코멘트를 입력해주세요.');
      return;
    }

    setStatus('submitting');
    setErrorMsg('');

    const payload: FeedbackPayload = {
      type,
      rating,
      comment: comment.trim(),
      page: typeof window !== 'undefined' ? window.location.pathname : '/',
    };

    try {
      const resp = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        setStatus('success');
        // 2초 후 초기화
        setTimeout(() => {
          setStatus('idle');
          setRating(0);
          setComment('');
          setType('general');
          setIsOpen(false);
        }, 2000);
      } else {
        const data = await resp.json().catch(() => ({}));
        setErrorMsg(data.error || '전송 중 오류가 발생했습니다.');
        setStatus('error');
      }
    } catch {
      setErrorMsg('서버에 연결할 수 없습니다.');
      setStatus('error');
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setStatus('idle');
    setErrorMsg('');
  };

  return (
    <>
      {/* 플로팅 토글 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg transition-all hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        aria-label="피드백 위젯 열기/닫기"
      >
        {isOpen ? (
          <>
            <span>✕</span>
            <span>닫기</span>
          </>
        ) : (
          <>
            <span>💬</span>
            <span>피드백</span>
          </>
        )}
      </button>

      {/* 피드백 패널 */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-50 w-80 rounded-xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-800">
          {/* 헤더 */}
          <div className="flex items-center justify-between rounded-t-xl bg-indigo-600 px-4 py-3">
            <h3 className="text-sm font-semibold text-white">{title}</h3>
            <button
              onClick={handleClose}
              className="text-indigo-200 hover:text-white"
              aria-label="닫기"
            >
              ✕
            </button>
          </div>

          {/* 성공 상태 */}
          {status === 'success' ? (
            <div className="flex flex-col items-center gap-3 p-6 text-center">
              <span className="text-4xl">🎉</span>
              <p className="font-semibold text-gray-800 dark:text-gray-100">
                감사합니다!
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                소중한 피드백이 전달되었습니다.
              </p>
            </div>
          ) : (
            <div className="p-4">
              {/* 피드백 유형 */}
              <div className="mb-4">
                <label className="mb-1.5 block text-xs font-medium text-gray-500 dark:text-gray-400">
                  유형
                </label>
                <div className="flex gap-2">
                  {feedbackTypes.map((ft) => (
                    <button
                      key={ft.value}
                      onClick={() => setType(ft.value)}
                      aria-label={`${ft.label} 유형 선택`}
                      className={`flex-1 rounded-lg border px-2 py-1.5 text-xs font-medium transition-colors ${
                        type === ft.value
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300'
                          : 'border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-600 dark:text-gray-300'
                      }`}
                    >
                      {ft.emoji} {ft.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 별점 */}
              <div className="mb-4">
                <label className="mb-1.5 block text-xs font-medium text-gray-500 dark:text-gray-400">
                  만족도
                </label>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setRating(star)}
                      onMouseEnter={() => setHoveredRating(star)}
                      onMouseLeave={() => setHoveredRating(0)}
                      className="text-2xl transition-transform hover:scale-110"
                      aria-label={`${star}점`}
                    >
                      {star <= (hoveredRating || rating) ? '⭐' : '☆'}
                    </button>
                  ))}
                </div>
              </div>

              {/* 코멘트 */}
              <div className="mb-4">
                <label className="mb-1.5 block text-xs font-medium text-gray-500 dark:text-gray-400">
                  코멘트
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="의견을 자유롭게 남겨주세요..."
                  rows={3}
                  maxLength={500}
                  className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-indigo-400 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                />
                <p className="mt-0.5 text-right text-xs text-gray-400">
                  {comment.length}/500
                </p>
              </div>

              {/* 오류 메시지 */}
              {errorMsg && (
                <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/20 dark:text-red-400">
                  {errorMsg}
                </p>
              )}

              {/* 전송 버튼 */}
              <button
                onClick={handleSubmit}
                disabled={status === 'submitting'}
                aria-label="피드백 전송"
                className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {status === 'submitting' ? '전송 중...' : '피드백 전송'}
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
