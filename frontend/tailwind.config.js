/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#06121a',
        surface: '#102231',
        'surface-alt': '#132c3f',
        'surface-muted': '#0a1823',
        border: '#2a4b63',
        'text-body': '#d7e4f2',
        'text-muted': '#8fa9c0',
        primary: {
          DEFAULT: '#38bdf8',
          hover: '#0ea5e9',
        },
        info: '#0ea5e9',
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
      fontFamily: {
        sans: ['Manrope', 'sans-serif'],
        heading: ['Space Grotesk', 'Manrope', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
