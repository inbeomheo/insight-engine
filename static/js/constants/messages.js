/**
 * 에러 및 알림 메시지 상수
 * 중복된 문자열을 중앙 집중 관리
 */

// 인증 관련 메시지
export const AUTH_MESSAGES = {
    LOGIN_REQUIRED: '로그인이 필요합니다.',
    SESSION_EXPIRED: '세션이 만료되었습니다. 다시 로그인해주세요.',
    LOGIN_SUCCESS: '로그인되었습니다.',
    LOGOUT_SUCCESS: '로그아웃되었습니다.',
    INVALID_CREDENTIALS: '이메일 또는 비밀번호가 올바르지 않습니다.',
};

// 사용량 관련 메시지
export const USAGE_MESSAGES = {
    EXHAUSTED: '오늘 사용 가능 횟수를 모두 소진했습니다.',
    EXHAUSTED_RETRY: '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
    ADMIN_UNLIMITED: '관리자 - 무제한 사용',
    REMAINING: (count) => `남은 횟수: ${count}회`,
};

// URL 관련 메시지
export const URL_MESSAGES = {
    EMPTY: 'YouTube URL을 입력해주세요.',
    INVALID: '유효하지 않은 YouTube URL입니다.',
    FIRST_REQUIRED: 'YouTube URL을 먼저 입력해주세요.',
    DUPLICATE: '이미 추가된 URL입니다.',
    MAX_REACHED: (max) => `최대 ${max}개의 URL만 추가할 수 있습니다.`,
};

// 프로바이더 관련 메시지
export const PROVIDER_MESSAGES = {
    NO_PROVIDER: '사용 가능한 AI 서비스가 없습니다.',
    NO_MODEL: '모델을 선택해주세요.',
    API_KEY_INVALID: 'API 키가 유효하지 않습니다.',
    RATE_LIMIT: 'API 요청 제한에 도달했습니다. 잠시 후 다시 시도해주세요.',
};

// 콘텐츠 생성 관련 메시지
export const GENERATE_MESSAGES = {
    START: '콘텐츠 생성을 시작합니다.',
    IN_PROGRESS: '콘텐츠 생성 중...',
    COMPLETE: '콘텐츠 생성이 완료되었습니다.',
    ERROR: '콘텐츠 생성 중 오류가 발생했습니다.',
    ANALYSIS_ERROR: '분석 중 오류가 발생했습니다.',
    BATCH_ERROR: '배치 처리 중 오류가 발생했습니다.',
    NO_TRANSCRIPT: '이 영상에는 자막이 없습니다.',
};

// 네트워크 관련 메시지
export const NETWORK_MESSAGES = {
    CONNECTION_FAILED: '서버 연결에 실패했습니다. 네트워크 상태를 확인해주세요.',
    TIMEOUT: '요청 시간이 초과되었습니다. 다시 시도해주세요.',
    SERVER_ERROR: '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
    UNKNOWN: '알 수 없는 오류가 발생했습니다.',
};

// 스타일 관련 메시지
export const STYLE_MESSAGES = {
    CUSTOM_SAVED: '커스텀 스타일이 저장되었습니다.',
    CUSTOM_DELETED: '커스텀 스타일이 삭제되었습니다.',
    NAME_REQUIRED: '스타일 이름을 입력해주세요.',
    PROMPT_REQUIRED: '프롬프트를 입력해주세요.',
    MAX_REACHED: (max) => `최대 ${max}개의 커스텀 스타일만 생성할 수 있습니다.`,
};

// 클립보드 관련 메시지
export const CLIPBOARD_MESSAGES = {
    COPY_SUCCESS: '클립보드에 복사되었습니다.',
    COPY_FAILED: '클립보드 복사에 실패했습니다.',
};

// 캐시 관련 메시지
export const CACHE_MESSAGES = {
    CLEARED: '캐시가 삭제되었습니다.',
    CLEAR_FAILED: '캐시 삭제에 실패했습니다.',
};

// 버튼 타이틀
export const BUTTON_TITLES = {
    GENERATE: '콘텐츠 생성',
    GENERATING: '생성 중...',
    LOGIN_REQUIRED: '로그인이 필요합니다',
    USAGE_EXHAUSTED: '사용량 소진',
};

// HTTP 상태 코드별 메시지 매핑
export const HTTP_ERROR_MESSAGES = {
    400: '잘못된 요청입니다.',
    401: AUTH_MESSAGES.LOGIN_REQUIRED,
    403: '접근 권한이 없습니다.',
    404: '요청한 리소스를 찾을 수 없습니다.',
    429: USAGE_MESSAGES.EXHAUSTED,
    500: NETWORK_MESSAGES.SERVER_ERROR,
    502: '서버가 일시적으로 사용 불가능합니다.',
    503: '서비스가 일시적으로 중단되었습니다.',
};

/**
 * HTTP 상태 코드에 맞는 에러 메시지 조회
 * @param {number} status - HTTP 상태 코드
 * @param {string} fallback - 기본 메시지
 * @returns {string}
 */
export function getHttpErrorMessage(status, fallback = NETWORK_MESSAGES.UNKNOWN) {
    return HTTP_ERROR_MESSAGES[status] || fallback;
}

/**
 * 네트워크 에러를 한국어 메시지로 변환
 * @param {Error} error - 에러 객체
 * @returns {string}
 */
export function getKoreanErrorMessage(error) {
    if (!error || !error.message) {
        return NETWORK_MESSAGES.UNKNOWN;
    }

    const msg = error.message.toLowerCase();

    if (msg.includes('failed to fetch') || msg.includes('network')) {
        return NETWORK_MESSAGES.CONNECTION_FAILED;
    }

    if (msg.includes('timeout') || msg.includes('timed out')) {
        return NETWORK_MESSAGES.TIMEOUT;
    }

    if (msg.includes('abort')) {
        return '요청이 취소되었습니다.';
    }

    return error.message;
}

export default {
    AUTH: AUTH_MESSAGES,
    USAGE: USAGE_MESSAGES,
    URL: URL_MESSAGES,
    PROVIDER: PROVIDER_MESSAGES,
    GENERATE: GENERATE_MESSAGES,
    NETWORK: NETWORK_MESSAGES,
    STYLE: STYLE_MESSAGES,
    CLIPBOARD: CLIPBOARD_MESSAGES,
    CACHE: CACHE_MESSAGES,
    BUTTON: BUTTON_TITLES,
    getHttpErrorMessage,
    getKoreanErrorMessage,
};
