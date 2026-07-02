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
        background: '#09090b',
        foreground: '#fafafa',
        primary: '#3b82f6',
        secondary: '#1e293b',
        muted: '#71717a',
        accent: '#8b5cf6',
      }
    },
  },
  plugins: [],
}
