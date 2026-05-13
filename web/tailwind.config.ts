import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          50:  "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
          950: "#172554",
        },
        neutral: {
          0:   "#ffffff",
          50:  "#f9fafb",
          100: "#f3f4f6",
          200: "#e5e7eb",
          300: "#d1d5db",
          400: "#9ca3af",
          500: "#6b7280",
          600: "#4b5563",
          700: "#374151",
          800: "#1f2937",
          900: "#111827",
          950: "#030712",
        },
        sidebar: {
          bg:     "#f9fafb",
          border: "#e5e7eb",
          item:   "#6b7280",
          hover:  "#f3f4f6",
          active: "#eff6ff",
          text:   "#111827",
        },
      },
      borderRadius: {
        "4xl": "2rem",
      },
      boxShadow: {
        xs:           "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        card:         "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
        elevated:     "0 4px 16px -2px rgb(0 0 0 / 0.08), 0 2px 4px -1px rgb(0 0 0 / 0.04)",
        "elevated-md":"0 8px 24px -4px rgb(0 0 0 / 0.10), 0 4px 8px -2px rgb(0 0 0 / 0.05)",
        "glow-brand": "0 0 24px -4px rgb(37 99 235 / 0.35)",
        focus:        "0 0 0 3px rgb(37 99 235 / 0.15)",
        "inner-sm":   "inset 0 1px 2px 0 rgb(0 0 0 / 0.06)",
      },
      backgroundImage: {
        "brand-gradient":  "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
        "dark-gradient":   "linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)",
        "subtle-gradient": "linear-gradient(180deg, #ffffff 0%, #f9fafb 100%)",
      },
      animation: {
        "fade-in":   "fadeIn 0.15s ease-out",
        "slide-up":  "slideUp 0.2s ease-out",
        "slide-in":  "slideIn 0.2s ease-out",
        "pulse-dot": "pulseDot 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%":   { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%":      { opacity: "0.5", transform: "scale(0.85)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
