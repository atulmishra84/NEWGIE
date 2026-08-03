export class ComplianceClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async analyze(bundle: unknown, persist = true): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/compliance/analyze`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle, persist }),
    });
    if (!res.ok) throw new Error(`compliance analyze failed: ${res.status}`);
    return res.json();
  }

  async validate(payload: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/compliance/validate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`compliance validate failed: ${res.status}`);
    return res.json();
  }

  async report(applicationId: string): Promise<unknown> {
    const res = await fetch(
      `${this.baseUrl}/v1/compliance/report?application_id=${encodeURIComponent(applicationId)}`,
      { headers: this.headers() },
    );
    if (!res.ok) throw new Error(`compliance report failed: ${res.status}`);
    return res.json();
  }

  async frameworks(): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/frameworks`, { headers: this.headers() });
    if (!res.ok) throw new Error(`frameworks failed: ${res.status}`);
    return res.json();
  }
}
