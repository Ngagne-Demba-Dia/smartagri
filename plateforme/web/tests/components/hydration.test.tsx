// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SyncBanner } from "@/components/SyncBanner";
import { VoiceInput } from "@/features/assistant/VoiceInput";
import messages from "@/messages/fr.json";

import { renderFr } from "./render";

vi.mock("@/services/ai/assistant-transcribe", () => ({
  useTranscribe: () => ({ mutate: vi.fn(), reset: vi.fn(), isPending: false, error: null }),
}));

const wrap = (ui: React.ReactElement) => (
  <QueryClientProvider client={new QueryClient()}>
    <NextIntlClientProvider locale="fr" messages={messages} timeZone="Africa/Dakar">
      {ui}
    </NextIntlClientProvider>
  </QueryClientProvider>
);

describe("hydratation", () => {
  it("la saisie vocale ne rend rien côté serveur : pas de différence avec le navigateur", () => {
    expect(renderToString(wrap(<VoiceInput onText={vi.fn()} />))).toBe("");
  });

  it("la saisie vocale dit que la dictée est indisponible quand le navigateur ne sait pas enregistrer", () => {
    renderFr(
      <QueryClientProvider client={new QueryClient()}>
        <VoiceInput onText={vi.fn()} />
      </QueryClientProvider>,
    );
    expect(screen.getByText("La dictée n’est pas disponible sur cet appareil.")).toBeInTheDocument();
  });

  it("le bandeau de synchronisation ne rend rien côté serveur", () => {
    expect(renderToString(wrap(<SyncBanner />))).toBe("");
  });

  it("le bandeau reste à jour sans mise à jour pendant le rendu d'un autre composant", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const client = new QueryClient();
    renderFr(
      <QueryClientProvider client={client}>
        <SyncBanner />
      </QueryClientProvider>,
    );
    await act(async () => {
      await client.fetchQuery({ queryKey: ["x"], queryFn: () => Promise.resolve(1) });
    });
    expect(screen.getByRole("status")).toHaveTextContent(/données reçues/);
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });
});
