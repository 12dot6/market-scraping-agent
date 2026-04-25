# Story E3-S1: ProductCard Component

**Epic:** E3 — Results UI & Export  
**Story ID:** E3-S1  
**Status:** review  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want to see each product's ingredients grouped by component with dye actives highlighted  
So that I can quickly identify formulation patterns and active ingredients

---

## Acceptance Criteria

- [x] Component section headers in ALL CAPS sourced from Claude API `components` field
- [x] Dye actives shown as amber ⚠️ pill inline within ingredient lists
- [x] Dye actives also summarised in card header
- [x] Lists >8 ingredients collapsed with "Show all N ingredients" toggle
- [x] Mapped ingredients (have internal_name): dotted underline + hover tooltip
- [x] In-scope badge (🟢) shown in card header; INCI names preserved exactly as scraped
- [x] Card renders correctly for single-component products (`{"All": [...]}`)

---

## Technical Requirements

### Files to Create

```
frontend/src/components/
├── ProductCard.tsx
├── DyeActiveBadge.tsx
└── ScopeBadge.tsx
```

### Data Type (from api.ts)

```typescript
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
```

### ProductCard.tsx

```tsx
import { useState } from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";

const COLLAPSE_THRESHOLD = 8;

interface ProductCardProps {
  product: ProductResult;
}

export function ProductCard({ product }: ProductCardProps) {
  // Group ingredients by component
  const componentMap = new Map<string, IngredientItem[]>();
  for (const ing of product.ingredients) {
    if (!componentMap.has(ing.component)) componentMap.set(ing.component, []);
    componentMap.get(ing.component)!.push(ing);
  }

  const dyeActives = product.ingredients.filter(i => i.is_dye_active);

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <a href={product.url} target="_blank" rel="noopener noreferrer"
               className="font-semibold text-base hover:underline">
              {product.name || product.url}
            </a>
            {dyeActives.length > 0 && (
              <p className="text-sm text-amber-600 mt-1">
                ⚠️ Dye actives: {dyeActives.map(d => d.name).join(", ")}
              </p>
            )}
          </div>
          <ScopeBadge inScope={product.in_scope} />
        </div>
      </CardHeader>
      <CardContent>
        {[...componentMap.entries()].map(([componentName, ingredients]) => (
          <ComponentSection
            key={componentName}
            name={componentName}
            ingredients={ingredients}
          />
        ))}
        {product.ingredients.length === 0 && (
          <p className="text-sm text-muted-foreground italic">No ingredients listed</p>
        )}
      </CardContent>
    </Card>
  );
}
```

### DyeActiveBadge.tsx

```tsx
export function DyeActiveBadge() {
  return (
    <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-xs px-1 py-0">
      ⚠️
    </Badge>
  );
}
```

### ScopeBadge.tsx

```tsx
interface ScopeBadgeProps {
  inScope: boolean;
}

export function ScopeBadge({ inScope }: ScopeBadgeProps) {
  if (inScope) {
    return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300">🟢 In scope</Badge>;
  }
  return <Badge variant="secondary">Excluded</Badge>;
}
```

### Design System Alignment

- Colors: amber `#F59E0B` for dye actives, emerald `#10B981` for in-scope
- Component header: `text-xs font-semibold uppercase tracking-wider text-muted-foreground`
- Tooltip: Shadcn `<Tooltip>` with `<TooltipProvider>` in App root
- Collapse threshold: 8 ingredients (per AC)
- INCI names: preserve exactly — no lowercasing, no normalization

---

## Implementation Tasks

- [x] Create `frontend/src/components/ProductCard.tsx`
- [x] Create `frontend/src/components/DyeActiveBadge.tsx`
- [x] Create `frontend/src/components/ScopeBadge.tsx`
- [x] Implement ingredient collapse/expand logic
- [x] Wrap app with `<TooltipProvider>` in `App.tsx`

---

## Dev Notes

### Single-Component Products

When Claude returns `{"All": ["Ingredient1", "Ingredient2", ...]}` (no meaningful grouping), do NOT render the "All" header — it's redundant. The check `{name !== "All" && <h4>...` handles this.

### INCI Names Must Be Preserved Exactly

Do not call `.toLowerCase()`, `.trim()`, or any normalization on `ingredient.name` in the display layer. These are INCI names exactly as returned by Claude (which preserves them as scraped per PRD FR-03).

