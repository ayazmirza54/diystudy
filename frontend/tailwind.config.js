/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        comet: {
          dark: '#1a1e24',
          accent: '#8be9fd',
        },
      },
    },
  },
  plugins: [],
};