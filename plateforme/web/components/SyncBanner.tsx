"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState, useSyncExternalStore } from "react";

import { formatClock } from "@/lib/format";

import { Icon } from "./Icon";
import { useAgoLabel } from "./TimeAgo";

const TICK_MS = 30_000;

function subscribeOnline(callback: () => void): () => void {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

/** Côté serveur on suppose « en ligne » : le bandeau hors ligne n'apparaît qu'après hydratation. */
function useOnline(): boolean {
  return useSyncExternalStore(
    subscribeOnline,
    () => navigator.onLine,
    () => true,
  );
}

/** Horodatage de la donnée la plus récente parmi toutes les requêtes en cache (0 : rien de chargé). */
function useNewestDataAt(): number {
  const queryClient = useQueryClient();
  const [newest, setNewest] = useState(0);
  useEffect(() => {
    const cache = queryClient.getQueryCache();
    let active = true;
    const update = () => setNewest(Math.max(0, ...cache.getAll().map((q) => q.state.dataUpdatedAt)));
    // Le cache notifie parfois pendant le rendu d'un autre composant (création d'une requête) :
    // la mise à jour est reportée après le rendu pour ne pas déclencher l'avertissement de React.
    const compute = () =>
      queueMicrotask(() => {
        if (active) update();
      });
    update();
    const unsubscribe = cache.subscribe(compute);
    return () => {
      active = false;
      unsubscribe();
    };
  }, [queryClient]);
  return newest;
}

/**
 * Bandeau d'état de synchronisation (doc 10 §6) : « Données à jour il y a 3 min » en ligne,
 * « Hors ligne · données de 9 h 12 » sans réseau. Rafraîchi toutes les 30 s.
 */
export function SyncBanner() {
  const t = useTranslations("sync");
  const ago = useAgoLabel();
  const online = useOnline();
  const newest = useNewestDataAt();
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const timer = window.setInterval(() => setNow(new Date()), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  // Rien avant hydratation : l'heure locale du serveur ne doit pas être comparée à celle du navigateur.
  if (!now) return null;

  const at = newest > 0 ? new Date(newest).toISOString() : null;
  let text: string;
  if (!online) text = at ? t("offline", { clock: formatClock(at) }) : t("offlineNoData");
  else text = at ? t("online", { age: ago(at, now) }) : t("waiting");

  return (
    <p
      role="status"
      className={`flex items-center gap-2 px-4 py-1.5 text-sm ${online ? "text-mute" : "bg-warn-bg font-semibold text-warn-ink"}`}
    >
      <Icon name={online ? "clock" : "offline"} size={16} />
      {text}
    </p>
  );
}
