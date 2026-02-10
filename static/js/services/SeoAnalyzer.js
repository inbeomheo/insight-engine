/**
 * SeoAnalyzer - SEO 점수 분석 (프론트엔드 전용)
 * HTML 콘텐츠를 파싱하여 8개 항목 기준 100점 만점 점수 산출
 */
export class SeoAnalyzer {
    /**
     * HTML 콘텐츠의 SEO 점수를 분석합니다.
     * @param {string} html - 분석할 HTML 문자열
     * @param {string} title - 콘텐츠 제목
     * @param {string[]} keywords - 키워드 목록
     * @returns {{score: number, items: Array<{name: string, score: number, max: number, detail: string}>}}
     */
    static analyze(html, title = '', keywords = []) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(`<div>${html}</div>`, 'text/html');
        const body = doc.body.firstChild;
        const text = body?.textContent || '';

        const items = [
            this._checkMetaDescription(body, text),
            this._checkTitle(body, title),
            this._checkHeadingStructure(body),
            this._checkParagraphReadability(body),
            this._checkKeywordDensity(body, text, title, keywords),
            this._checkListAndTable(body),
            this._checkLinks(body),
            this._checkCodeBlocks(body)
        ];

        const score = items.reduce((sum, item) => sum + item.score, 0);
        return { score, items };
    }

    /**
     * 메타 설명 (15점): 첫 단락이 155자 이내의 요약 역할을 하는지
     */
    static _checkMetaDescription(body, text) {
        const firstP = body?.querySelector('p');
        const firstText = firstP?.textContent?.trim() || '';
        let score = 0;
        let detail = '';

        if (!firstText) {
            detail = '첫 단락이 없습니다';
        } else if (firstText.length <= 155) {
            score = 15;
            detail = `첫 단락 ${firstText.length}자 (적절)`;
        } else if (firstText.length <= 200) {
            score = 10;
            detail = `첫 단락 ${firstText.length}자 (약간 김)`;
        } else {
            score = 5;
            detail = `첫 단락 ${firstText.length}자 (너무 김, 155자 이내 권장)`;
        }

        return { name: '메타 설명', score, max: 15, detail };
    }

    /**
     * 제목 (10점): H1 존재 + 10~60자
     */
    static _checkTitle(body, title) {
        const h1 = body?.querySelector('h1');
        const titleText = h1?.textContent?.trim() || title || '';
        let score = 0;
        let detail = '';

        if (!titleText) {
            detail = '제목(H1)이 없습니다';
        } else {
            const len = titleText.length;
            if (len >= 10 && len <= 60) {
                score = 10;
                detail = `제목 ${len}자 (적절)`;
            } else if (len < 10) {
                score = 5;
                detail = `제목 ${len}자 (너무 짧음, 10자 이상 권장)`;
            } else {
                score = 7;
                detail = `제목 ${len}자 (약간 김, 60자 이내 권장)`;
            }
        }

        return { name: '제목', score, max: 10, detail };
    }

    /**
     * 소제목 구조 (15점): H2 2개+ / H3 사용
     */
    static _checkHeadingStructure(body) {
        const h2s = body?.querySelectorAll('h2') || [];
        const h3s = body?.querySelectorAll('h3') || [];
        let score = 0;
        const details = [];

        if (h2s.length >= 2) {
            score += 10;
            details.push(`H2 ${h2s.length}개`);
        } else if (h2s.length === 1) {
            score += 5;
            details.push(`H2 1개 (2개 이상 권장)`);
        } else {
            details.push('H2 없음');
        }

        if (h3s.length > 0) {
            score += 5;
            details.push(`H3 ${h3s.length}개`);
        }

        return { name: '소제목 구조', score, max: 15, detail: details.join(', ') || 'H2/H3 없음' };
    }

    /**
     * 단락 가독성 (15점): 평균 50~200자
     */
    static _checkParagraphReadability(body) {
        const ps = body?.querySelectorAll('p') || [];
        if (ps.length === 0) {
            return { name: '단락 가독성', score: 0, max: 15, detail: '단락이 없습니다' };
        }

        const lengths = Array.from(ps).map(p => p.textContent.trim().length).filter(l => l > 0);
        if (lengths.length === 0) {
            return { name: '단락 가독성', score: 0, max: 15, detail: '빈 단락만 있습니다' };
        }

        const avg = Math.round(lengths.reduce((a, b) => a + b, 0) / lengths.length);
        let score = 0;
        let detail = '';

        if (avg >= 50 && avg <= 200) {
            score = 15;
            detail = `평균 ${avg}자/단락 (적절)`;
        } else if (avg < 50) {
            score = 8;
            detail = `평균 ${avg}자/단락 (너무 짧음)`;
        } else {
            score = 8;
            detail = `평균 ${avg}자/단락 (너무 김, 200자 이내 권장)`;
        }

        return { name: '단락 가독성', score, max: 15, detail };
    }

    /**
     * 키워드 밀도 (15점): 제목+본문에서 키워드 반복률 1~3%
     */
    static _checkKeywordDensity(body, text, title, keywords) {
        if (!keywords || keywords.length === 0) {
            return { name: '키워드 밀도', score: 5, max: 15, detail: '키워드 없음 (자동 추출 키워드로 분석)' };
        }

        const fullText = (title + ' ' + text).toLowerCase();
        const totalChars = fullText.length;
        if (totalChars === 0) {
            return { name: '키워드 밀도', score: 0, max: 15, detail: '텍스트가 없습니다' };
        }

        let totalMatches = 0;
        keywords.forEach(kw => {
            const kwLower = kw.toLowerCase();
            let idx = 0;
            while ((idx = fullText.indexOf(kwLower, idx)) !== -1) {
                totalMatches++;
                idx += kwLower.length;
            }
        });

        const avgKeywordLen = keywords.reduce((sum, kw) => sum + kw.length, 0) / keywords.length;
        const density = (totalMatches * avgKeywordLen / totalChars) * 100;
        let score = 0;
        let detail = '';

        if (density >= 1 && density <= 3) {
            score = 15;
            detail = `밀도 ${density.toFixed(1)}% (적절)`;
        } else if (density > 0 && density < 1) {
            score = 8;
            detail = `밀도 ${density.toFixed(1)}% (낮음, 1~3% 권장)`;
        } else if (density > 3) {
            score = 8;
            detail = `밀도 ${density.toFixed(1)}% (과다, 3% 이하 권장)`;
        } else {
            score = 3;
            detail = '키워드가 본문에 없습니다';
        }

        return { name: '키워드 밀도', score, max: 15, detail };
    }

    /**
     * 목록/표 활용 (10점): ul/ol/table 존재
     */
    static _checkListAndTable(body) {
        const lists = body?.querySelectorAll('ul, ol') || [];
        const tables = body?.querySelectorAll('table') || [];
        let score = 0;
        const details = [];

        if (lists.length > 0) {
            score += 6;
            details.push(`목록 ${lists.length}개`);
        }
        if (tables.length > 0) {
            score += 4;
            details.push(`표 ${tables.length}개`);
        }

        if (score === 0) {
            return { name: '목록/표 활용', score: 0, max: 10, detail: '목록이나 표가 없습니다' };
        }

        return { name: '목록/표 활용', score, max: 10, detail: details.join(', ') };
    }

    /**
     * 링크/참조 (10점): a 태그 존재
     */
    static _checkLinks(body) {
        const links = body?.querySelectorAll('a[href]') || [];
        let score = 0;
        let detail = '';

        if (links.length >= 2) {
            score = 10;
            detail = `링크 ${links.length}개`;
        } else if (links.length === 1) {
            score = 5;
            detail = '링크 1개 (2개 이상 권장)';
        } else {
            score = 0;
            detail = '링크가 없습니다';
        }

        return { name: '링크/참조', score, max: 10, detail };
    }

    /**
     * 코드 블록/강조 (10점): code/pre/strong/em 태그 사용
     */
    static _checkCodeBlocks(body) {
        const codes = body?.querySelectorAll('code, pre') || [];
        const strongs = body?.querySelectorAll('strong, b') || [];
        const ems = body?.querySelectorAll('em, i') || [];
        let score = 0;
        const details = [];

        if (codes.length > 0) {
            score += 4;
            details.push(`코드 ${codes.length}개`);
        }
        if (strongs.length > 0) {
            score += 3;
            details.push(`굵게 ${strongs.length}개`);
        }
        if (ems.length > 0) {
            score += 3;
            details.push(`기울임 ${ems.length}개`);
        }

        if (score === 0) {
            return { name: '텍스트 강조', score: 0, max: 10, detail: '강조나 코드 블록이 없습니다' };
        }

        return { name: '텍스트 강조', score, max: 10, detail: details.join(', ') };
    }

    /**
     * 점수에 따른 등급 반환
     */
    static getGrade(score) {
        if (score >= 90) return { label: 'A+', color: '#10b981' };
        if (score >= 80) return { label: 'A', color: '#10b981' };
        if (score >= 70) return { label: 'B+', color: '#3b82f6' };
        if (score >= 60) return { label: 'B', color: '#3b82f6' };
        if (score >= 50) return { label: 'C', color: '#f59e0b' };
        return { label: 'D', color: '#ef4444' };
    }
}
