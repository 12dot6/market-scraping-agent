import { Badge } from "@/components/ui/badge";

interface ScopeBadgeProps {
  inScope: boolean;
}

export function ScopeBadge({ inScope }: ScopeBadgeProps) {
  if (inScope) {
    return (
      <Badge className="bg-emerald-100 text-emerald-800 border border-emerald-300">
        🟢 In scope
      </Badge>
    );
  }
  return <Badge variant="secondary">Excluded</Badge>;
}
