/**
 * ReportFormatter - 데이터 포맷 유틸리티
 * 정적 메서드로 URL, 시간, ID 등의 포맷팅 담당
 */
export class ReportFormatter {
    /**
     * URL을 짧은 형식으로 변환
     * @param {string} url - 원본 URL
     * @param {number} maxLength - 최대 길이
     * @returns {string} 포맷된 URL
     */
    static formatShortUrl(url, maxLength = 40) {
        const stripped = url.replace(/^https?:\/\//, '');
        return stripped.length > maxLength ? `${stripped.substring(0, maxLength)}...` : stripped;
    }

    /**
     * 현재 시간을 한국어 형식으로 반환
     * @returns {string} 포맷된 시간 문자열 (예: "14:30")
     */
    static getCurrentTimeStr() {
        return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    }

    /**
     * 유니크한 pending ID 생성
     * @returns {string} 고유 ID
     */
    static generatePendingId() {
        return `pending_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    }

    /**
     * 메타정보를 텍스트로 포맷
     * @param {Object} data - 리포트 데이터
     * @returns {string} 포맷된 메타 텍스트
     */
    static buildMetaText(data) {
        const lines = [];
        lines.push(`제목: ${data.title}`);
        lines.push(`스타일: ${data.style}`);
        lines.push(`생성 시간: ${data.time}`);
        if (data.usage?.total_tokens) {
            lines.push(`총 토큰: ${data.usage.total_tokens.toLocaleString()}`);
        }
        if (data.usage?.prompt_tokens) {
            lines.push(`입력 토큰: ${data.usage.prompt_tokens.toLocaleString()}`);
        }
        if (data.usage?.completion_tokens) {
            lines.push(`출력 토큰: ${data.usage.completion_tokens.toLocaleString()}`);
        }
        if (data.elapsed_time) {
            lines.push(`처리 시간: ${data.elapsed_time}초`);
        }
        return lines.join('\n');
    }
}
