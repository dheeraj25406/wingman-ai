/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          app: '#090909',
          primary: '#090909',
          sidebar: '#0D0D0D',
          surface: '#111111',
          secondary: '#191919',
          elevated: '#222222',
          raised: '#222222',
          hover: '#292929',
        },
        border: {
          subtle: '#252525',
          primary: '#252525',
          normal: '#303030',
          strong: '#404040',
        },
        text: {
          primary: '#F2F2F2',
          secondary: '#BDBDBD',
          muted: '#858585',
          disabled: '#5C5C5C',
        },
        accent: {
          DEFAULT: '#F2F2F2',
          primary: '#F2F2F2',
          subtle: '#BDBDBD',
          hover: '#FFFFFF',
          lavender: '#BDBDBD',
        },
        status: {
          critical: '#D96C6C',
          coral: '#D96C6C',
          warning: '#D9A65F',
          amber: '#D9A65F',
          healthy: '#79B68A',
          sage: '#79B68A',
          neutral: '#BDBDBD',
          lavender: '#BDBDBD',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Geist Mono', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '4px',
        sm: '3px',
        md: '6px',
        lg: '8px',
      }
    },
  },
  plugins: [],
}
