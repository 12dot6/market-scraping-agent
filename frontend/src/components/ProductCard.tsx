import { useState } from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { DyeActiveBadge } from "@/components/DyeActiveBadge";
import { ScopeBadge } from "@/components/ScopeBadge";
import type { IngredientItem, ProductResult } from "@/lib/api";

const COLLAPSE_THRESHOLD = 8;

interface ProductCardProps {
  product: ProductResult;
}

export function ProductCard({ product }: ProductCardProps) {
  const componentMap = new Map<string, IngredientItem[]>();
  for (const ing of product.ingredients) {
    if (!componentMap.has(ing.component)) componentMap.set(ing.component, []);
    componentMap.get(ing.component)!.push(ing);
  }

  const dyeActives = product.ingredients.filter((i) => i.is_dye_active);

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-base hover:underline text-gray-900"
            >
              {product.name || product.url}
            </a>
            {dyeActives.length > 0 && (
              <p className="text-sm text-amber-600 mt-1">
                ⚠️ Dye actives: {dyeActives.map((d) => d.name).join(", ")}
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
          <p className="text-sm text-gray-400 italic">No ingredients listed</p>
        )}
      </CardContent>
    </Card>
  );
}

function ComponentSection({
  name,
  ingredients,
}: {
  name: string;
  ingredients: IngredientItem[];
}) {
  const [expanded, setExpanded] = useState(false);
  const showToggle = ingredients.length > COLLAPSE_THRESHOLD;
  const visible =
    showToggle && !expanded ? ingredients.slice(0, COLLAPSE_THRESHOLD) : ingredients;

  return (
    <div className="mb-4">
      {/* Skip "All" header for single-component products — it's redundant */}
      {name !== "All" && (
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
          {name}
        </h4>
      )}
      <div className="flex flex-wrap gap-1 leading-relaxed">
        {visible.map((ing, i) => (
          <IngredientChip
            key={i}
            ingredient={ing}
            isLast={i === visible.length - 1}
          />
        ))}
      </div>
      {showToggle && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(!expanded)}
          className="mt-1 text-xs"
        >
          {expanded ? "Show less" : `Show all ${ingredients.length} ingredients`}
        </Button>
      )}
    </div>
  );
}

function IngredientChip({
  ingredient,
  isLast,
}: {
  ingredient: IngredientItem;
  isLast: boolean;
}) {
  const chip = (
    <span
      className={
        ingredient.internal_name
          ? "underline decoration-dotted cursor-help text-sm"
          : "text-sm"
      }
    >
      {ingredient.name}
    </span>
  );

  const wrapped = ingredient.internal_name ? (
    <Tooltip>
      <TooltipTrigger asChild>{chip}</TooltipTrigger>
      <TooltipContent>Internal: {ingredient.internal_name}</TooltipContent>
    </Tooltip>
  ) : (
    chip
  );

  if (ingredient.is_dye_active) {
    return (
      <span className="inline-flex items-center gap-1 mr-1">
        {wrapped}
        <DyeActiveBadge />
        {!isLast && <span className="text-gray-400">,</span>}
      </span>
    );
  }

  return (
    <span className="mr-1 text-sm text-gray-700">
      {wrapped}
      {!isLast && ","}
    </span>
  );
}
