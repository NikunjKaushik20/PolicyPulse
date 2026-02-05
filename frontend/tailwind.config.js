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
        background: "hsl(var(--pk-primary))",
        sidebar: "hsl(var(--pk-sidebar))",
        primary: "hsl(var(--pk-accent))",
        "text-primary": "hsl(var(--pk-text-primary))",
        "text-secondary": "hsl(var(--pk-text-secondary))",
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
