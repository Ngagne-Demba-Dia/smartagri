import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** Sondes Kubernetes (infra/k8s/base/app/web.yaml) : vivacité du serveur Next.js seulement. */
export function GET() {
  return NextResponse.json({ status: "ok" });
}
