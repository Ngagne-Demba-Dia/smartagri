/**
 * Rendu de composants avec les vrais messages français (next-intl) : les tests lisent ce que lit l'utilisateur.
 */
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";

import messages from "@/messages/fr.json";
import type { Provenance } from "@/lib/contracts/provenance";

export function renderFr(ui: ReactElement) {
  return render(
    <NextIntlClientProvider locale="fr" messages={messages} timeZone="Africa/Dakar">
      {ui}
    </NextIntlClientProvider>,
  );
}

export function makeProvenance(overrides: Partial<Provenance> = {}): Provenance {
  return {
    model_name: "irr_need_24h",
    model_version: "3",
    source: "agriml",
    fallback_step: 0,
    computed_at: "2027-03-02T06:00:00Z",
    data_as_of: "2027-03-02T05:00:00Z",
    stale: false,
    confidence: { kind: "interval", value: null, p10: 4.1, p90: 7.9, calibrated: true },
    ...overrides,
  };
}
