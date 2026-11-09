"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { usePathname, useRouter } from "next/navigation";
import { useId, useMemo, useState } from "react";

import { ModuleShell } from "@/components/ModuleShell";
import { ProvenanceNote } from "@/components/Provenance";
import { ErrorNotice, QueryState } from "@/components/QueryState";
import { RampStepSwatch } from "@/components/RampSwatch";
import { useFarmMapLayers, useFarmMaps, type FarmMapEntry } from "@/services/ai/map-layers";
import { MAP_LAYERS, type MapLayer, type MapLayersView } from "@/lib/contracts/org";
import { formatNumber } from "@/lib/format";
import {
  MAP_MODES,
  farmShapes,
  isMapMode,
  layersFor,
  legendFor,
  type LegendItem,
  type MapFieldShape,
  type MapMode,
} from "@/lib/map-style";

import { FieldMapTable } from "./FieldMapTable";
import { FieldPanel } from "./FieldPanel";

function CanvasLoading() {
  const t = useTranslations("map");
  return (
    <div role="status" className="card flex h-[60vh] min-h-[320px] items-center justify-center text-mute">
      {t("canvasLoading")}
    </div>
  );
}

/** Leaflet touche à window au chargement : le fond est chargé côté client seulement. */
const FieldMapCanvas = dynamic(() => import("./FieldMapCanvas"), { ssr: false, loading: CanvasLoading });

const isMapLayer = (value: string): value is MapLayer => (MAP_LAYERS as readonly string[]).includes(value);

