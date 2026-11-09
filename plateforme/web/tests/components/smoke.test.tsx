// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("outillage de test de composants", () => {
  it("rend un élément et lit son rôle accessible", () => {
    render(<button type="button">Valider</button>);
    expect(screen.getByRole("button", { name: "Valider" })).toBeInTheDocument();
  });
});
