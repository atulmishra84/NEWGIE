export class PolicyClient {
  constructor(
    private baseUrl: string,
    private opts: { token?: string; apiKey?: string } = {},
  ) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async generate(bundle: unknown, dryRun = false): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/policies/generate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bundle, dry_run: dryRun }),
    });
    if (!res.ok) throw new Error(`policy generate failed: ${res.status}`);
    return res.json();
  }
}
