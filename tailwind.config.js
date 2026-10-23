/** Tailwind config for GhostTab AI. */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
    "./apps/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        gt: {
          bg: "var(--gt-bg)",
          "bg-elev-1": "var(--gt-bg-elev-1)",
          "bg-elev-2": "var(--gt-bg-elev-2)",
          "bg-elev-3": "var(--gt-bg-elev-3)",
          surface: "var(--gt-surface)",
          "surface-strong": "var(--gt-surface-strong)",
          border: "var(--gt-border)",
          "border-strong": "var(--gt-border-strong)",
          text: "var(--gt-text)",
          muted: "var(--gt-text-muted)",
          soft: "var(--gt-text-soft)",
          dim: "var(--gt-text-dim)",
          accent: "var(--gt-accent)",
          "accent-soft": "var(--gt-accent-soft)",
          cyan: "var(--gt-cyan)",
          "cyan-soft": "var(--gt-cyan-soft)",
          warn: "var(--gt-warn)",
          danger: "var(--gt-danger)",
          success: "var(--gt-success)",
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        gt: {
          xs: "var(--gt-r-xs)",
          sm: "var(--gt-r-sm)",
          md: "var(--gt-r-md)",
          lg: "var(--gt-r-lg)",
          xl: "var(--gt-r-xl)",
        },
      },
      boxShadow: {
        gt: {
          sm: "var(--gt-shadow-sm)",
          md: "var(--gt-shadow-md)",
          lg: "var(--gt-shadow-lg)",
          glow: "var(--gt-shadow-glow-violet)",
        },
      },
      transitionTimingFunction: {
        gt: {
          out: "var(--gt-ease-out)",
          spring: "var(--gt-ease-spring)",
        },
      },
      keyframes: {
        "fade-up": { from: { opacity: 0, transform: "translateY(16px)" }, to: { opacity: 1, transform: "translateY(0)" } },
        "scale-in": { from: { opacity: 0, transform: "scale(0.96)" }, to: { opacity: 1, transform: "scale(1)" } },
      },
      animation: {
        "fade-up": "fade-up 0.42s var(--gt-ease-out) both",
        "scale-in": "scale-in 0.22s var(--gt-ease-spring) both",
      },
    },
  },
  plugins: [],
};
