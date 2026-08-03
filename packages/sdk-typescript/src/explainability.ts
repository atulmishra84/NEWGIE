export class ExplainabilityClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async explain(bundle: unknown, persist = true): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/explain`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle, persist }),
    });
    if (!res.ok) throw new Error(`explain failed: ${res.status}`);
    return res.json();
  }

  async get(explanationId: string): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/explanation/${encodeURIComponent(explanationId)}`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error(`get explanation failed: ${res.status}`);
    return res.json();
  }

  async figmaGenerateDiagram(explanationId?: string): Promise<unknown> {
    const q = explanationId ? `?explanation_id=${encodeURIComponent(explanationId)}` : "";
    const res = await fetch(`${this.baseUrl}/v1/figma-generate-diagram${q}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`figma diagram failed: ${res.status}`);
    return res.json();
  }
}
