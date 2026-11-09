"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useId, useRef, useState, type ChangeEvent } from "react";

import { FieldPicker } from "@/components/FieldPicker";
import { ModuleShell } from "@/components/ModuleShell";
import { ProvenanceNote } from "@/components/Provenance";
import { QueryState, useErrorMessage } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import type { Diagnosis } from "@/lib/contracts/assistant";
import { VISION_ABSTAIN_BELOW } from "@/lib/contracts/provenance";
import { bytesToBase64 } from "@/lib/base64";
import { ACCEPTED_IMAGE_TYPES, checkImageFile, diagnosisVerdict, VERDICT_TONE } from "@/lib/diagnosis";
import { formatDateTime, formatPct } from "@/lib/format";
import { probabilityView } from "@/lib/pests";
import { useAllFields } from "@/hooks/places";
import { useDiagnosis } from "@/services/ai/disease-diagnosis";

import { prepareImage } from "./prepareImage";

const PERCENT = 100;
type FileError = "type" | "size" | "empty" | "unreadable" | "tooLarge";
interface Prepared {
  blob: Blob;
  url: string;
}

function Hypotheses({ diagnosis, uncertain }: { diagnosis: Diagnosis; uncertain: boolean }) {
  const t = useTranslations("diagnosis");
  const calibrated = diagnosis.provenance.confidence.calibrated;
  if (diagnosis.top3.length === 0) return null;
  return (
    <div className="card">
      <h2 className="text-sm text-mute">{uncertain ? t("top3Title.uncertain") : t("top3Title.certain")}</h2>
      <ul className="flex flex-col gap-1">
        {diagnosis.top3.map((entry) => {
          const view = probabilityView(entry.probability, calibrated);
          const text =
            view.type === "percent"
              ? formatPct(view.value)
              : view.type === "uncalibrated"
                ? t("pUncalibrated")
                : "—";
          return (
            <li key={entry.code} className="flex flex-wrap justify-between gap-2">
              <span>{t.has(`names.${entry.code}`) ? t(`names.${entry.code}`) : entry.code}</span>
              <span className="font-semibold">{text}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Result({ diagnosis }: { diagnosis: Diagnosis }) {
  const t = useTranslations("diagnosis");
  const verdict = diagnosisVerdict(diagnosis);
  const code = diagnosis.disease_code;
  return (
    <div className="flex flex-col gap-3">
      <div role="status" className="card flex flex-col gap-2">
        <StatusTag tone={VERDICT_TONE[verdict]} label={t(`verdict.${verdict}`)} />
        {verdict === "sick" && code ? (
          <p className="text-2xl font-bold">{t.has(`names.${code}`) ? t(`names.${code}`) : code}</p>
        ) : null}
        <p>{t(`advice.${verdict}`, { threshold: formatPct(VISION_ABSTAIN_BELOW * PERCENT) })}</p>
        <p className="text-xs text-mute">
          {t("capturedAt", { date: formatDateTime(diagnosis.captured_at) })}
        </p>
      </div>
      <Hypotheses diagnosis={diagnosis} uncertain={verdict === "uncertain"} />
      <ProvenanceNote provenance={diagnosis.provenance} />
    </div>
  );
}

function Analyzer({ fieldId }: { fieldId: string }) {
  const t = useTranslations("diagnosis");
  const errorMessage = useErrorMessage();
  const diagnosis = useDiagnosis();
  const inputId = useId();
  const sequence = useRef(0);
  const [prepared, setPrepared] = useState<Prepared | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [fileError, setFileError] = useState<FileError | null>(null);
  const { reset } = diagnosis;

  // L'aperçu est un objet navigateur : on le libère quand la photo change et à la fermeture de l'écran.
  useEffect(() => () => void (prepared && URL.revokeObjectURL(prepared.url)), [prepared]);
  // Un résultat vaut pour une photo et une parcelle : il disparaît si l'une des deux change.
  useEffect(() => reset(), [fieldId, reset]);

  const choose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const ticket = ++sequence.current;
    reset();
    setPrepared(null);
    const check = checkImageFile(file);
    if (check !== "ok") return setFileError(check);
    setFileError(null);
    setPreparing(true);
    try {
      const blob = await prepareImage(file);
      if (ticket !== sequence.current) return;
      if (blob) setPrepared({ blob, url: URL.createObjectURL(blob) });
      else setFileError("tooLarge");
    } catch {
      if (ticket === sequence.current) setFileError("unreadable");
    } finally {
      if (ticket === sequence.current) setPreparing(false);
    }
  };

  const analyze = async () => {
    if (!prepared) return;
    const bytes = new Uint8Array(await prepared.blob.arrayBuffer());
    diagnosis.mutate({
      image_base64: bytesToBase64(bytes),
      content_type: "image/jpeg",
      field_id: fieldId,
      device_id: null,
      captured_at: new Date().toISOString(),
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor={inputId} className="font-semibold">
          {t("photoLabel")}
        </label>
        <input
          id={inputId}
          type="file"
          accept={ACCEPTED_IMAGE_TYPES.join(",")}
          className="field-input py-2"
          onChange={(event) => void choose(event)}
          aria-describedby={`${inputId}-hint`}
        />
        <p id={`${inputId}-hint`} className="text-xs text-mute">
          {t("photoHint")}
        </p>
      </div>
      <p role="status" className="text-sm text-mute">
        {preparing ? t("preparing") : null}
      </p>
      {fileError ? (
        <p role="alert" className="text-sm font-semibold text-bad-ink">
          {t(`fileError.${fileError}`)}
        </p>
      ) : null}
      {prepared ? (
        <>
          {/* Aperçu d'un objet navigateur (blob:) : next/image ne s'applique pas. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={prepared.url}
            alt={t("previewAlt")}
            className="max-h-72 self-start rounded-btn border border-line"
          />
          <button
            type="button"
            className="btn-primary self-start"
            onClick={() => void analyze()}
            disabled={diagnosis.isPending}
          >
            {diagnosis.isPending ? t("analyzing") : t("analyze")}
          </button>
        </>
      ) : null}
      {diagnosis.isError ? (
        <p role="alert" className="rounded-btn bg-bad-bg p-3 text-sm font-semibold text-bad-ink">
          {errorMessage(diagnosis.error)}
        </p>
      ) : null}
      {diagnosis.data ? <Result diagnosis={diagnosis.data} /> : null}
    </div>
  );
}

/** Maladies (service 8, doc 18 §10) : photo, aperçu, analyse, verdict avec abstention et provenance. */
export function DiagnosisView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("diagnosis");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const select = useCallback((id: string) => setFieldId(id), []);

  return (
    <ModuleShell title={tm("diseases")} description={t("intro")}>
      <QueryState
        isPending={all.isPending}
        error={all.error}
        isEmpty={all.fields.length === 0}
        emptyLabel={t("noFields")}
        onRetry={all.refetch}
      >
        <FieldPicker farms={all.farms} fields={all.fields} value={fieldId} onChange={select} />
        {fieldId ? <Analyzer fieldId={fieldId} /> : null}
      </QueryState>
    </ModuleShell>
  );
}
