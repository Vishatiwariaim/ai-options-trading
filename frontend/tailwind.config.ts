import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#131722",
        panel2: "#1c2230",
        accent: "#3b82f6",
        bull: "#16c784",
        bear: "#ea3943",
      },
    },
  },
  plugins: [],
};

export default config;
