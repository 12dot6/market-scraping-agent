const BASE = "/api";

export interface IngredientItem {
  name: string;
  internal_name: string | null;
  component: string;
  is_dye_active: boolean;
}

export interface ProductResult {
  id: string;
  url: string;
  name: string;
  in_scope: boolean;
  scope_reason: string | null;
  ingredients: IngredientItem[];
  error: string | null;
}

export interface JobCreated {
  job_id: string;
}

export interface JobSummary {
  id: string;
  status: "queued" | "running" | "complete" | "failed";
  url_count: number;
  processed: number;
  in_scope: number;
  excluded: number;
  errors: number;
  created_at: string;
  completed_at: string | null;
}

export async function postJob(urls: string[]): Promise<JobCreated> {
  const res = await fetch(`${BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ urls }),
  });
  if (!res.ok) throw new Error(`POST /api/jobs failed: ${res.status}`);
  return res.json();
}

export async function getJobs(): Promise<JobSummary[]> {
  const res = await fetch(`${BASE}/jobs`);
  if (!res.ok) throw new Error(`GET /api/jobs failed: ${res.status}`);
  return res.json();
}
