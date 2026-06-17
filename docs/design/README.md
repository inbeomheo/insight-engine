# 디자인 참고 (Design Reference)

claude.ai/design에서 만든 디자인 시안을 **참고용으로 보관**하는 폴더입니다.
구현 코드가 아니며, Next.js 빌드/lint 대상이 아닙니다 (앱 트리 밖 `docs/` 하위).

## 출처

- **프로젝트**: Insight Engine Redesign
- **claude.ai/design**: https://claude.ai/design/p/2f69f454-5dc9-402c-a76d-aaa4ab487bc6

## 보관된 패키지

### `design_handoff_signal_redesign/` — "Signal" 리디자인 핸드오프

shadcn 기본 indigo 테마 → **에디토리얼 "Signal" 시스템**(따뜻한 페이퍼 캔버스 `#FAF8F4`,
잉크 `#17150F`, 액션 전용 버밀리언 액센트 `#EA4E20`, 메타/숫자에 JetBrains Mono)으로
전면 리디자인. 핵심 플로우(URL→스타일 선택→생성→에디터) + 라이브러리 + 대시보드,
데스크탑 + 모바일(하단 탭) 모두 포함.

> **승인 방향: A "Editorial Command."** B/C는 참고용 대안.

| 파일 | 설명 |
|---|---|
| `README.md` | 핸드오프 명세 (토큰표·화면별 스펙·인터랙션·코드 매핑) — **세부 구현 시 출발점** |
| `Insight Engine Redesign.dc.html` | 디자인 보드 (토큰 시스템 + A/B/C 방향 + 전 화면) |
| `Insight Engine Prototype.dc.html` | 클릭 가능한 데스크탑 프로토타입 (방향 A) |
| `Insight Engine Mobile.dc.html` | 클릭 가능한 모바일 프로토타입 (iPhone 프레임) |
| `globals.signal.css.patch.css` | `frontend/app/globals.css`의 `:root`/`.dark` 토큰 드롭인 교체본 |
| `support.js` | `.dc.html` 프로토타입 런타임 (Claude Design 익스포트 부속) |

`.dc.html`은 이미지·폰트·스타일이 인라인된 자체완결 HTML이라 브라우저에서 바로 열립니다.

## 향후 구현 시

실제 프론트엔드(`frontend/`, Next.js + shadcn/ui + Tailwind v4)에 반영하려면 별도 작업으로 진행합니다.
패키지 `README.md`의 "Mapping to existing code" 섹션이 컴포넌트별 반영 위치를 안내합니다.
현재는 **보관만** 합니다.
