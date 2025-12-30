/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'block-purple': '#8B5CF6',
        'block-blue': '#3B82F6',
        'block-orange': '#F97316',
        'block-yellow': '#EAB308',
        'block-green': '#22C55E',
      },
      fontFamily: {
        sans: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}

