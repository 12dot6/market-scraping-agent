# Story E3-S2: Ingredient Table Component (Per-Run)

**Epic:** E3 — Results UI & Export  
**Story ID:** E3-S2  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want a sortable, searchable ingredient table for a run's results  
So that I can analyse ingredient frequency within a batch

---

## Acceptance Criteria

- [ ] Columns: ingredient name, internal name, count, frequency bar
- [ ] Sort by count (default) or name — client-side, no API call
- [ ] Dye active rows: amber left border
- [ ] Search box filters by ingredient name (client-side)
- [ ] Toggle: "Dye actives only" filters list
- [ ] Row click expands a panel listing which products in this run contain the ingredient

---

## Technical Requirements

### File to Create

`frontend/src/components/IngredientTable.tsx`

### API Data Needed

The `GET /api/jobs/{id}/products` response (from E1-S4) includes `ingredients: IngredientItem[]` per product. The ingredient table must be derived client-side from this data — no separate `/api/ingredients?job_id={id}` endpoint exists yet.

**Derive aggregate ingredient data client-side:**
```typescript
interface AggregatedIngredient {
  name: string;
  internal_name: string | null;
  count: number;  // how many products in this run contain it
  is_dye_active: boolean;
  products: string[];  // product names that contain this ingredient
}

function aggregateIngredients(products: ProductResult[]): AggregatedIngredient[] {
  const map = new Map<string, AggregatedIngredient>();
  for (const product of products) {
    for (const ing of product.ingredients) {
      if (!map.has(ing.name)) {
        map.set(ing.name, {
          name: ing.name,
          internal_name: ing.internal_name,
          count: 0,
          is_dye_active: ing.is_dye_active,
          products: [],
        });
      }
      const entry = map.get(ing.name)!;
      entry.count += 1;
      entry.products.push(product.name || product.url);
      if (ing.is_dye_active) entry.is_dye_active = true;
    }
  }
  return [...map.values()];
}
```

### IngredientTable.tsx

```tsx
import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

type SortKey = "count" | "name";
type SortDir = "asc" | "desc";

interface IngredientTableProps {
  products: ProductResult[];  // from GET /api/jobs/{id}/products
}

export function IngredientTable({ products }: IngredientTableProps) {
  const [search, setSearch] = useState("");
  const [dyeOnly, setDyeOnly] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("count");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const ingredients = useMemo(() => aggregateIngredients(products), [products]);

  const filtered = useMemo(() => {
    let list = ingredients;
    if (dyeOnly) list = list.filter(i => i.is_dye_active);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(i => i.name.toLowerCase().includes(q));
    }
    return [...list].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "count") cmp = a.count - b.count;
      if (sortKey === "name") cmp = a.name.localeCompare(b.name);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [ingredients, search, dyeOnly, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir(key === "count" ? "desc" : "asc");
    }
  }

  const maxCount = Math.max(...ingredients.map(i => i.count), 1);

  return (
    <div>
      {/* Controls */}
      <div className="flex items-center gap-4 mb-4">
        <Input
          placeholder="Search ingredients..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <div className="flex items-center gap-2">
          <Switch id="dye-only" checked={dyeOnly} onCheckedChange={setDyeOnly} />
          <Label htmlFor="dye-only">Dye actives only</Label>
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[2fr_1fr_80px_1fr] gap-2 px-4 py-2 bg-muted text-xs font-semibold uppercase tracking-wider">
          <button onClick={() => toggleSort("name")} className="text-left">
            Ingredient {sortKey === "name" ? (sortDir === "asc" ? "↑" : "↓") : ""}
          </button>
          <span>Internal Name</span>
          <button onClick={() => toggleSort("count")} className="text-left">
            Count {sortKey === "count" ? (sortDir === "asc" ? "↑" : "↓") : ""}
          </button>
          <span>Frequency</span>
        </div>

        {/* Rows */}
        {filtered.length === 0 && (
          <p className="px-4 py-6 text-muted-foreground text-sm text-center">
            No ingredients match your search
          </p>
        )}
        {filtered.map(ing => (
          <Collapsible key={ing.name} open={expandedRow === ing.name}>
            <CollapsibleTrigger asChild>
              <div
                className={`grid grid-cols-[2fr_1fr_80px_1fr] gap-2 px-4 py-2 border-t cursor-pointer hover:bg-muted/50
                  ${ing.is_dye_active ? "border-l-4 border-l-amber-400" : "border-l-4 border-l-transparent"}`}
                onClick={() => setExpandedRow(expandedRow === ing.name ? null : ing.name)}
              >
                <span className="text-sm font-medium">{ing.name}</span>
                <span className="text-sm text-muted-foreground">{ing.internal_name ?? "—"}</span>
                <span className="text-sm">{ing.count}</span>
                <div className="flex items-center">
                  <div className="h-2 rounded bg-violet-500"
                       style={{ width: `${(ing.count / maxCount) * 100}%`, minWidth: "4px" }} />
                </div>
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="px-4 py-2 bg-muted/30 border-t text-sm">
                <p className="text-xs font-semibold uppercase tracking-wider mb-1">
                  Found in {ing.products.length} product{ing.products.length !== 1 ? "s" : ""}:
                </p>
                <ul className="list-disc list-inside space-y-0.5">
                  {ing.products.map((p, i) => <li key={i} className="text-muted-foreground">{p}</li>)}
                </ul>
              </div>
            </CollapsibleContent>
          </Collapsible>
        ))}
      </div>
    </div>
  );
}
```

---

## Implementation Tasks

- [ ] Create `frontend/src/components/IngredientTable.tsx`
- [ ] Implement client-side sort, search, filter, expand logic
- [ ] Verify `GET /api/jobs/{id}/products` response includes per-ingredient `is_dye_active` and `internal_name`

---

## Dev Notes

### Data Source: Derived from Products, Not a Separate API

This component receives `ProductResult[]` from the parent page (which already fetches products). It aggregates ingredient data client-side using `aggregateIngredients()`. No separate `/api/ingredients?job_id={id}` call is needed for this component.

The global ingredients screen (E4-S1) will use a different data source (server-side `GET /api/ingredients`), but this per-run table works client-side.

### Only Count Unique Product Occurrences

`count` = number of products in this run that contain this ingredient. If a product has the same ingredient listed twice in different components (unlikely but possible), count it once per product. Use a `Set<string>` per ingredient to track product IDs if needed.

### Frequency Bar: Relative to Max

The bar width is `(ing.count / maxCount) * 100%`. This gives a relative view. If all ingredients appear in every product, all bars are 100% wide — that's correct behavior.

### Dye Active Row Highlighting

Amber left border (`border-l-4 border-l-amber-400`) on the row, not background color. This preserves readability of the row content while clearly marking dye actives. Non-dye rows get a transparent left border to maintain layout consistency.

### Shadcn Collapsible

Use Shadcn's `<Collapsible>` with `open` controlled by `expandedRow === ing.name`. Only one row is expanded at a time (clicking the same row again collapses it).

### Performance: useMemo

Both `aggregateIngredients(products)` and the filtered/sorted list use `useMemo`. The products list doesn't change between renders, so this is a pure optimization. Don't skip the memos — large runs could have 50+ products with 100+ unique ingredients.
