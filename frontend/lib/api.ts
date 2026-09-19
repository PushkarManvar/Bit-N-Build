type HealthResult = {
  ok: boolean;
  label: string;
};

export async function getHealth(): Promise<HealthResult> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${baseUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1_500),
    });
    if (!response.ok) {
      return { ok: false, label: `unavailable (${response.status})` };
    }
    return { ok: true, label: "connected" };
  } catch {
    return { ok: false, label: "waiting for API" };
  }
}
