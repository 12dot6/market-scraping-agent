import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { ProductResult } from "@/lib/api";

interface AggregatedIngredient {
  name: string;
  internal_name: string | null;
  count: number;
  is_dye_active: boolean;
  products: string[];
}

function aggregateIngredients(products: ProductResult[]): AggregatedIngredient[] {
  const map = new Map<string, AggregatedIngredient & { _productIds: Set<string> }>();

  for (const product of products) {
    const productLabel = product.name || product.url;
    for (const ing of product.ingredients) {
      if (!map.has(ing.name)) {
        map.set(ing.name, {
          name: ing.name,
          internal_name: ing.internal_name,
          count: 0,
          is_dye_active: ing.is_dye_active,
          products: [],
          _productIds: new Set(),
        });
      }
      const entry = map.get(ing.name)!;
      // Count each product once, even if ingredient appears multiple times in one product
      if (!entry._productIds.has(product.id)) {
        entry._productIds.add(product.id);
        entry.count += 1;
        entry.products.push(productLabel);
      }
      if (ing.is_dye_active) entry.is_dye_active = true;
    }
  }

  return [...map.values()].map(({ _productIds: _ignored, ...rest }) => rest);
}

type SortKey = "count" | "name";
type SortDir = "asc" | "desc";

interface IngredientTableProps {
  products: ProductResult[];
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
    if (dyeOnly) list = list.filter((i) => i.is_dye_active);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((i) => i.name.toLowerCase().includes(q));
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
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "count" ? "desc" : "asc");
    }
  }

  const maxCount = Math.max(...ingredients.map((i) => i.count), 1);

  return (
    <div>
      {/* Controls */}
      <div className="flex items-center gap-4 mb-4">
        <Input
          placeholder="Search ingredients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
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
        <div className="grid grid-cols-[2fr_1fr_80px_1fr] gap-2 px-4 py-2 bg-gray-50 text-xs font-semibold uppercase tracking-wider">
          <button onClick={() => toggleSort("name")} className="text-left hover:text-violet-700">
            Ingredient {sortKey === "name" ? (sortDir === "asc" ? "↑" : "↓") : ""}
          </button>
          <span>Internal Name</span>
          <button onClick={() => toggleSort("count")} className="text-left hover:text-violet-700">
            Count {sortKey === "count" ? (sortDir === "asc" ? "↑" : "↓") : ""}
          </button>
          <span>Frequency</span>
        </div>

        {/* Empty state */}
        {filtered.length === 0 && (
          <p className="px-4 py-6 text-gray-400 text-sm text-center">
            No ingredients match your search
          </p>
        )}

        {/* Rows */}
        {filtered.map((ing) => (
          <Collapsible key={ing.name} open={expandedRow === ing.name}>
            <CollapsibleTrigger asChild>
              <div
                className={`grid grid-cols-[2fr_1fr_80px_1fr] gap-2 px-4 py-2 border-t cursor-pointer hover:bg-gray-50 ${
                  ing.is_dye_active
                    ? "border-l-4 border-l-amber-400"
                    : "border-l-4 border-l-transparent"
                }`}
                onClick={() =>
                  setExpandedRow(expandedRow === ing.name ? null : ing.name)
                }
              >
                <span className="text-sm font-medium">{ing.name}</span>
                <span className="text-sm text-gray-500">{ing.internal_name ?? "—"}</span>
                <span className="text-sm">{ing.count}</span>
                <div className="flex items-center">
                  <div
                    className="h-2 rounded bg-violet-500"
                    style={{
                      width: `${(ing.count / maxCount) * 100}%`,
                      minWidth: "4px",
                    }}
                  />
                </div>
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="px-4 py-2 bg-gray-50 border-t text-sm">
                <p className="text-xs font-semibold uppercase tracking-wider mb-1 text-gray-500">
                  Found in {ing.products.length} product
                  {ing.products.length !== 1 ? "s" : ""}:
                </p>
                <ul className="list-disc list-inside space-y-0.5">
                  {ing.products.map((p, i) => (
                    <li key={i} className="text-gray-500">
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            </CollapsibleContent>
          </Collapsible>
        ))}
      </div>
    </div>
  );
}
