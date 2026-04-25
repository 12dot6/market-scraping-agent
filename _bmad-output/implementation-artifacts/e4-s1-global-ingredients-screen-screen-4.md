# Story E4-S1: Global Ingredients Screen (Screen 4)

**Epic:** E4 — Global Ingredients & Deployment  
**Story ID:** E4-S1  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want to see ingredient frequency across all scraping runs  
So that I can identify the most commonly used ingredients in the full dataset

---

## Acceptance Criteria

- [ ] Same IngredientTable component as per-run, but queries `GET /api/ingredients` (no job_id filter)
- [ ] Run filter dropdown: "All runs" or select a specific run by date
- [ ] Date range filter: from/to date pickers
- [ ] [Download Master CSV] button triggers `GET /api/export/master-csv`
- [ ] Frequency chart (Recharts bar chart) showing top 20 ingredients by count
- [ ] Navigable at `/results` (no job ID)

---

## Technical Requirements

### Files to Create

```
frontend/src/
├── pages/
│   └── Ingredients.tsx
└── components/
    └── FrequencyChart.tsx
```

### New Backend Endpoint Needed: GET /api/ingredients

Add to `backend/routers/results.py`:

```python
from fastapi import Query
from backend.models import Ingredient

@router.get("/api/ingredients")
def get_ingredients(
    job_id: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Returns global ingredient list, optionally filtered by job or date range.
    For job_id filter: compute per-run count from ProductIngredient table.
    For global (no filter): return Ingredient table directly.
    """
    if job_id:
        # Per-run: aggregate from junction table
        from sqlalchemy import func
        rows = (
            db.query(
                Ingredient.name,
                Ingredient.internal_name,
                func.count(ProductIngredient.ingredient_id).label("count"),
                Ingredient.is_dye_active,
            )
            .join(ProductIngredient, Ingredient.id == ProductIngredient.ingredient_id)
            .join(Product, ProductIngredient.product_id == Product.id)
            .filter(Product.job_id == job_id)
            .group_by(Ingredient.id)
            .order_by(func.count(ProductIngredient.ingredient_id).desc())
            .all()
        )
    else:
        # Global: use stored count on Ingredient table
        rows = (
            db.query(Ingredient)
            .order_by(Ingredient.count.desc())
            .all()
        )
    
    return [
        {
            "name": r.name,
            "internal_name": r.internal_name,
            "count": r.count,
            "is_dye_active": r.is_dye_active,
        }
        for r in rows
    ]
```

### GlobalIngredientTable Adapter

The existing `IngredientTable` component (E3-S2) expects `ProductResult[]` and aggregates client-side. For the global view, we already have aggregated data from the API.

Two options:
1. **Extend IngredientTable** to accept either `ProductResult[]` OR pre-aggregated `AggregatedIngredient[]`
2. **Create a new GlobalIngredientTable** that uses the API data directly

**Recommended: Option 2** — keeps per-run and global concerns separate. GlobalIngredientTable accepts `AggregatedIngredient[]` directly from the API.

Actually `IngredientTable` can be refactored to accept `AggregatedIngredient[]` as an optional prop. If both `products` and `aggregated` are provided, prefer `aggregated`. This avoids duplication.

### FrequencyChart.tsx (Recharts)

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface FrequencyChartProps {
  data: { name: string; count: number; is_dye_active: boolean }[];
}

export function FrequencyChart({ data }: FrequencyChartProps) {
  const top20 = [...data].sort((a, b) => b.count - a.count).slice(0, 20);
  const chartData = top20.map(d => ({
    name: d.name.length > 20 ? d.name.slice(0, 20) + "…" : d.name,
    count: d.count,
    fill: d.is_dye_active ? "#F59E0B" : "#7C3AED",
  }));

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
          <XAxis type="number" />
          <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value) => [`${value} products`, "Count"]} />
          <Bar dataKey="count" fill="#7C3AED">
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Ingredients.tsx (Page)

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FrequencyChart } from "@/components/FrequencyChart";
import { IngredientTable } from "@/components/IngredientTable";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { getIngredients, getJobs } from "@/lib/api";

