/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'Inter var',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'sans-serif',
        ],
      },
      colors: {
        brand: {
          50: '#f5f3ff',
          100: '#ede8ff',
          200: '#ddd5ff',
          300: '#c3b4ff',
          400: '#a184ff',
          500: '#8155f7',
          600: '#6d38eb',
          700: '#5b26cf',
          800: '#4a20a8',
          900: '#3d1c87',
        },
        ink: {
          900: '#0b0b0f',
          800: '#16161d',
          700: '#24242e',
        },
      },
      letterSpacing: {
        tightest: '-0.025em',
        label: '0.08em',
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        card: '0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)',
        panel: '0 1px 2px rgba(16, 24, 40, 0.04), 0 12px 32px -16px rgba(16, 24, 40, 0.16)',
        float: '0 24px 64px -24px rgba(16, 24, 40, 0.28)',
        glow: '0 0 0 1px rgba(109, 56, 235, 0.16), 0 12px 40px -12px rgba(109, 56, 235, 0.32)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.24s cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-in': 'slide-in 0.24s cubic-bezier(0.16, 1, 0.3, 1) both',
      },
    },
  },
  plugins: [],
}
