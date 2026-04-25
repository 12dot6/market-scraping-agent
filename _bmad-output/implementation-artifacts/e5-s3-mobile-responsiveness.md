# Story E5-S3: Mobile Responsiveness

**Epic:** E5 — Polish & Quality  
**Story ID:** E5-S3  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a user on a tablet or phone  
I want the app to be usable on smaller screens  
So that I can check job status or browse results away from my desk

---

## Acceptance Criteria

- [ ] Home screen: textarea and submit button stack vertically on mobile
- [ ] JobProgress: Live Feed and Stats panels stack vertically below progress bar
- [ ] RunResults: tabs scroll horizontally if needed; ProductCard readable at 375px width
- [ ] IngredientTable: columns collapse gracefully (hide frequency bar on mobile)
- [ ] Navigation header collapses to hamburger menu below 768px

---

## Technical Requirements

### Breakpoints (Tailwind Defaults)

- Mobile: `< 768px` (default, no prefix)
- Tablet: `md:` (`768px+`)
- Desktop: `lg:` (`1024px+`)

### Per-Component Changes

**Home.tsx — Stack vertically on mobile:**
```tsx
// URL input area: full width on all screens
<div className="w-full">
  <Textarea className="w-full" />
</div>
// Domain chips + submit: stacked on mobile, row on desktop
<div className="flex flex-col md:flex-row md:items-center gap-3 mt-3">
  <div className="flex flex-wrap gap-1 flex-1">{/* chips */}</div>
  <Button className="w-full md:w-auto">Start Scraping</Button>
</div>
```

**JobProgress.tsx — Stats + LiveFeed stacked on mobile:**
```tsx
// Stats grid: 2 cols on mobile, 4 on desktop
<div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
  {/* stat cards */}
</div>
// LiveFeed: full width on all screens (already is)
```

**RunResults.tsx — Tabs scroll on mobile:**
```tsx
// Wrap TabsList in horizontal scroll container
<div className="overflow-x-auto">
  <TabsList className="w-max">
    <TabsTrigger value="products">Products ({inScopeProducts.length})</TabsTrigger>
    <TabsTrigger value="ingredients">Ingredients</TabsTrigger>
    <TabsTrigger value="excluded">Excluded ({excludedProducts.length})</TabsTrigger>
  </TabsList>
</div>
```

**ProductCard.tsx — Readable at 375px:**
```tsx
// Card header: stack on mobile
<div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
  <div className="flex-1 min-w-0">
    <a className="font-semibold text-sm sm:text-base break-words">{product.name}</a>
  </div>
  <ScopeBadge inScope={product.in_scope} />
</div>
// Ingredient chips: flex-wrap (already wraps)
// Component header: smaller text on mobile (already text-xs)
```

**IngredientTable.tsx — Hide frequency bar on mobile:**
```tsx
// Grid with responsive columns
<div className="grid grid-cols-[2fr_1fr_60px] md:grid-cols-[2fr_1fr_80px_1fr] gap-2 px-4 py-2 bg-muted ...">
  <span>Ingredient</span>
  <span>Internal Name</span>
  <span>Count</span>
  <span className="hidden md:block">Frequency</span>  {/* hide on mobile */}
</div>
// Same pattern for each row
<div className="grid grid-cols-[2fr_1fr_60px] md:grid-cols-[2fr_1fr_80px_1fr] ...">
  {/* ... */}
  <div className="hidden md:flex items-center">  {/* frequency bar — hidden on mobile */}
    <div className="h-2 rounded bg-violet-500" style={{ width: `...` }} />
  </div>
</div>
```

**Navigation Header — Hamburger on mobile:**

```tsx
// Create frontend/src/components/AppHeader.tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";

export function AppHeader() {
  const [open, setOpen] = useState(false);

  const navLinks = [
    { to: "/", label: "Home" },
    { to: "/results", label: "Ingredients" },
  ];

  return (
    <header className="border-b bg-white sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="font-semibold text-violet-700">Formulation Wiki</Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          {navLinks.map(l => (
            <Link key={l.to} to={l.to} className="text-sm text-muted-foreground hover:text-foreground">
              {l.label}
            </Link>
          ))}
        </nav>

        {/* Mobile hamburger */}
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-56">
            <nav className="flex flex-col gap-4 mt-8">
              {navLinks.map(l => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="text-base"
                  onClick={() => setOpen(false)}
                >
                  {l.label}
                </Link>
              ))}
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
```

Add `<AppHeader />` at the top of `App.tsx` (outside Routes, inside Router).

### Test Viewports

Test at:
- 375px (iPhone SE) — smallest target
- 768px (iPad portrait) — tablet breakpoint
- 1024px (desktop minimum)

Use browser DevTools responsive mode or real devices.

---

## Implementation Tasks

- [ ] Audit all four screens with Tailwind responsive prefixes (`sm:`, `md:`)
- [ ] Test at 375px (iPhone SE) and 768px (iPad) viewport widths
- [ ] Add responsive nav (Shadcn Sheet for mobile drawer)
- [ ] Hide frequency bar column in IngredientTable on mobile
- [ ] Stack Stats + LiveFeed vertically on mobile in JobProgress

---

## Dev Notes

### Mobile-First vs Desktop-First

The UX spec says "desktop-first, fully responsive." Tailwind defaults to mobile styles (no prefix), with `md:` overrides for tablet/desktop. Use the default (no prefix) for mobile layout, then `md:` to adapt for larger screens.

### Sheet Component for Drawer Nav

Shadcn `<Sheet>` renders a slide-in panel from the side. `side="right"` opens from the right edge. Close the sheet (`setOpen(false)`) when a nav link is clicked to avoid leaving the drawer open after navigation.

### IngredientTable: Column Grid Must Match

When hiding the frequency bar column on mobile, the CSS grid `grid-cols` definition must match for both the header row and data rows. The header and each data row use the same `grid-cols-[2fr_1fr_60px] md:grid-cols-[2fr_1fr_80px_1fr]` class to stay aligned.

### ProductCard: Text Truncation

At 375px, long product names can overflow. Use `break-words` or `truncate` (with `overflow-hidden`) on the name element. `break-words` is preferred since the full name is useful; `truncate` cuts it with ellipsis. Use `break-words` for names and `truncate` for URLs.

### ExportBar: Stack on Mobile

The ExportBar in RunResults has stats text + download buttons side by side on desktop. On mobile, stack them:
```tsx
<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 ...">
  <div>{/* stats */}</div>
  <div className="flex flex-wrap gap-2">{/* buttons */}</div>
</div>
```

### No Complex Touch Gestures

The UX spec doesn't require swipe navigation or touch-specific gestures. Tabs scroll horizontally with standard overflow behavior — this is touch-scrollable on mobile by default. No additional JS needed.
