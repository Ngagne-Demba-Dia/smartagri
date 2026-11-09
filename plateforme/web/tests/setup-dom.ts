/**
 * Préparation des tests de composants (fichiers `.test.tsx`, environnement jsdom déclaré par
 * `// @vitest-environment jsdom`). Sans effet dans les tests de calcul, qui restent sous Node.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  if (typeof document !== "undefined") cleanup();
});
