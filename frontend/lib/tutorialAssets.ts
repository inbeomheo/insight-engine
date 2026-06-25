export interface TutorialOnboardingStep {
  id: string;
  title: string;
  description: string;
  imageSrc: string;
  imageAlt: string;
  fallbackLabel: string;
}

export const TUTORIAL_ONBOARDING_STEPS: TutorialOnboardingStep[] = [
  {
    id: 'source-input',
    title: '소스 붙여넣기',
    description: 'YouTube, 웹페이지, RSS, arXiv, Podcast 주소를 한 줄 입력창에 추가합니다.',
    imageSrc: '/tutorial/onboarding/01-source-input.svg',
    imageAlt: 'Insight Engine의 URL 입력 화면 예시',
    fallbackLabel: 'URL 입력 화면',
  },
  {
    id: 'style-select',
    title: '튜토리얼 스타일 선택',
    description: '출력 스타일에서 튜토리얼을 고르면 단계별 학습 가이드 형식으로 생성됩니다.',
    imageSrc: '/tutorial/onboarding/02-style-select.svg',
    imageAlt: 'Insight Engine의 출력 스타일 선택 화면 예시',
    fallbackLabel: '출력 스타일 선택 화면',
  },
  {
    id: 'result-review',
    title: '결과 확인과 활용',
    description: '생성된 튜토리얼을 확인하고 복사, 내보내기, 발행 준비 흐름으로 이어갑니다.',
    imageSrc: '/tutorial/onboarding/03-result-review.svg',
    imageAlt: 'Insight Engine의 결과 카드 확인 화면 예시',
    fallbackLabel: '결과 카드 화면',
  },
];
