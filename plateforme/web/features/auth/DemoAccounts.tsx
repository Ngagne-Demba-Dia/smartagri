import { useTranslations } from "next-intl";

import type { Role } from "@/lib/types";

export interface DemoAccount {
  role: Role;
  username: string;
}

/**
 * Comptes de démonstration du mode simulé (AGRI_MOCK=1) : un par rôle, aucun nom de personne.
 * Rendu par la page de connexion seulement quand le serveur est en mode simulé.
 */
export function DemoAccounts({ accounts, password }: { accounts: readonly DemoAccount[]; password: string }) {
  const t = useTranslations("login.demo");
  const tc = useTranslations("common");
  return (
    <section
      aria-labelledby="demo-accounts-title"
      className="card flex w-full max-w-sm flex-col gap-2 bg-warn-bg text-warn-ink"
    >
      <h2 id="demo-accounts-title" className="font-semibold">
        {t("title")}
      </h2>
      <p className="text-sm">{t("intro", { password })}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        {accounts.map((a) => (
          <div key={a.role} className="contents">
            <dt className="font-semibold">{tc(`roles.${a.role}`)}</dt>
            <dd>
              <code>{a.username}</code>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
