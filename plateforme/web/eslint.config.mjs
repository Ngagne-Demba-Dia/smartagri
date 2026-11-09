import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

const config = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "next-env.d.ts",
      "coverage/**",
      "test-results/**",
      "audit-shots/**",
      "playwright-report/**",
    ],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      "no-console": "error",
      // Les jetons ne vont jamais dans le stockage du navigateur (doc 10 §7).
      "no-restricted-globals": ["error", "localStorage", "sessionStorage"],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "localStorage" },
        { object: "window", property: "sessionStorage" },
      ],
      "react/no-danger": "error",
    },
  },
  // Outils de développement (rapports en console) : hors du code livré.
  { files: ["scripts/**", "e2e/**"], rules: { "no-console": "off" } },
];

export default config;
