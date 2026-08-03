export class LearningClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async feedback(event: unknown, persist = true): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/feedback`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ event, persist }),
    });
    if (!res.ok) throw new Error(`feedback failed: ${res.status}`);
    return res.json();
  }

  async learn(bundle: unknown, persist = true): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/learn`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle, persist }),
    });
    if (!res.ok) throw new Error(`learn failed: ${res.status}`);
    return res.json();
  }

  async history(agentId?: string): Promise<unknown> {
    const q = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
    const res = await fetch(`${this.baseUrl}/v1/learning/history${q}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`learning history failed: ${res.status}`);
    return res.json();
  }

  async knowledgeChanges(status?: string): Promise<unknown> {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    const res = await fetch(`${this.baseUrl}/v1/knowledge/changes${q}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`knowledge changes failed: ${res.status}`);
    return res.json();
  }
}