export default function Ingredients() {
  const [selectedJobId, setSelectedJobId] = useState<string>("all");

  const { data: jobs } = useQuery({ queryKey: ["jobs"], queryFn: getJobs });
  const { data: ingredients, isLoading } = useQuery({
    queryKey: ["ingredients", selectedJobId],
    queryFn: () => getIngredients(selectedJobId === "all" ? undefined : selectedJobId),
  });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Global Ingredients</h1>
        <div className="flex items-center gap-4">
          {/* Run filter */}
          <Select value={selectedJobId} onValueChange={setSelectedJobId}>
            <SelectTrigger className="w-52">
              <SelectValue placeholder="All runs" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All runs</SelectItem>
              {jobs?.map(job => (
                <SelectItem key={job.id} value={job.id}>
                  {formatDate(job.created_at)} ({job.in_scope} products)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {/* Download master CSV */}
          <Button variant="outline" onClick={() => window.open("/api/export/master-csv", "_blank")}>
            Download Master CSV
          </Button>
        </div>
      </div>

      {/* Frequency chart */}
      {ingredients && ingredients.length > 0 && (
        <div className="mb-8 border rounded-lg p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-4 text-muted-foreground">
            Top 20 Ingredients by Frequency
          </h2>
          <FrequencyChart data={ingredients} />
        </div>
      )}

      {/* Ingredient table */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : ingredients && ingredients.length > 0 ? (
        <IngredientTable aggregated={ingredients} />
      ) : (
        <div className="py-12 text-center text-muted-foreground">
          No ingredients yet — run a scrape to populate this table
        </div>
      )}
    </div>
  );
}
```

### API Function to Add to api.ts

```typescript
export async function getIngredients(jobId?: string): Promise<AggregatedIngredient[]> {
  const params = jobId ? `?job_id=${jobId}` : "";
  const res = await fetch(`/api/ingredients${params}`);
  if (!res.ok) throw new Error(`GET /api/ingredients failed: ${res.status}`);
  return res.json();
}
```

### Nav Header Link

Add a nav link to the global ingredients screen. In `App.tsx` or a shared `<Header>` component:
```tsx
<nav>
  <Link to="/">Home</Link>
  <Link to="/results">Ingredients</Link>
</nav>
```

---

## Implementation Tasks

- [ ] Create `frontend/src/pages/Ingredients.tsx`
- [ ] Create `frontend/src/components/FrequencyChart.tsx` using Recharts
- [ ] Add run filter + date range query params to `GET /api/ingredients` (backend)
- [ ] Wire [Download Master CSV] to export endpoint
- [ ] Add nav link in app header
- [ ] Add `recharts` to frontend package.json dependencies

---

## Dev Notes

### Recharts Installation

```bash
npm install recharts
```

Recharts is a React charting library built on D3. Use the `BarChart` with `layout="vertical"` for a horizontal bar chart (ingredient names on Y axis, counts on X axis). This is more readable than vertical bars for long ingredient names.

### Cell Fill Colors

Use `<Cell>` from recharts to set per-bar fill color. Dye active bars: amber `#F59E0B`. Regular bars: violet `#7C3AED`.

### IngredientTable — Dual Mode

Modify E3-S2's `IngredientTable` to accept `aggregated?: AggregatedIngredient[]` as an optional prop. If provided, skip the `aggregateIngredients(products)` calculation and use it directly:

```tsx
interface IngredientTableProps {
  products?: ProductResult[];
  aggregated?: AggregatedIngredient[];
}
// In component:
const ingredients = useMemo(
  () => aggregated ?? (products ? aggregateIngredients(products) : []),
  [aggregated, products]
);
```

### Run Filter — No Date Pickers in MVP

The AC mentions date range filters. Add a basic "from/to" `<Input type="date">` pair but keep it optional for MVP. The run filter dropdown (select by run date) covers the core use case. Full date range filtering can be a quick follow-on.

### Route: /results (No Job ID)

This route is for the global view. `/results/:jobId` is for per-run results (E3-S3). Both routes exist. The nav "Ingredients" link goes to `/results` (no ID).
