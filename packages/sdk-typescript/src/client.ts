export type ScanSource = Record<string, unknown>;

export interface ApiMeta {
  trace_id: string;
  request_id: string;
  correlation_id: string;
  execution_ms: number;
  confidence?: number | null;
  agent_version: string;
  agent_name: string;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: ApiMeta;
}

export interface ScanRecord {
  scan_id: string;
  tenant_id: string;
  status: string;
  source: ScanSource;
  idempotency_key: string;
  requested_by: string;
  webhook_url?: string | null;
  model_id?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export type ContextModelEnvelope = ApiEnvelope<Record<string, unknown>>;

export interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  bearerToken?: string;
  fetchImpl?: typeof fetch;
}

function authHeaders(options: ClientOptions): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  if (options.apiKey) {
    headers["X-API-Key"] = options.apiKey;
  } else if (options.bearerToken) {
    headers.Authorization = `Bearer ${options.bearerToken}`;
  }
  return headers;
}

export class ScansClient {
  constructor(
    private readonly baseUrl: string,
    private readonly options: ClientOptions,
  ) {}

  private fetch = this.options.fetchImpl ?? fetch;

  async create(input: {
    source: ScanSource;
    idempotencyKey?: string;
    webhookUrl?: string;
  }): Promise<ScanRecord> {
    const headers = authHeaders(this.options);
    if (input.idempotencyKey) {
      (headers as Record<string, string>)["Idempotency-Key"] = input.idempotencyKey;
    }
    const resp = await this.fetch(`${this.baseUrl}/v1/scans`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        source: input.source,
        idempotency_key: input.idempotencyKey,
        webhook_url: input.webhookUrl,
      }),
    });
    if (!resp.ok) {
      throw new Error(`create scan failed: ${resp.status}`);
    }
    const body = (await resp.json()) as ApiEnvelope<ScanRecord>;
    return body.data;
  }

  async get(scanId: string): Promise<ScanRecord> {
    const resp = await this.fetch(`${this.baseUrl}/v1/scans/${scanId}`, {
      headers: authHeaders(this.options),
    });
    if (!resp.ok) {
      throw new Error(`get scan failed: ${resp.status}`);
    }
    const body = (await resp.json()) as ApiEnvelope<ScanRecord>;
    return body.data;
  }

  async list(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<{ items: ScanRecord[]; limit: number; offset: number }> {
    const qs = new URLSearchParams();
    if (params?.limit != null) qs.set("limit", String(params.limit));
    if (params?.offset != null) qs.set("offset", String(params.offset));
    if (params?.status) qs.set("status", params.status);
    const resp = await this.fetch(`${this.baseUrl}/v1/scans?${qs}`, {
      headers: authHeaders(this.options),
    });
    if (!resp.ok) {
      throw new Error(`list scans failed: ${resp.status}`);
    }
    const body = (await resp.json()) as ApiEnvelope<{
      items: ScanRecord[];
      limit: number;
      offset: number;
    }>;
    return body.data;
  }

  async cancel(scanId: string): Promise<ScanRecord> {
    const resp = await this.fetch(`${this.baseUrl}/v1/scans/${scanId}/cancel`, {
      method: "POST",
      headers: authHeaders(this.options),
    });
    if (!resp.ok) {
      throw new Error(`cancel scan failed: ${resp.status}`);
    }
    const body = (await resp.json()) as ApiEnvelope<ScanRecord>;
    return body.data;
  }
}

export class ModelsClient {
  constructor(
    private readonly baseUrl: string,
    private readonly options: ClientOptions,
  ) {}

  private fetch = this.options.fetchImpl ?? fetch;

  async get(modelId: string, version?: number): Promise<ContextModelEnvelope> {
    const qs = version != null ? `?version=${version}` : "";
    const resp = await this.fetch(`${this.baseUrl}/v1/context-models/${modelId}${qs}`, {
      headers: authHeaders(this.options),
    });
    if (!resp.ok) {
      throw new Error(`get model failed: ${resp.status}`);
    }
    return (await resp.json()) as ContextModelEnvelope;
  }

  async listVersions(modelId: string): Promise<{
    model_id: string;
    versions: Array<{
      version: number;
      schema_version: string;
      confidence: number;
      created_at?: string | null;
    }>;
  }> {
    const resp = await this.fetch(`${this.baseUrl}/v1/context-models/${modelId}/versions`, {
      headers: authHeaders(this.options),
    });
    if (!resp.ok) {
      throw new Error(`list versions failed: ${resp.status}`);
    }
    const body = (await resp.json()) as ApiEnvelope<{
      model_id: string;
      versions: Array<{
        version: number;
        schema_version: string;
        confidence: number;
        created_at?: string | null;
      }>;
    }>;
    return body.data;
  }

  async diff(
    modelId: string,
    fromVersion: number,
    toVersion: number,
  ): Promise<Record<string, unknown>> {
    const qs = new URLSearchParams({
      from: String(fromVersion),
      to: String(toVersion),
    });
    const resp = await this.fetch(
      `${this.baseUrl}/v1/context-models/${modelId}/diff?${qs}`,
      { headers: authHeaders(this.options) },
    );
    if (!resp.ok) {
      throw new Error(`diff models failed: ${resp.status}`);
    }
    const body = (await resp.json()) as ApiEnvelope<Record<string, unknown>>;
    return body.data;
  }
}

export class GieContextClient {
  readonly scans: ScansClient;
  readonly models: ModelsClient;

  constructor(options: ClientOptions = {}) {
    const baseUrl = (options.baseUrl ?? "http://localhost:8080").replace(/\/$/, "");
    this.scans = new ScansClient(baseUrl, options);
    this.models = new ModelsClient(baseUrl, options);
  }
}
