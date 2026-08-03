export class PolicyGeneratorClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async generate(bundle: unknown, persist = true): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/policy/generate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle, persist }),
    });
    if (!res.ok) throw new Error(`policy generate failed: ${res.status}`);
    return res.json();
  }

  async validate(payload: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/policy/validate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`policy validate failed: ${res.status}`);
    return res.json();
  }

  async templates(): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/policy/templates`, { headers: this.headers() });
    if (!res.ok) throw new Error(`policy templates failed: ${res.status}`);
    return res.json();
  }

  async get(policyId: string): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/policy/${encodeURIComponent(policyId)}`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error(`policy get failed: ${res.status}`);
    return res.json();
  }
}
