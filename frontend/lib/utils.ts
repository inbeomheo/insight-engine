import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** 모델 디스크 크기(바이트)를 사람이 읽는 단위로 변환. 값이 없으면 빈 문자열. */
export function formatModelSize(bytes?: number): string {
  if (!bytes || bytes <= 0) return ""
  const gb = bytes / 1e9
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  return `${Math.round(bytes / 1e6)} MB`
}
