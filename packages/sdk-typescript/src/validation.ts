export class ValidationClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async validate(bundle: unknown, persist = true, runSimulation = true): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/validate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle, persist, run_simulation: runSimulation }),
    });
    if (!res.ok) throw new Error(`validate failed: ${res.status}`);
    return res.json();
  }

  async simulate(payload: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/simulate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`simulate failed: ${res.status}`);
    return res.json();
  }

  async get(validationId: string): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/validation/${encodeURIComponent(validationId)}`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error(`get validation failed: ${res.status}`);
    return res.json();
  }

  async report(agentId?: string): Promise<unknown> {
    const q = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
    const res = await fetch(`${this.baseUrl}/v1/validation/report${q}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`validation report failed: ${res.status}`);
    return res.json();
  }
}
