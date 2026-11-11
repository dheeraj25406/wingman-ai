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
          sidebar: '#0C0C0C',
          surface: '#111111',
          raised: '#171717',
          hover: '#1D1D1D',
        },
        border: {
          subtle: '#1B1B1B',
          primary: '#252525',
          strong: '#303030',
        },
        text: {
          primary: '#EAE8E3',
          secondary: '#A09E98',
          muted: '#686761',
        },
        accent: {
          DEFAULT: '#EAE8E3',
          subtle: '#AAA69E',
          hover: '#FFFFFF',
        },
        status: {
          coral: '#D66A61',
          amber: '#D6A65D',
          sage: '#75A98B',
          neutral: '#AAA69E',
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
