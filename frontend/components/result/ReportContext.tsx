'use client';

import { createContext, useContext } from 'react';
import type { Report } from '@/lib/types';

/**
 * ResultCard 서브컴포넌트에서 report props 드릴링을 제거하기 위한 Context.
 * ResultCard가 Provider로 감싸고, 서브컴포넌트가 useReport()로 필요한 필드만 접근.
 */
const ReportContext = createContext<Report | null>(null);

export function ReportProvider({ report, children }: { report: Report; children: React.ReactNode }) {
  return <ReportContext.Provider value={report}>{children}</ReportContext.Provider>;
}

/** report 전체 객체 반환. ResultCard 하위에서만 사용. */
export function useReport(): Report {
  const ctx = useContext(ReportContext);
  if (!ctx) throw new Error('useReport는 ReportProvider 하위에서만 사용 가능합니다.');
  return ctx;
}

export default ReportContext;