### TooltipProvider Requirement

Shadcn `<Tooltip>` requires `<TooltipProvider>` to be an ancestor. Add it in `App.tsx`:
```tsx
import { TooltipProvider } from "@/components/ui/tooltip";
<TooltipProvider><RouterProvider ... /></TooltipProvider>
```

### Comma Separation in Ingredient List

The ingredient chip rendering adds trailing commas. Watch out for the last item — you may want to omit the trailing comma on the last ingredient in a component section. Use `index === visible.length - 1` to conditionally skip it.

### Collapsed State Per Card

Each `ComponentSection` manages its own `expanded` state. Different component sections on the same card can be independently expanded. This is the correct behavior.

---

## Dev Agent Record

### Implementation Plan

All 5 tasks implemented in a single session:

1. **`frontend/src/components/ui/card.tsx`** — New Shadcn-style Card, CardHeader, CardContent components (not pre-existing). Uses `forwardRef` pattern consistent with other UI components.

2. **`frontend/src/components/ui/tooltip.tsx`** — Pure CSS tooltip (no Radix UI — it's not in `package.json`). Uses Tailwind `group`/`group-hover` pattern. `TooltipProvider` is a passthrough no-op. `TooltipTrigger` supports `asChild` via `React.cloneElement`. `TooltipContent` is absolutely positioned and opacity-animated.

3. **`frontend/src/lib/api.ts`** — Added `IngredientItem` and `ProductResult` interfaces at top of file.

4. **`frontend/src/components/DyeActiveBadge.tsx`** — Amber pill badge with ⚠️ emoji, uses existing Badge component with custom className.

5. **`frontend/src/components/ScopeBadge.tsx`** — Emerald 🟢 In scope / secondary Excluded badge.

6. **`frontend/src/components/ProductCard.tsx`** — Full ProductCard with `ComponentSection` and `IngredientChip` sub-components. Implements:
   - Map-based grouping of ingredients by component
   - Collapse/expand per section at threshold of 8
   - Trailing comma omitted on last visible ingredient (`isLast` prop)
   - Tooltip for mapped ingredients (`internal_name != null`)
   - DyeActiveBadge inline for `is_dye_active` ingredients
   - "All" header suppressed for single-component products

7. **`frontend/src/App.tsx`** — Wrapped `<Routes>` with `<TooltipProvider>`.

TypeScript type check (`tsc --noEmit`) passes with exit code 0.

**Note on Tooltip:** `TooltipProvider` wraps `<Routes>` in App.tsx. The tooltip is purely CSS-driven (group-hover), so it works without Radix/JS state. The `asChild` prop on `TooltipTrigger` uses `React.cloneElement` to pass props to the child element directly.

### Completion Notes

All 5 tasks checked. All 7 acceptance criteria satisfied:
- ✅ Component headers ALL CAPS (via `uppercase tracking-wider` Tailwind classes)
- ✅ Dye actives shown as amber ⚠️ pill inline
- ✅ Dye actives summarised in card header
- ✅ Lists >8 collapsed with "Show all N ingredients" toggle (per-section state)
- ✅ Mapped ingredients: dotted underline + hover tooltip showing `internal_name`
- ✅ In-scope badge 🟢 in header; INCI names preserved exactly
- ✅ Single-component "All" renders without redundant header

### Debug Log

No blocking issues. Key decisions:
- No Radix UI available → implemented pure CSS tooltip using `group`/`group-hover`
- Badge `border` prop pattern: added `border` utility class directly in DyeActiveBadge/ScopeBadge classNames
- Last-comma suppression handled via `isLast` prop through to `IngredientChip`

---

## File List

- `frontend/src/components/ui/card.tsx` (created)
- `frontend/src/components/ui/tooltip.tsx` (created)
- `frontend/src/lib/api.ts` (modified — added IngredientItem, ProductResult interfaces)
- `frontend/src/components/DyeActiveBadge.tsx` (created)
- `frontend/src/components/ScopeBadge.tsx` (created)
- `frontend/src/components/ProductCard.tsx` (created)
- `frontend/src/App.tsx` (modified — wrapped with TooltipProvider)

---

## Change Log

- 2026-04-25: Implemented E3-S1 ProductCard component — card UI, tooltip, ingredient grouping, collapse/expand, dye active badges (Srini / AI)
