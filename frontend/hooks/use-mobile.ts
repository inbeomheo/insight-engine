import * as React from "react"

// 앱의 모바일/데스크톱 분기는 Tailwind `xl`(1280px) 기준이다.
// (app/page.tsx: 모바일 셸은 `xl:hidden`, 데스크톱 셸은 `hidden xl:flex`)
// 여기서 768을 쓰면 CSS 분기와 JS 분기가 어긋나 768~1279px 구간에서
// "모바일 셸인데 isMobile === false"인 모순이 생긴다.
const MOBILE_BREAKPOINT = 1280

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    // 판정 기준을 matchMedia 한 곳으로 통일 (innerWidth와 이중 관리하지 않는다)
    const onChange = (event: MediaQueryListEvent) => setIsMobile(event.matches)
    mql.addEventListener("change", onChange)
    setIsMobile(mql.matches)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return !!isMobile
}
