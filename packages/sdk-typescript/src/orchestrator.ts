export class OrchestratorClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async analyze(request: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/analyze`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error(`analyze failed: ${res.status}`);
    return res.json();
  }

  async status(): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/status`, { headers: this.headers() });
    if (!res.ok) throw new Error(`status failed: ${res.status}`);
    return res.json();
  }

  async execution(id: string): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/execution/${id}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`execution failed: ${res.status}`);
    return res.json();
  }

  async trace(id: string): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/trace/${id}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`trace failed: ${res.status}`);
    return res.json();
  }
}
