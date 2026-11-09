import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#080b12",
          900: "#0c111b",
          850: "#111827",
          800: "#151d2c",
          700: "#1f2a3c",
          600: "#2b3a52",
        },
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
        },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(16, 185, 129, 0.25), 0 12px 40px -12px rgba(16, 185, 129, 0.35)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
