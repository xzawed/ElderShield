/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#ecfdf7',
          100: '#d1faf0',
          500: '#0d9488',
          600: '#0f766e',
          700: '#115e59',
          900: '#134e4a',
        },
        ink: {
          950: '#0b1220',
          800: '#1e293b',
          600: '#475569',
          400: '#94a3b8',
        },
      },
      fontFamily: {
        sans: ['"Source Sans 3"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Fraunces"', 'Georgia', 'serif'],
      },
      boxShadow: {
        panel:
          '0 1px 2px rgba(15,23,42,0.04), 0 8px 24px rgba(15,23,42,0.06)',
      },
    },
  },
  plugins: [],
}