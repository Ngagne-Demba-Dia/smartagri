import { NextIntlClientProvider } from "next-intl";
import { getMessages, getNow, getTimeZone } from "next-intl/server";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { Providers } from "@/components/Providers";
import { isLocale } from "@/i18n/routing";

/**
 * Layout d'une langue : messages (le français complète wo et ff), fuseau Africa/Dakar et horloge de la requête
 * transmis aux composants clients, puis le cache des requêtes (TanStack Query).
 */
export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const [messages, timeZone, now] = await Promise.all([getMessages(), getTimeZone(), getNow()]);
  return (
    <NextIntlClientProvider locale={locale} messages={messages} timeZone={timeZone} now={now}>
      <Providers>{children}</Providers>
    </NextIntlClientProvider>
  );
}
