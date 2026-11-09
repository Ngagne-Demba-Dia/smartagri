import type { Config } from "tailwindcss";

/** Les couleurs pointent vers les jetons CSS (app/globals.css) : le thème sombre ne demande aucune classe dark:. */
const token = (name: string) => `var(--${name})`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        /* Verre : card et surface sont les versions translucides ; les hex --card/--surface servent au contrôle de contraste. */
        card: token("glass"),
        surface: token("surface-glass"),
        "glass-edge": token("glass-edge"),
        accent: token("accent"),
        /* Teintes translucides : Tailwind ne sait pas appliquer /20 à une var(), d'où ces jetons nommés. */
        "accent-soft": "color-mix(in srgb, var(--accent) 22%, transparent)",
        "ink-soft": "color-mix(in srgb, var(--ink) 16%, transparent)",
        gold: token("gold"),
        ink: token("ink"),
        mute: token("mute"),
        line: token("line"),
        g: token("g"),
        g2: token("g2"),
        "on-g": token("on-g"),
        blue: token("blue"),
        ok: { ink: token("ok-ink"), bg: token("ok-bg") },
        warn: { ink: token("warn-ink"), bg: token("warn-bg") },
        bad: { ink: token("bad-ink"), bg: token("bad-bg") },
      },
      borderRadius: {
        card: "22px",
        btn: "14px",
      },
      boxShadow: { card: token("shadow-card"), pop: token("shadow-pop") },
      fontFamily: {
        sans: ["var(--font-inter)", "var(--font-inter-ext)", "system-ui", "sans-serif"],
      },
      /* Les keyframes (rise, sweep, drift, breathe) vivent dans app/globals.css. */
      animation: { rise: "rise 520ms cubic-bezier(0.2, 0.7, 0.2, 1) both" },
      minHeight: { touch: "44px" },
      minWidth: { touch: "44px" },
    },
  },
  plugins: [],
};

export default config;
