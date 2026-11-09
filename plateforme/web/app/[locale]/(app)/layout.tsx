import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { MockBanner } from "@/features/dev/MockBanner";
import { isMockMode } from "@/lib/mock-config";

/** Écrans authentifiés : en-tête, navigation et barre du bas. En mode simulé, un bandeau le signale en permanence. */
export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell banner={isMockMode() ? <MockBanner /> : null}>{children}</AppShell>;
}
