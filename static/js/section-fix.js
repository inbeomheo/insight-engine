// 섹션 레이아웃 수정 - flex 스타일만 적용 (접기/펼치기 기능 유지)
document.addEventListener('DOMContentLoaded', function() {
    // 모든 섹션에 flex 스타일 적용 (레이아웃 문제 해결)
    ['url-section', 'ai-model-section', 'style-section', 'modifier-section'].forEach(function(id) {
        var section = document.getElementById(id);
        if (section) {
            section.style.flex = '0 0 auto';
        }
    });

    // 패널 강제 표시 제거 - 접기/펼치기 기능이 정상 작동하도록 함

    console.log('[section-fix.js] 섹션 레이아웃 수정 완료');
});
