export class RiskClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async calculate(bundle: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/risk/calculate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle }),
    });
    if (!res.ok) throw new Error(`risk calculate failed: ${res.status}`);
    return res.json();
  }
}
