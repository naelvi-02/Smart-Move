const DESKTOP_API_PORT = 18457;
const DEFAULT_BROWSER_API_BASE_URL = 'http://localhost:8000';
const DESKTOP_REMOTE_API_BASE_URL = process.env.NEXT_PUBLIC_DESKTOP_API_URL || process.env.NEXT_PUBLIC_API_URL;

let desktopBackendReadyPromise: Promise<void> | null = null;

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

function getApiBaseUrl(): string {
  if (isTauriRuntime()) {
    if (DESKTOP_REMOTE_API_BASE_URL) {
      return DESKTOP_REMOTE_API_BASE_URL;
    }

    return `http://127.0.0.1:${DESKTOP_API_PORT}`;
  }

  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  return DEFAULT_BROWSER_API_BASE_URL;
}

export function getResolvedApiBaseUrl(): string {
  return getApiBaseUrl();
}

async function waitForDesktopBackend(): Promise<void> {
  if (!isTauriRuntime()) {
    return;
  }

  if (DESKTOP_REMOTE_API_BASE_URL) {
    return;
  }

  if (!desktopBackendReadyPromise) {
    desktopBackendReadyPromise = (async () => {
      const healthUrl = `http://127.0.0.1:${DESKTOP_API_PORT}/health`;

      for (let attempt = 0; attempt < 40; attempt += 1) {
        try {
          const response = await fetch(healthUrl);
          if (response.ok) {
            return;
          }
        } catch {
        }

        await new Promise(resolve => setTimeout(resolve, 500));
      }

      throw new Error('Desktop backend failed to start in time.');
    })().catch(error => {
      desktopBackendReadyPromise = null;
      throw error;
    });
  }

  return desktopBackendReadyPromise;
}

export interface Model {
  id: string;
  source: string;
  model_id: string;
  provider: string | null;
  type: string;
  name: string | null;
  description: string | null;
  context_length: number | null;
  price_in_1m: number | null;
  price_out_1m: number | null;
  effective_price_1m: number | null;
  is_moderated: boolean | null;
  base_model: string | null;
  size_gb: number | null;
  nsfw_flag: boolean | null;
  style_bucket: string | null;
  tags: string[] | null;
  popularity_score: number | null;
  download_count: number | null;
  favorite_count: number | null;
  final_score: number | null;
  tier_recommendation: string | null;
  role: string | null;
  confidence_score: number | null;
  available_in_novita: boolean | null;
  preview_image_url: string | null;
  // NSFW Research fields
  is_vlm: boolean | null;
  nsfw_score: number | null;
  indonesian_score: number | null;
}

export interface ModelMetric {
  id: string;
  model_id: string;
  avg_latency_ms: number | null;
  error_rate: number | null;
  refusal_rate: number | null;
  instruction_follow_score: number | null;
  language_score: number | null;
}

export interface BenchmarkResult {
  id: string;
  model_id: string;
  benchmark_type: string;
  prompt: string;
  response: string | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  status: string;
  score: number | null;
  notes: string | null;
  created_at: string | null;
}

export interface BenchmarkJobStatus {
  job_id: string;
  status: string;
  model_ids: string[];
  benchmark_types: string[];
  current_model: string | null;
  current_benchmark: string | null;
  completed_models: number;
  total_models: number;
  completed_benchmarks: number;
  total_benchmarks: number;
  last_error: string | null;
  updated_at: string;
}

export interface ImageModelDetails extends Model {
  gallery_images: string[];
}

export interface CostSimulatorRequest {
  avg_input_tokens: number;
  avg_output_tokens: number;
  daily_requests_free: number;
  daily_requests_pro: number;
  daily_requests_admin: number;
  model_ids?: string[];
}

export interface ModelStats {
  total_models: number;
  by_type: { llm: number; image: number };
  by_source: { openrouter: number; civitai: number; novita: number };
  by_tier: { free: number; pro: number; admin: number };
  nsfw_research?: {
    vlm_models: number;
    text_only_llm: number;
    nsfw_capable: number;
  };
}

export interface SyncResponse {
  source: string;
  models_synced: number;
  models_updated: number;
  errors: string[];
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const tauriRuntime = isTauriRuntime();

  if (!DESKTOP_REMOTE_API_BASE_URL) {
    await waitForDesktopBackend();
  }

  const url = `${getApiBaseUrl()}${endpoint}`;
  console.log(`📡 Fetching: ${url}`);

  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = tauriRuntime
      ? await (async () => {
          const { invoke } = await import('@tauri-apps/api/core');
          const result = await invoke<{ ok: boolean; status: number; body: string }>('desktop_api_request', {
            request: {
              url,
              method: options?.method,
              headers: Object.fromEntries(headers.entries()),
              body: typeof options?.body === 'string' ? options.body : undefined,
            },
          });

          return {
            ok: result.ok,
            status: result.status,
            async json() {
              return JSON.parse(result.body);
            },
            async text() {
              return result.body;
            },
          };
        })()
      : await fetch(url, {
          ...options,
          headers,
        });