function MapControls({
  farms,
  farmId,
  onFarm,
  mode,
  onMode,
  showKits,
  onKits,
  showBoundaries,
  onBoundaries,
}: {
  farms: readonly FarmMapEntry[];
  farmId: string | null;
  onFarm: (farmId: string) => void;
  mode: MapMode;
  onMode: (mode: MapMode) => void;
  showKits: boolean;
  onKits: (value: boolean) => void;
  showBoundaries: boolean;
  onBoundaries: (value: boolean) => void;
}) {
  const t = useTranslations("map.controls");
  const farmSelect = useId();
  return (
    <div className="card flex flex-col gap-3 md:flex-row md:flex-wrap md:items-end md:gap-6">
      <div className="flex flex-col gap-1">
        <label htmlFor={farmSelect} className="text-sm font-semibold">
          {t("farm")}
        </label>
        <select
          id={farmSelect}
          className="field-input"
          value={farmId ?? ""}
          onChange={(e) => onFarm(e.target.value)}
        >
          {farms.map((f) => (
            <option key={f.farmId} value={f.farmId}>
              {f.farmName}
            </option>
          ))}
        </select>
      </div>
      <fieldset className="flex flex-col gap-1">
        <legend className="text-sm font-semibold">{t("mode")}</legend>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {MAP_MODES.map((m) => (
            <label key={m} className="flex min-h-touch items-center gap-2">
              <input
                type="radio"
                name="map-mode"
                value={m}
                checked={mode === m}
                onChange={(e) => isMapMode(e.target.value) && onMode(e.target.value)}
              />
              {t(`modes.${m}`)}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="flex flex-col gap-1">
        <legend className="text-sm font-semibold">{t("show")}</legend>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <label className="flex min-h-touch items-center gap-2">
            <input type="checkbox" checked={showKits} onChange={(e) => onKits(e.target.checked)} />
            {t("kits")}
          </label>
          <label className="flex min-h-touch items-center gap-2">
            <input
              type="checkbox"
              checked={showBoundaries}
              onChange={(e) => onBoundaries(e.target.checked)}
            />
            {t("boundaries")}
          </label>
        </div>
      </fieldset>
    </div>
  );
}

function legendLabel(
  t: ReturnType<typeof useTranslations<"map.legend">>,
  mode: MapMode,
  item: LegendItem,
): string {
  if (item.kind === "noData") return t("noData");
  if (item.kind === "salinity") return t(`salinity.${item.value}`);
  const digits = mode === "ndvi" ? 1 : 0;
  const unit = mode === "moisture" ? " %" : "";
  const from = item.from === null ? null : `${formatNumber(item.from, digits)}${unit}`;
  const to = item.to === null ? null : `${formatNumber(item.to, digits)}${unit}`;
  if (from === null) return t("below", { to: to ?? "" });
  if (to === null) return t("above", { from });
  return t("range", { from, to });
}

/** Légende du mode courant ; en mode culture, pas d'échelle : chaque parcelle porte son étiquette. */
function MapLegend({ mode }: { mode: MapMode }) {
  const t = useTranslations("map.legend");
  const items = legendFor(mode);
  return (
    <section className="card flex flex-col gap-2" aria-labelledby="map-legend-title">
      <h2 id="map-legend-title" className="font-semibold">
        {t(`title.${mode}`)}
      </h2>
      {items.length === 0 ? (
        <p className="text-sm text-mute">{t("cropNote")}</p>
      ) : (
        <ul className="flex flex-wrap gap-3 text-sm">
          {items.map((item) => (
            <li key={item.step} className="flex items-center gap-2">
              <RampStepSwatch step={item.step} />
              {legendLabel(t, mode, item)}
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-mute">{t("kitsNote")}</p>
    </section>
  );
}

/** Choix de la parcelle au clavier : équivalent du clic sur la carte. */
function FieldSelect({
  fields,
  value,
  onChange,
}: {
  fields: readonly MapFieldShape[];
  value: string | null;
  onChange: (id: string) => void;
}) {
  const t = useTranslations("map");
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">
        {t("fieldSelect")}
      </label>
      <select id={id} className="field-input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
        {fields.map((f) => (
          <option key={f.props.field_id} value={f.props.field_id}>
            {f.props.name}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Provenance de la carte : bloc d'ensemble, puis une note par couche reçue (doc 16 §9.2). */
function MapSources({ base, overlay }: { base: MapLayersView; overlay: MapLayersView | null }) {
  const t = useTranslations("map.sources");
  const layers = Object.entries(overlay?.layers ?? {}).filter(([key]) => isMapLayer(key));
  return (
    <section aria-labelledby="map-sources-title" className="flex flex-col gap-2">
      <h2 id="map-sources-title" className="text-base font-semibold">
        {t("title")}
      </h2>
      <p className="text-sm text-mute">{t("base")}</p>
      <ProvenanceNote provenance={overlay?.provenance ?? base.provenance} />
      {layers.map(([key, provenance]) => (
        <div key={key} className="flex flex-col gap-1">
          <p className="text-sm text-mute">{t(`layer.${key}`)}</p>
          <ProvenanceNote provenance={provenance} unit="" />
        </div>
      ))}
    </section>
  );
}

/**
 * Carte (module 4, service 18 map_layers) : fond Leaflet sans tuiles, une exploitation à la fois (elles sont
 * éloignées de près de 100 km), coloration par humidité, NDVI, culture détectée ou salinité, kits et contours.
 * La carte de base (route existante) reste affichée si la couche demandée (route proposée) échoue.
 */
export function FieldMap({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("map");
  const tm = useTranslations("modules");
  const router = useRouter();
  const pathname = usePathname();
  const base = useFarmMaps();
  const [farmChoice, setFarmChoice] = useState<string | null>(null);
  const [fieldChoice, setFieldChoice] = useState<string | null>(initialFieldId);
  const [mode, setMode] = useState<MapMode>("moisture");
  const [showKits, setShowKits] = useState(true);
  const [showBoundaries, setShowBoundaries] = useState(false);

  const farmOfField = useMemo(
    () =>
      new Map(
        base.maps.flatMap((m) =>
          m.map.features.flatMap((f) =>
            f.properties.kind === "field" ? [[f.properties.field_id, m.farmId] as const] : [],
          ),
        ),
      ),
    [base.maps],
  );
  const farmId =
    farmChoice ?? (fieldChoice ? farmOfField.get(fieldChoice) : undefined) ?? base.maps[0]?.farmId ?? null;
  const entry = base.maps.find((m) => m.farmId === farmId) ?? null;
  const layers = useMemo(() => layersFor(mode, showBoundaries), [mode, showBoundaries]);
  const overlay = useFarmMapLayers(entry ? farmId : null, layers);
  const overlayData = layers.length > 0 ? (overlay.data ?? null) : null;
  const shapes = useMemo(() => (entry ? farmShapes(entry.map, overlayData) : null), [entry, overlayData]);
  const selected = shapes?.fields.find((f) => f.props.field_id === fieldChoice) ?? shapes?.fields[0] ?? null;

  const selectField = (fieldId: string) => {
    setFieldChoice(fieldId);
    router.replace(`${pathname}?parcelle=${encodeURIComponent(fieldId)}`, { scroll: false });
  };
  const selectFarm = (id: string) => {
    setFarmChoice(id);
    setFieldChoice(null);
    router.replace(pathname, { scroll: false });
  };

  return (
    <ModuleShell title={tm("map")} description={t("description")}>
      <p className="text-sm text-mute">{t("intro")}</p>
      <QueryState
        isPending={base.isPending}
        error={base.error}
        isEmpty={farmOfField.size === 0}
        emptyLabel={t("empty")}
        onRetry={base.refetch}
      >
        <MapControls
          farms={base.maps}
          farmId={farmId}
          onFarm={selectFarm}
          mode={mode}
          onMode={setMode}
          showKits={showKits}
          onKits={setShowKits}
          showBoundaries={showBoundaries}
          onBoundaries={setShowBoundaries}
        />
        {entry && shapes ? (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <div className="flex flex-col gap-3">
              <figure className="flex flex-col gap-2">
                <figcaption className="sr-only">{t("canvasLabel", { farm: entry.farmName })}</figcaption>
                <FieldMapCanvas
                  shapes={shapes}
                  mode={mode}
                  showKits={showKits}
                  showBoundaries={showBoundaries}
                  selectedId={selected?.props.field_id ?? null}
                  onSelect={selectField}
                />
              </figure>
              {layers.length > 0 && overlay.isLoading ? (
                <p role="status" className="text-sm text-mute">
                  {t("layerLoading")}
                </p>
              ) : null}
              {layers.length > 0 && overlay.error ? (
                <ErrorNotice error={overlay.error} onRetry={() => void overlay.refetch()} />
              ) : null}
              <MapLegend mode={mode} />
            </div>
            <div className="flex flex-col gap-3">
              <FieldSelect
                fields={shapes.fields}
                value={selected?.props.field_id ?? null}
                onChange={selectField}
              />
              {selected ? <FieldPanel field={selected} farmName={entry.farmName} /> : null}
            </div>
          </div>
        ) : null}
        {entry ? <MapSources base={entry.map} overlay={overlayData} /> : null}
        <section aria-labelledby="map-tables-title" className="flex flex-col gap-2">
          <h2 id="map-tables-title" className="text-base font-semibold">
            {t("tablesTitle")}
          </h2>
          <FieldMapTable entries={base.maps} />
        </section>
      </QueryState>
    </ModuleShell>
  );
}
