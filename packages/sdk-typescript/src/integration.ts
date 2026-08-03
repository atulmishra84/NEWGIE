export class IntegrationClient {
  constructor(private baseUrl: string, private opts: { token?: string; apiKey?: string } = {}) {}

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.opts.token) h.Authorization = `Bearer ${this.opts.token}`;
    if (this.opts.apiKey) h["X-API-Key"] = this.opts.apiKey;
    return h;
  }

  async platforms(): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/integrations`, { headers: this.headers() });
    if (!res.ok) throw new Error(`platforms failed: ${res.status}`);
    return res.json();
  }

  async connect(request: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/integrations/connect`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error(`connect failed: ${res.status}`);
    return res.json();
  }

  async sync(connectionId: string, tenantId = "default", payload: unknown = {}): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/integrations/${connectionId}/sync`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ tenant_id: tenantId, payload }),
    });
    if (!res.ok) throw new Error(`sync failed: ${res.status}`);
    return res.json();
  }
}
