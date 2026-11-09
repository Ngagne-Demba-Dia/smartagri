"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useId, useState } from "react";
import { z } from "zod";

import { DataTable, type Column } from "@/components/DataTable";
import { Icon } from "@/components/Icon";
import { ErrorNotice, QueryState } from "@/components/QueryState";
import { ApiError } from "@/lib/api";
import { api } from "@/lib/client";
import { SERVICES, SERVICE_IDS, type ServiceDef, type ServiceId } from "@/lib/contracts/registry";
import { formatNumber } from "@/lib/format";
import { MOCK_SCENARIOS, type MockScenario } from "@/lib/mock-config";

/**
 * Bandeau du mode simulé (doc 16 §9.5) et panneau de pilotage des simulations : scénario global, surcharge
 * par service, remise à zéro. Rendu seulement quand le serveur est en mode simulé (AGRI_MOCK=1) : la route
 * /api/dev/mock répond 404 sinon. Le panneau n'importe rien de mocks/ : il lit la table des services
 * et la liste des scénarios, et valide la réponse de la route.
 */
const DEV_MOCK_KEY = ["dev-mock"] as const;
const DEV_MOCK_PATH = "/dev/mock";
/** Valeur du sélecteur « suit le scénario global » (pas de surcharge). */
const INHERIT = "";

const ScenarioSchema = z.enum(MOCK_SCENARIOS);
const DevMockSchema = z.object({
  global: ScenarioSchema,
  overrides: z.partialRecord(z.enum(SERVICE_IDS), ScenarioSchema),
  latencyFactor: z.number().nonnegative(),
});
type DevMockState = z.infer<typeof DevMockSchema>;

interface ScenarioChange {
  scenario: MockScenario | null;
  service?: ServiceId;
}

const isScenario = (value: string): value is MockScenario =>
  (MOCK_SCENARIOS as readonly string[]).includes(value);

function parseState(data: unknown): DevMockState {
  const parsed = DevMockSchema.safeParse(data);
  if (!parsed.success) throw new ApiError("BAD_RESPONSE", "Réponse inattendue du serveur.", 200);
  return parsed.data;
}

function useDevMock() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: DEV_MOCK_KEY,
    queryFn: async ({ signal }) =>
      parseState((await api.get<unknown>(DEV_MOCK_PATH, undefined, signal)).data),
    staleTime: 0,
  });
  /** Nouvel état du pilotage, puis toutes les autres données rechargées sous le nouveau scénario. */
  const applied = (state: DevMockState) => {
    queryClient.setQueryData(DEV_MOCK_KEY, state);
    void queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== DEV_MOCK_KEY[0] });
  };
  const change = useMutation({
    mutationFn: async (body: ScenarioChange) =>
      parseState((await api.post<unknown>(DEV_MOCK_PATH, body)).data),
    onSuccess: applied,
  });
  const reset = useMutation({
    mutationFn: async () =>
      parseState((await api.request<unknown>(DEV_MOCK_PATH, { method: "DELETE" })).data),
    onSuccess: applied,
  });
  return { query, change, reset };
}

interface ServiceRow {
  service: ServiceDef;
  override: MockScenario | undefined;
}

function ServiceScenarioSelect({
  row,
  global,
  disabled,
  onChange,
}: {
  row: ServiceRow;
  global: MockScenario;
  disabled: boolean;
  onChange: (change: ScenarioChange) => void;
}) {
  const t = useTranslations("devMock");
  const id = row.service.id;
  return (
    <select
      className="field-input"
      aria-label={t("serviceSelect", { service: id })}
      value={row.override ?? INHERIT}
      disabled={disabled}
      onChange={(e) => {
        const value = e.target.value;
        if (value === INHERIT) onChange({ scenario: null, service: id });
        else if (isScenario(value)) onChange({ scenario: value, service: id });
      }}
    >
      <option value={INHERIT}>{t("inherit", { scenario: t(`scenario.${global}`) })}</option>
      {MOCK_SCENARIOS.map((s) => (
        <option key={s} value={s}>
          {t(`scenario.${s}`)}
        </option>
      ))}
    </select>
  );
}

