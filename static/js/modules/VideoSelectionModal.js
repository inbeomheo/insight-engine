/**
 * VideoSelectionModal - 영상 선택 모달
 * 플레이리스트/채널의 영상 목록을 표시하고 선택할 수 있는 공유 모달
 */
import { getEventBus, EVENTS } from '../core/EventBus.js';

export class VideoSelectionModal {
    constructor(urlManager, ui, authManager) {
        this.urlManager = urlManager;
        this.ui = ui;
        this.authManager = authManager;
        this.videos = [];
        this.modal = null;

        this._createModal();
    }

    _createModal() {
        this.modal = document.createElement('div');
        this.modal.className = 'video-modal-overlay';
        this.modal.innerHTML = `
            <div class="video-modal">
                <div class="video-modal-header">
                    <h3 class="video-modal-title">
                        <span class="material-symbols-outlined">playlist_play</span>
                        <span class="video-modal-title-text">영상 목록</span>
                    </h3>
                    <button class="video-modal-close">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                <div class="video-modal-toolbar">
                    <label class="video-select-all">
                        <input type="checkbox" id="video-select-all-cb">
                        <span>전체 선택</span>
                    </label>
                    <span class="video-count">0개 선택</span>
                </div>
                <div class="video-modal-list" id="video-modal-list"></div>
                <div class="video-modal-footer">
                    <button class="video-modal-cancel">취소</button>
                    <button class="video-modal-add">
                        <span class="material-symbols-outlined">add</span>
                        <span>선택 추가</span>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);

        // 이벤트 바인딩
        this.modal.querySelector('.video-modal-close').addEventListener('click', () => this.close());
        this.modal.querySelector('.video-modal-cancel').addEventListener('click', () => this.close());
        this.modal.querySelector('.video-modal-add').addEventListener('click', () => this._addSelected());
        this.modal.addEventListener('click', (e) => { if (e.target === this.modal) this.close(); });

        // 전체 선택
        const selectAllCb = this.modal.querySelector('#video-select-all-cb');
        selectAllCb.addEventListener('change', () => {
            const checked = selectAllCb.checked;
            this.modal.querySelectorAll('.video-item-cb').forEach(cb => { cb.checked = checked; });
            this._updateCount();
        });
    }

    /**
     * 모달 열기
     * @param {Array} videos - [{video_id, title, thumbnail, view_count?, published_at?}]
     * @param {Object} options - {title: string, type: 'playlist'|'channel'}
     */
    open(videos, options = {}) {
        this.videos = videos;
        const titleText = this.modal.querySelector('.video-modal-title-text');
        const icon = this.modal.querySelector('.video-modal-title .material-symbols-outlined');

        if (options.type === 'channel') {
            titleText.textContent = options.title || '채널 영상';
            icon.textContent = 'subscriptions';
        } else {
            titleText.textContent = options.title || '플레이리스트';
            icon.textContent = 'playlist_play';
        }

        this._renderList(videos, options);
        this.modal.classList.add('active');
    }

    close() {
        this.modal.classList.remove('active');
    }

    _renderList(videos, options) {
        const list = this.modal.querySelector('#video-modal-list');
        const maxUrls = 10; // UrlManager 최대값

        list.innerHTML = videos.map((v, i) => {
            const viewCount = v.view_count ? `${Number(v.view_count).toLocaleString()}회` : '';
            const published = v.published_at ? new Date(v.published_at).toLocaleDateString('ko-KR') : '';
            const meta = [viewCount, published].filter(Boolean).join(' · ');

            return `
                <label class="video-item ${i >= maxUrls ? 'video-item--disabled' : ''}">
                    <input type="checkbox" class="video-item-cb" value="${v.video_id}"
                        ${i >= maxUrls ? 'disabled' : ''}>
                    <div class="video-item-thumb">
                        ${v.thumbnail ? `<img src="${v.thumbnail}" alt="" loading="lazy">` : '<span class="material-symbols-outlined">movie</span>'}
                    </div>
                    <div class="video-item-info">
                        <div class="video-item-title">${this.ui.escapeHtml(v.title)}</div>
                        ${meta ? `<div class="video-item-meta">${meta}</div>` : ''}
                    </div>
                </label>
            `;
        }).join('');

        // 체크박스 변경 시 카운트 업데이트
        list.querySelectorAll('.video-item-cb').forEach(cb => {
            cb.addEventListener('change', () => this._updateCount());
        });

        this._updateCount();
    }

    _updateCount() {
        const checked = this.modal.querySelectorAll('.video-item-cb:checked').length;
        this.modal.querySelector('.video-count').textContent = `${checked}개 선택`;
    }

    _addSelected() {
        const selected = Array.from(this.modal.querySelectorAll('.video-item-cb:checked'))
            .map(cb => cb.value);

        if (selected.length === 0) {
            this.ui.showAlert('영상을 선택해주세요.', 'warning');
            return;
        }

        // UrlManager에 URL 추가
        let added = 0;
        for (const videoId of selected) {
            const url = `https://www.youtube.com/watch?v=${videoId}`;
            const result = this.urlManager.parseAndAddUrls(url);
            if (result > 0) added++;
        }

        this.close();
        this.ui.showAlert(`${added}개 영상이 추가되었습니다.`, 'success');
    }

    /**
     * 플레이리스트 URL을 API에 요청하고 모달을 엽니다
     */
    async loadPlaylist(url) {
        try {
            const token = this.authManager?.getAccessToken?.() || '';
            const res = await fetch('/api/playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ url })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || '플레이리스트 조회 실패');

            this.open(data.videos, {
                title: data.playlist_title,
                type: 'playlist'
            });

            getEventBus().emit(EVENTS.PLAYLIST_LOADED, data);

        } catch (e) {
            this.ui.showAlert(e.message, 'error');
        }
    }

    /**
     * 채널 URL을 API에 요청하고 모달을 엽니다
     */
    async loadChannel(url) {
        try {
            const token = this.authManager?.getAccessToken?.() || '';
            const res = await fetch('/api/channel/videos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ url, max_results: 20 })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || '채널 영상 조회 실패');

            this.open(data.videos, {
                title: `채널 영상 (${data.total}개)`,
                type: 'channel'
            });

            getEventBus().emit(EVENTS.CHANNEL_LOADED, data);

        } catch (e) {
            this.ui.showAlert(e.message, 'error');
        }
    }
}
