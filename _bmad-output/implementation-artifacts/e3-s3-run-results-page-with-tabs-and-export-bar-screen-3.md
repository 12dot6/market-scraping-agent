# Story E3-S3: Run Results Page with Tabs and Export Bar (Screen 3)

**Epic:** E3 — Results UI & Export  
**Story ID:** E3-S3  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want a tabbed results view with a persistent export bar  
So that I can navigate between products, ingredients, and exclusions and download data

---

## Acceptance Criteria

- [ ] Export bar (always visible): run date + stats + [Download CSV] [Download MD] [Download ZIP]
- [ ] Three tabs: Products | Ingredients | Excluded
- [ ] Products tab: list of ProductCards (in-scope products)
- [ ] Ingredients tab: IngredientTable for this run
- [ ] Excluded tab: table of excluded products with name, URL, reason
- [ ] Page navigable via `/results/{jobId}`

---

## Technical Requirements

### File to Create

`frontend/src/pages/RunResults.tsx`

### API Used

- `GET /api/jobs/{id}/products` — fetch all products for this run (already defined in E1-S4)
- `GET /api/jobs/{id}` — fetch job metadata (date, stats)
- Export links: `/api/jobs/{id}/export/csv`, `/api/jobs/{id}/export/md`, `/api/jobs/{id}/export/zip` (E3-S4)

### RunResults.tsx Structure

```tsx
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProductCard } from "@/components/ProductCard";
import { IngredientTable } from "@/components/IngredientTable";
import { ExportBar } from "@/components/ExportBar";
import { getProducts, getJob } from "@/lib/api";

export default function RunResults() {
  const { jobId } = useParams<{ jobId: string }>();

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ["products", jobId],
    queryFn: () => getProducts(jobId!),
  });

  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId!),
  });

  if (productsLoading) return <LoadingSkeleton />;

  const inScopeProducts = products?.filter(p => p.in_scope && !p.error) ?? [];
  const excludedProducts = products?.filter(p => !p.in_scope || p.error) ?? [];

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Export bar — always visible */}
      <ExportBar jobId={jobId!} job={job} />

      {/* Tabs */}
      <Tabs defaultValue="products" className="mt-6">
        <TabsList>
          <TabsTrigger value="products">
            Products ({inScopeProducts.length})
          </TabsTrigger>
          <TabsTrigger value="ingredients">Ingredients</TabsTrigger>
          <TabsTrigger value="excluded">
            Excluded ({excludedProducts.length})
          </TabsTrigger>
        </TabsList>

        {/* Products tab */}
        <TabsContent value="products">
          {inScopeProducts.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              No in-scope products found for this run
            </div>
          ) : (
            inScopeProducts.map(p => <ProductCard key={p.id} product={p} />)
          )}
        </TabsContent>

        {/* Ingredients tab */}
        <TabsContent value="ingredients">
          {products && products.length > 0 ? (
            <IngredientTable products={products} />
          ) : (
            <div className="py-12 text-center text-muted-foreground">
              No ingredients data available
            </div>
          )}
        </TabsContent>

        {/* Excluded tab */}
        <TabsContent value="excluded">
          {excludedProducts.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              All products were in scope — nothing excluded
            </div>
          ) : (
            <ExcludedTable products={excludedProducts} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

### ExportBar Component

```tsx
// Create frontend/src/components/ExportBar.tsx
interface ExportBarProps {
  jobId: string;
  job: JobDetail | undefined;
}

export function ExportBar({ jobId, job }: ExportBarProps) {
  function download(format: "csv" | "md" | "zip") {
    window.open(`/api/jobs/${jobId}/export/${format}`, "_blank");
  }

  return (
    <div className="flex items-center justify-between bg-white border rounded-lg p-4 shadow-sm">
      <div>
        {job && (
          <>
            <span className="font-medium">{formatDate(job.created_at)}</span>
            <span className="text-muted-foreground ml-3 text-sm">
              {job.in_scope} in scope · {job.excluded} excluded · {job.errors} errors
            </span>
          </>
        )}
      </div>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={() => download("csv")}>
          Download CSV
        </Button>
        <Button variant="outline" size="sm" onClick={() => download("md")}>
          Download MD
        </Button>
        <Button variant="outline" size="sm" onClick={() => download("zip")}>
          Download ZIP
        </Button>
      </div>
    </div>
  );
}
```

### ExcludedTable Component (inline in RunResults or separate file)

```tsx
function ExcludedTable({ products }: { products: ProductResult[] }) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="grid grid-cols-[2fr_3fr_2fr] px-4 py-2 bg-muted text-xs font-semibold uppercase tracking-wider">
        <span>Product</span>
        <span>URL</span>
        <span>Reason</span>
      </div>
      {products.map(p => (
        <div key={p.id} className="grid grid-cols-[2fr_3fr_2fr] px-4 py-3 border-t text-sm">
          <span>{p.name || "Unknown"}</span>
          <a href={p.url} target="_blank" rel="noopener noreferrer"
             className="text-violet-600 hover:underline truncate block">
            {p.url}
          </a>
          <span className="text-muted-foreground">{p.scope_reason ?? p.error ?? "Not in scope"}</span>
        </div>
      ))}
    </div>
  );
}
```

### API Functions to Add to api.ts

```typescript
// Add to api.ts
export async function getProducts(jobId: string): Promise<ProductResult[]> {
  const res = await fetch(`/api/jobs/${jobId}/products`);
  if (!res.ok) throw new Error(`GET products failed: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<JobDetail> {
  const res = await fetch(`/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`GET job failed: ${res.status}`);
  return res.json();
}
```

### Loading Skeleton

```tsx
function LoadingSkeleton() {
  return (
    <div className="max-w-6xl mx-auto p-6 space-y-4">
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}
```

---

## Implementation Tasks

- [ ] Create `frontend/src/pages/RunResults.tsx` with tab state
- [ ] Create `frontend/src/components/ExportBar.tsx`
- [ ] Add `getProducts` and `getJob` to `frontend/src/lib/api.ts`
- [ ] Add `GET /api/ingredients?job_id={id}` variant for per-run ingredient table (if needed — but E3-S2 derives this client-side, so may not be needed)
- [ ] Add route `/results/:jobId` to React Router in `App.tsx`

---

## Dev Notes

### ExportBar — window.open for File Downloads

Using `window.open(url, "_blank")` triggers a file download for endpoints that return `Content-Disposition: attachment`. Do not use `fetch()` for downloads — you'd need to handle blob URLs. The export endpoints (E3-S4) must set the correct response headers.

### Tab State Persistence

Shadcn `<Tabs>` maintains tab state in local component state by default (not URL). The selected tab resets on page navigation. This is acceptable for now — URL-based tab state (e.g., `?tab=ingredients`) can be added later if needed.

### Products Tab: Only In-Scope Products

The Products tab shows `products.filter(p => p.in_scope && !p.error)`. Excluded products (out of scope OR errored) go to the Excluded tab. Both groups are derived from the same API response.

### ExportBar: Always Visible

The export bar is above the `<Tabs>` component, not inside any tab. It remains visible regardless of which tab is selected. This is a deliberate UX decision (per the UX spec: "Export actions stay persistent and obvious").

### Empty States Required

Per E5-S1 requirements (which this story should anticipate):
- Products tab empty: "No in-scope products found for this run"
- Excluded tab empty: "All products were in scope — nothing excluded"

Add these now rather than waiting for E5-S1 to avoid regression.

### Date Formatting

```typescript
function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}
```
