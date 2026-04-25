import { Badge } from "@/components/ui/badge";
import type { SSEEvent } from "@/lib/sse";

interface LiveFeedProps {
  events: SSEEvent[];
}

export function LiveFeed({ events }: LiveFeedProps) {
  const feedEvents = events.filter(
    (e) => e.type === "product_done" || e.type === "error"
  );

  return (
    <div className="border border-gray-200 rounded-lg overflow-y-auto max-h-80">
      {feedEvents.length === 0 && (
        <p className="p-4 text-gray-400 text-sm">Waiting for first product...</p>
      )}
      {feedEvents.map((e, i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-4 py-2 border-b border-gray-100 last:border-0"
        >
          {e.type === "error" ? (
            <span className="text-red-500 text-sm">
              ⚠ Error: {e.url ?? e.message}
            </span>
          ) : (
            <>
              <span>{e.in_scope ? "🟢" : "🔴"}</span>
              <span className="text-sm flex-1 truncate">{e.name}</span>
              <Badge variant={e.in_scope ? "green" : "secondary"}>
                {e.in_scope ? "In scope" : "Excluded"}
              </Badge>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