function ServicesTable({
  state,
  disabled,
  onChange,
}: {
  state: DevMockState;
  disabled: boolean;
  onChange: (change: ScenarioChange) => void;
}) {
  const t = useTranslations("devMock");
  const rows: ServiceRow[] = SERVICES.map((service) => ({ service, override: state.overrides[service.id] }));
  const columns: Column<ServiceRow>[] = [
    { key: "number", header: t("columns.number"), numeric: true, cell: (r) => `#${r.service.number}` },
    { key: "service", header: t("columns.service"), cell: (r) => <code>{r.service.id}</code> },
    {
      key: "latency",
      header: t("columns.latency"),
      numeric: true,
      cell: (r) => t("latencyValue", { value: formatNumber(r.service.mockLatencyMs * state.latencyFactor) }),
    },
    {
      key: "scenario",
      header: t("columns.scenario"),
      cell: (r) => (
        <ServiceScenarioSelect row={r} global={state.global} disabled={disabled} onChange={onChange} />
      ),
    },
  ];
  return (
    <DataTable caption={t("servicesTitle")} columns={columns} rows={rows} rowKey={(r) => r.service.id} />
  );
}

/** Panneau de pilotage : visible sur demande depuis le bandeau. */
export function DevMockPanel() {
  const t = useTranslations("devMock");
  const titleId = useId();
  const globalSelect = useId();
  const { query, change, reset } = useDevMock();
  const busy = change.isPending || reset.isPending;
  const failure = change.error ?? reset.error;
  const state = query.data;

  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-3 border-b border-line bg-bg px-4 py-3">
      <h2 id={titleId} className="text-base font-semibold">
        {t("panelTitle")}
      </h2>
      <p className="text-sm text-mute">{t("panelIntro")}</p>
      <QueryState isPending={query.isPending} error={query.error} onRetry={() => void query.refetch()}>
        {state ? (
          <>
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:gap-6">
              <div className="flex flex-col gap-1">
                <label htmlFor={globalSelect} className="text-sm font-semibold">
                  {t("global")}
                </label>
                <select
                  id={globalSelect}
                  className="field-input"
                  value={state.global}
                  disabled={busy}
                  onChange={(e) => isScenario(e.target.value) && change.mutate({ scenario: e.target.value })}
                >
                  {MOCK_SCENARIOS.map((s) => (
                    <option key={s} value={s}>
                      {t(`scenario.${s}`)}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                className="btn-secondary self-start md:self-end"
                disabled={busy}
                onClick={() => reset.mutate()}
              >
                {t("reset")}
              </button>
            </div>
            <p className="text-sm text-mute">{t("resetNote")}</p>
            <p className="text-sm text-mute">
              {t("latencyNote", { factor: formatNumber(state.latencyFactor, 1) })}
            </p>
            {busy ? (
              <p role="status" className="text-sm text-mute">
                {t("applying")}
              </p>
            ) : null}
            {failure ? <ErrorNotice error={failure} /> : null}
            <ServicesTable state={state} disabled={busy} onChange={(c) => change.mutate(c)} />
          </>
        ) : null}
      </QueryState>
    </section>
  );
}

/** Bandeau permanent du mode simulé : aucune donnée réelle n'est affichée. */
export function MockBanner() {
  const t = useTranslations("devMock");
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 bg-warn-bg px-4 py-1.5 text-sm text-warn-ink">
        <Icon name="warn" size={16} />
        <p className="font-semibold">{t("banner")}</p>
        <button
          type="button"
          className="ml-auto min-h-touch underline"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? t("hide") : t("show")}
        </button>
      </div>
      <div id={panelId}>{open ? <DevMockPanel /> : null}</div>
    </div>
  );
}