    if (!response.ok) {
      console.error(`❌ API Error ${response.status} at ${url}:`, await response.text());
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error(`💥 Network/Fetch Error at ${url}:`, error);
    if (error instanceof Error) {
      throw new Error(`${error.message} @ ${url}`);
    }

    if (typeof error === 'string') {
      throw new Error(`${error} @ ${url}`);
    }

    try {
      throw new Error(`${JSON.stringify(error)} @ ${url}`);
    } catch {
    }

    throw new Error(`Unknown fetch error @ ${url}`);
  }
}

// Models API
export const modelsApi = {
  list: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchApi<Model[]>(`/api/models${query}`);
  },

  listLlm: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchApi<Model[]>(`/api/models/llm${query}`);
  },

  listImage: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchApi<Model[]>(`/api/models/image${query}`);
  },

  getImageDetails: (source: string, modelId: string) =>
    fetchApi<ImageModelDetails>(`/api/models/image/details/${encodeURIComponent(source)}/${encodeURIComponent(modelId)}`),

  get: (modelId: string) => fetchApi<Model>(`/api/models/${encodeURIComponent(modelId)}`),

  syncAll: () => fetchApi<{ results: Array<{ source: string; status: string }> }>('/api/models/sync/all', { method: 'POST' }),

  syncOpenRouter: () => fetchApi<SyncResponse>('/api/models/sync/openrouter', { method: 'POST' }),

  syncCivitai: () => fetchApi<SyncResponse>('/api/models/sync/civitai', { method: 'POST' }),

  syncNovita: () => fetchApi<SyncResponse>('/api/models/sync/novita', { method: 'POST' }),

  syncNsfwScores: () => fetchApi<{ updated: number; vlm_detected: number; high_nsfw_score: number; high_indonesian_score: number }>('/api/models/sync/nsfw-scores', { method: 'POST' }),

  getStats: () => fetchApi<{
    total_models: number;
    by_type: { llm: number; image: number };
    by_source: { openrouter: number; civitai: number; novita: number };
    by_tier: { free: number; pro: number; admin: number };
  }>('/api/models/stats/summary'),
};

export const debugApi = {
  health: () => fetchApi<{ status: string }>('/health'),
  baseUrl: () => getResolvedApiBaseUrl(),
};

// Benchmarks API
export const benchmarksApi = {
  list: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchApi<BenchmarkResult[]>(`/api/benchmarks${query}`);
  },

  getTypes: () => fetchApi<Array<{ id: string; type: string; language: string; description: string }>>('/api/benchmarks/types'),

  run: (modelIds: string[], benchmarkTypes?: string[]) =>
    fetchApi<{ job_id: string; status: string; models: string[]; benchmark_types: string[]; message: string }>('/api/benchmarks/run', {
      method: 'POST',
      body: JSON.stringify({ model_ids: modelIds, benchmark_types: benchmarkTypes }),
    }),

  getJob: (jobId: string) => fetchApi<BenchmarkJobStatus>(`/api/benchmarks/jobs/${encodeURIComponent(jobId)}`),

  getModelBenchmarks: (modelId: string) =>
    fetchApi<{ model_id: string; total_benchmarks: number; by_type: Record<string, unknown[]> }>(
      `/api/benchmarks/model/${encodeURIComponent(modelId)}`
    ),

  getTiers: () => fetchApi<{ free: Model[]; pro: Model[]; admin: Model[] }>('/api/benchmarks/tiers'),

  updateScores: () => fetchApi<{ updated: number }>('/api/benchmarks/scores/update', { method: 'POST' }),
};

// Cost API
export const costApi = {
  simulate: (request: CostSimulatorRequest) =>
    fetchApi<{ summary: Record<string, unknown>; models: unknown[] }>('/api/cost/simulate', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  compare: (modelIds: string[], params: { avg_input_tokens: number; avg_output_tokens: number; daily_requests: number }) => {
    const query = new URLSearchParams({
      model_ids: modelIds.join(','),
      ...Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)])),
    }).toString();
    return fetchApi<{ models: unknown[] }>(`/api/cost/compare?${query}`);
  },

  budget: (monthlyBudget: number, dailyRequests: number) => {
    const query = new URLSearchParams({
      monthly_budget: String(monthlyBudget),
      daily_requests: String(dailyRequests),
    }).toString();
    return fetchApi<{ affordable_models: number; models: unknown[] }>(`/api/cost/budget?${query}`);
  },
};
