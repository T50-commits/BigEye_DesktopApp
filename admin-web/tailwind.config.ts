import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        "bg-root": "#f5f7fa",
        "bg-surface": "#ffffff",
        "bg-elevated": "#f0f2f5",
        "bg-input": "#f8f9fb",
        "bg-hover": "#e8ecf1",
        "bdr": "#d1d9e6",
        "bdr-hover": "#b0bdd0",
        "txt-primary": "#1a202c",
        "txt-secondary": "#4a5568",
        "txt-muted": "#a0aec0",
        "accent-blue": "#3b82f6",
        "accent-cyan": "#0891b2",
        "accent-green": "#059669",
        "accent-yellow": "#d97706",
        "accent-red": "#dc2626",
        "accent-purple": "#7c3aed",
        "accent-pink": "#db2777",
        "accent-orange": "#ea580c",
      },
      fontFamily: {
        sans: ["Geist", "IBM Plex Sans Thai", "sans-serif"],
        mono: ["Geist Mono", "JetBrains Mono", "monospace"],
      },
      borderRadius: {
        card: "16px",
        btn: "10px",
        input: "10px",
      },
    },
  },
  plugins: [],
};
export default config;
