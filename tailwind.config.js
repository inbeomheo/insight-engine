/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  safelist: [
    'url-input-group',
    'dragging',
    'drag-over',
  ],
  theme: {
    extend: {
      /* ----------------------------------------
         Colors - CSS 변수 기반 색상
         ---------------------------------------- */
      colors: {
        // Background Colors - _tokens.css 변수 참조
        'bg-primary': 'var(--background-dark)',
        'bg-secondary': 'var(--surface-dark)',
        'bg-tertiary': 'var(--card-dark)',
        'bg-surface': 'var(--surface-dark)',
        'bg-overlay': 'var(--bg-overlay)',
        'background-dark': 'var(--background-dark)',
        'card-dark': 'var(--card-dark)',
        'bg-elevated': 'var(--bg-elevated)',
        'surface-lighter': 'var(--bg-elevated)',

        // Text Colors
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-tertiary': 'var(--text-tertiary)',
        'text-muted': 'var(--text-muted)',
        'text-subtle': 'var(--text-subtle)',
        'text-inverse': 'var(--text-inverse)',

        // Brand Colors - _tokens.css의 --primary 직접 참조
        'primary': 'var(--primary)',
        'primary-hover': 'var(--primary-hover)',
        'primary-light': 'var(--primary-light)',
        'primary-dark': 'var(--primary-dark)',
        'primary-glow': 'var(--primary-glow)',

        // Semantic Colors
        'success': 'var(--color-success)',
        'warning': 'var(--color-warning)',
        'error': 'var(--color-error)',
        'info': 'var(--color-info)',

        // Border Colors
        'border-primary': 'var(--border-primary)',
        'border-secondary': 'var(--border-secondary)',
        'border-focus': 'var(--border-focus)',
        'border-dark': 'var(--border-dark)',
        'card-border': 'var(--card-border)',

        // Surface Colors (컴포넌트용)
        'surface-dark': 'var(--surface-dark)',
      },

      /* ----------------------------------------
         Typography - CSS 변수 기반 타이포그래피
         ---------------------------------------- */
      fontSize: {
        'xs': 'var(--font-size-xs)',
        'sm': 'var(--font-size-sm)',
        'base': 'var(--font-size-base)',
        'lg': 'var(--font-size-lg)',
        'xl': 'var(--font-size-xl)',
        '2xl': 'var(--font-size-2xl)',
        '3xl': 'var(--font-size-3xl)',
      },
      lineHeight: {
        'tight': 'var(--line-height-tight)',
        'normal': 'var(--line-height-normal)',
        'relaxed': 'var(--line-height-relaxed)',
      },
      fontWeight: {
        'normal': 'var(--font-weight-normal)',
        'medium': 'var(--font-weight-medium)',
        'semibold': 'var(--font-weight-semibold)',
        'bold': 'var(--font-weight-bold)',
      },

      /* ----------------------------------------
         Spacing - CSS 변수 기반 간격
         ---------------------------------------- */
      spacing: {
        'token-1': 'var(--spacing-1)',
        'token-2': 'var(--spacing-2)',
        'token-3': 'var(--spacing-3)',
        'token-4': 'var(--spacing-4)',
        'token-5': 'var(--spacing-5)',
        'token-6': 'var(--spacing-6)',
        'token-7': 'var(--spacing-7)',
        'token-8': 'var(--spacing-8)',
      },

      /* ----------------------------------------
         Shadows - CSS 변수 기반 그림자
         ---------------------------------------- */
      boxShadow: {
        'token-sm': 'var(--shadow-sm)',
        'token-md': 'var(--shadow-md)',
        'token-lg': 'var(--shadow-lg)',
        'token-xl': 'var(--shadow-xl)',
        'token-glow': 'var(--shadow-glow)',
        'token-primary': 'var(--shadow-primary)',
      },

      /* ----------------------------------------
         Transitions - CSS 변수 기반 트랜지션
         ---------------------------------------- */
      transitionDuration: {
        'fast': '150ms',
        'normal': '200ms',
        'slow': '300ms',
      },
      transitionTimingFunction: {
        'ease': 'ease-in-out',
      },

      /* ----------------------------------------
         Border Radius - CSS 변수 기반 모서리 반경
         ---------------------------------------- */
      borderRadius: {
        'token-sm': 'var(--radius-sm)',
        'token-md': 'var(--radius-md)',
        'token-lg': 'var(--radius-lg)',
        'token-xl': 'var(--radius-xl)',
        'token-full': 'var(--radius-full)',
      },
    },
  },
  plugins: [],
}
