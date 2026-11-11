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
          app: '#0D1117',
          sidebar: '#111720',
          surface: '#151D27',
          raised: '#1A2430',
        },
        border: {
          subtle: '#222C38',
          strong: '#293442',
        },
        text: {
          primary: '#E6EDF3',
          secondary: '#929EAD',
          muted: '#647184',
        },
        accent: {
          DEFAULT: '#65A9FF',
          hover: '#82BAFF',
        },
        status: {
          success: '#35B88A',
          warning: '#E8B45B',
          critical: '#E16B73',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Geist Mono', 'JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
