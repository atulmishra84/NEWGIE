export class RecommendationClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async generate(bundle: unknown, persist = true): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/recommendations`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle, persist }),
    });
    if (!res.ok) throw new Error(`recommendations generate failed: ${res.status}`);
    return res.json();
  }

  async get(agentId: string): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/recommendations/${encodeURIComponent(agentId)}`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error(`recommendations get failed: ${res.status}`);
    return res.json();
  }

  async history(agentId?: string): Promise<unknown> {
    const q = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
    const res = await fetch(`${this.baseUrl}/v1/recommendations/history${q}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`recommendations history failed: ${res.status}`);
    return res.json();
  }

  async approve(payload: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/recommendations/approve`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`recommendations approve failed: ${res.status}`);
    return res.json();
  }
}
