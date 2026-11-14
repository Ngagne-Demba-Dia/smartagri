"use client";

import { useLocale, useTranslations } from "next-intl";
import { useId, useState, type FormEvent } from "react";

import { useErrorMessage } from "@/components/QueryState";
import type { Locale } from "@/i18n/routing";
import { api } from "@/lib/client";
import { safeNext } from "@/lib/nav";

const USERNAME_MIN = 3;

/**
 * Connexion (téléphone ou e-mail + mot de passe) via le BFF : les jetons restent dans des cookies httpOnly
 * posés par /api/auth/login ; le navigateur ne les voit jamais.
 */
export function LoginForm({ next }: { next: string | null }) {
  const t = useTranslations("login");
  const locale = useLocale() as Locale;
  const errorMessage = useErrorMessage();
  const userId = useId();
  const passId = useId();
  const errorId = useId();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const rawUser = (username || String(form.get("username") ?? "")).trim();
    const rawPass = password || String(form.get("password") ?? "");
    if (rawUser.length < USERNAME_MIN || rawPass.length === 0) {
      setError(t("missing"));
      return;
    }
    setPending(true);
    setError(null);
    try {
      await api.post("/auth/login", { username: rawUser, password: rawPass });
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
      return;
    }
    // Rechargement complet : le middleware relit les cookies et la CSP repart d'un nonce neuf.
    window.location.assign(safeNext(next, locale));
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      className="card flex w-full max-w-sm flex-col gap-4"
      aria-describedby={error ? errorId : undefined}
    >
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p className="text-mute">{t("intro")}</p>
      <div className="flex flex-col gap-1">
        <label htmlFor={userId} className="font-semibold">
          {t("username")}
        </label>
        <input
          id={userId}
          name="username"
          className="field-input min-h-touch"
          autoComplete="username"
          inputMode="email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          aria-invalid={error !== null}
          required
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor={passId} className="font-semibold">
          {t("password")}
        </label>
        <input
          id={passId}
          name="password"
          type="password"
          className="field-input min-h-touch"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={error !== null}
          required
        />
      </div>
      {error ? (
        <p id={errorId} role="alert" className="rounded-btn bg-bad-bg p-3 font-semibold text-bad-ink">
          {error}
        </p>
      ) : null}
      <button type="submit" className="btn-primary min-h-touch" disabled={pending}>
        {pending ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}
