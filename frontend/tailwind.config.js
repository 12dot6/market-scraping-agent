/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#7C3AED",
        amber: { DEFAULT: "#F59E0B" },
        success: "#10B981",
      },
    },
  },
  plugins: [],
};
