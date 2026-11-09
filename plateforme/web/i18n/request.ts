import type { AbstractIntlMessages } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { headers } from "next/headers";

import { mergeMessages, type Messages } from "./merge";
import { DEFAULT_LOCALE, LOCALE_HEADER, isLocale, type Locale } from "./routing";

async function loadMessages(locale: Locale): Promise<Messages> {
  const fr = (await import("../messages/fr.json")).default as Messages;
  if (locale === "fr") return fr;
  const local = (await import(`../messages/${locale}.json`)).default as Messages;
  return mergeMessages(fr, local);
}

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = (await requestLocale) ?? (await headers()).get(LOCALE_HEADER);
  const locale: Locale = isLocale(requested) ? requested : DEFAULT_LOCALE;
  return {
    locale,
    messages: (await loadMessages(locale)) as AbstractIntlMessages,
    timeZone: "Africa/Dakar",
    now: new Date(),
  };
});
