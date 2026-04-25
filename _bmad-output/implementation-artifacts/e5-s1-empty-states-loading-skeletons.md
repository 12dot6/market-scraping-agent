# Story E5-S1: Empty States & Loading Skeletons

**Epic:** E5 — Polish & Quality  
**Story ID:** E5-S1  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want informative empty states and loading feedback  
So that the app doesn't feel broken when there's no data yet

---

## Acceptance Criteria

- [ ] Home screen: "No runs yet — paste URLs above to get started" when job list is empty
- [ ] Run Results (Products tab): "No in-scope products found for this run" if all excluded
- [ ] Run Results (Excluded tab): "All products were in scope — nothing excluded" if none excluded
- [ ] Global Ingredients: "No ingredients yet — run a scrape to populate this table"
- [ ] All data-fetching views show a skeleton/spinner while loading

---

## Technical Requirements

### Scope

This is a polish story. Most of these empty states were already specified in E2-S2, E3-S3, and E4-S1 stories. This story exists to ensure they are all implemented consistently and to add loading skeletons to any views that are missing them.

### Shadcn Skeleton Component

Use `<Skeleton>` from Shadcn/ui for loading states:

```tsx
import { Skeleton } from "@/components/ui/skeleton";

// Card skeleton
function CardSkeleton() {
  return (
    <div className="border rounded-lg p-4 space-y-3 mb-4">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/6" />
      </div>
    </div>
  );
}

// Table skeleton
function TableSkeleton() {
  return (
    <div className="border rounded-lg overflow-hidden">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-4 px-4 py-3 border-b">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 flex-1" />
        </div>
      ))}
    </div>
  );
}
```

### Empty State Component (Reusable)

Create `frontend/src/components/EmptyState.tsx`:

```tsx
interface EmptyStateProps {
  message: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="py-12 text-center space-y-4">
      <p className="text-muted-foreground">{message}</p>
      {action && (
        <Button variant="outline" onClick={action.onClick}>{action.label}</Button>
      )}
    </div>
  );
}
```

### Per-Screen Inventory

**Home.tsx — Recent Runs section:**
```tsx
{recentJobs === undefined ? (
  // Loading
  Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full mb-2" />)
) : recentJobs.length === 0 ? (
  // Empty
  <EmptyState message="No runs yet — paste URLs above to get started" />
) : (
  recentJobs.map(job => <JobCard key={job.id} job={job} />)
)}
```

**RunResults.tsx — Products tab:**
```tsx
{inScopeProducts.length === 0 ? (
  <EmptyState message="No in-scope products found for this run" />
) : (
  inScopeProducts.map(p => <ProductCard key={p.id} product={p} />)
)}
```

**RunResults.tsx — Excluded tab:**
```tsx
{excludedProducts.length === 0 ? (
  <EmptyState message="All products were in scope — nothing excluded" />
) : (
  <ExcludedTable products={excludedProducts} />
)}
```

**RunResults.tsx — Loading state:**
```tsx
{productsLoading ? (
  <>
    <Skeleton className="h-16 w-full mb-4" />  {/* export bar */}
    <Skeleton className="h-10 w-64 mb-6" />    {/* tabs */}
    <CardSkeleton />
    <CardSkeleton />
    <CardSkeleton />
  </>
) : (
  // ... normal content
)}
```

**Ingredients.tsx (Global view) — Loading + empty:**
```tsx
{isLoading ? (
  <TableSkeleton />
) : ingredients?.length === 0 ? (
  <EmptyState message="No ingredients yet — run a scrape to populate this table" />
) : (
  <IngredientTable aggregated={ingredients} />
)}
```

### TanStack Query Error Boundaries

Add error state handling to all queries:

```tsx
const { data, isLoading, isError, refetch } = useQuery(...);

if (isError) {
  return (
    <EmptyState
      message="Failed to load data"
      action={{ label: "Retry", onClick: refetch }}
    />
  );
}
```

### Files to Create/Modify

- **Create:** `frontend/src/components/EmptyState.tsx`
- **Modify:** `Home.tsx` — add empty/loading states for recent runs
- **Modify:** `RunResults.tsx` — verify empty states already in place (from E3-S3)
- **Modify:** `Ingredients.tsx` — verify empty state already in place (from E4-S1)
- **Verify:** All `useQuery` calls handle `isError` with retry

---

## Implementation Tasks

- [ ] Add empty state components to Home, RunResults, Ingredients pages
- [ ] Add loading skeletons (Shadcn Skeleton) to all list/table views
- [ ] Add TanStack Query error boundaries with retry button
- [ ] Create reusable `EmptyState` component

---

## Dev Notes

### Skeleton Placeholders Match Layout

Skeleton elements should approximate the layout of the real content. For JobCard, use a single `h-16` skeleton. For ProductCard, use a multi-row skeleton that resembles a card. This prevents layout shift when real data loads.

### Don't Show Skeleton During Refetch

TanStack Query's `isLoading` is `true` only on initial load (no cached data). Subsequent refetches set `isFetching: true` but leave `isLoading: false`. Show skeletons only on `isLoading`, not `isFetching`, to avoid flickering on background refreshes.

### Empty State Exact Wording

The AC specifies exact copy for empty states. Use this wording precisely:
- Home: `"No runs yet — paste URLs above to get started"`
- Products tab: `"No in-scope products found for this run"`
- Excluded tab: `"All products were in scope — nothing excluded"`
- Global Ingredients: `"No ingredients yet — run a scrape to populate this table"`

### Empty States Were Pre-Added

E3-S3 and E4-S1 stories already specified these empty states. If they were implemented during those stories, this story is a verification pass. If they weren't, implement them now. Either way, this story closes when all four empty states are verified working.
