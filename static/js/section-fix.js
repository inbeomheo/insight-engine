// 섹션 레이아웃 수정 - 모든 섹션이 펼쳐진 상태로 표시되도록 함
document.addEventListener('DOMContentLoaded', function() {
    // 모든 섹션에 flex 스타일 적용 (레이아웃 문제 해결)
    ['url-section', 'ai-model-section', 'style-section', 'modifier-section'].forEach(function(id) {
        var section = document.getElementById(id);
        if (section) {
            section.style.flex = '0 0 auto';
        }
    });

    // 모든 패널이 표시되도록 설정
    ['url-section-panel', 'ai-model-panel', 'style-section-panel', 'advanced-options-panel'].forEach(function(id) {
        var panel = document.getElementById(id);
        if (panel) {
            panel.style.display = 'block';
        }
    });

    console.log('[section-fix.js] 섹션 레이아웃 수정 완료');
});
