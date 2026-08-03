export type KnowledgeQueryRequest = {
  query: string;
  domains?: string[];
  top_k?: number;
  version?: string;
  include_graph?: boolean;
  hybrid?: boolean;
};

export class KnowledgeClient {
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

  async query(body: KnowledgeQueryRequest): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/knowledge/query`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`knowledge query failed: ${res.status}`);
    return res.json();
  }

  async getNode(nodeId: string, version?: string): Promise<unknown> {
    const url = new URL(`${this.baseUrl}/v1/knowledge/nodes/${nodeId}`);
    if (version) url.searchParams.set("version", version);
    const res = await fetch(url, { headers: this.headers() });
    if (!res.ok) throw new Error(`get node failed: ${res.status}`);
    return res.json();
  }

  async upsert(payload: unknown): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/v1/knowledge/nodes`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`upsert failed: ${res.status}`);
    return res.json();
  }
}
