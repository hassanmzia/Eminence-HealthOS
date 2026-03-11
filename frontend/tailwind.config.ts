import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        healthos: {
          50: "#eef7ff",
          100: "#d8edff",
          200: "#b9dfff",
          300: "#89ccff",
          400: "#52afff",
          500: "#2a8cff",
          600: "#136bfa",
          700: "#0c55e6",
          800: "#1145ba",
          900: "#143d92",
          950: "#112759",
        },
      },
    },
  },
  plugins: [],
};

export default config;
