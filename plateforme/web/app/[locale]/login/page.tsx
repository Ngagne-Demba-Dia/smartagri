import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { Brand } from "@/components/Brand";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { Scene } from "@/components/Scene";
import { ThemeToggle } from "@/components/ThemeToggle";
import { TranslationBanner } from "@/components/TranslationBanner";
import { DemoAccounts, type DemoAccount } from "@/features/auth/DemoAccounts";
import { LoginForm } from "@/features/auth/LoginForm";
import { isMockMode } from "@/lib/mock-config";
import { firstParam, type PageSearchParams } from "@/lib/nav";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("login");
  return { title: t("pageTitle") };
}

/** Comptes de démonstration : chargés seulement en mode simulé, pour que le module de simulation reste hors du rendu réel. */
async function demoAccounts(): Promise<{ accounts: DemoAccount[]; password: string } | null> {
  if (!isMockMode()) return null;
  const { DEMO_ACCOUNTS, DEMO_PASSWORD } = await import("@/mocks/auth");
  const accounts = Object.entries(DEMO_ACCOUNTS).map(([role, account]) => ({
    role: role as DemoAccount["role"],
    username: account.username,
  }));
  return { accounts, password: DEMO_PASSWORD };
}

export default async function LoginPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  const demo = await demoAccounts();
  const t = await getTranslations("login");
  const tc = await getTranslations("common");
  return (
    <div data-scene="login" className="relative isolate min-h-screen">
      <Scene />
      <main
        id="contenu"
        className="mx-auto grid min-h-screen w-full max-w-6xl content-center gap-8 p-4 sm:p-6 lg:grid-cols-[1.1fr_minmax(0,24rem)] lg:items-center lg:gap-14"
      >
        <section className="reveal flex flex-col gap-5 text-white">
          <Brand name={tc("appName")} tone="light" />
          <h2 className="max-w-xl text-3xl font-bold leading-tight tracking-tight sm:text-5xl">
            {t("heroTitle")}
          </h2>
          <p className="max-w-lg text-base text-white sm:text-lg">{t("heroSubtitle")}</p>
        </section>
        <div className="reveal flex flex-col items-center gap-4 [animation-delay:120ms]">
          <div className="glass flex w-full max-w-sm items-center justify-end gap-2 !rounded-full px-3 py-1.5">
            <ThemeToggle />
            <LocaleSwitcher />
          </div>
          <TranslationBanner />
          <LoginForm next={firstParam(sp.next)} />
          {demo ? <DemoAccounts accounts={demo.accounts} password={demo.password} /> : null}
        </div>
      </main>
    </div>
  );
}
