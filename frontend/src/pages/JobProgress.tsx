import { useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSSE } from "@/lib/sse";
import { LiveFeed } from "@/components/LiveFeed";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: "green" | "amber" | "red";
}) {
  const colorMap: Record<string, string> = {
    green: "text-green-600",
    amber: "text-amber-600",
    red: "text-red-600",
  };
  return (
    <div className="bg-gray-50 rounded-lg p-4 text-center border border-gray-200">
      <p className={cn("text-2xl font-bold", color ? colorMap[color] : "text-gray-800")}>
        {value}
      </p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

export default function JobProgress() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { events, isComplete, isConnecting } = useSSE(jobId!);
  const startTime = useRef(Date.now());

  // Derive progress from most recent product_done event
  const lastProgress = [...events].reverse().find((e) => e.type === "product_done")?.progress;
  const done = lastProgress?.done ?? 0;
  const total = lastProgress?.total ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const inScopeCount = events.filter((e) => e.type === "product_done" && e.in_scope).length;
  const excludedCount = events.filter((e) => e.type === "product_done" && !e.in_scope).length;
  const errorCount = events.filter((e) => e.type === "error").length;

  const elapsed = (Date.now() - startTime.current) / 1000;
  const avgPerProduct = done > 0 ? elapsed / done : 0;
  const remainingSec = avgPerProduct * (total - done);

  const statusText = isConnecting
    ? "Connecting..."
    : isComplete
    ? "Complete"
    : "Running — processing products...";

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">{statusText}</h1>
      <p className="text-sm text-gray-400 mb-4">Job {jobId}</p>

      <Progress value={pct} className="h-3 my-4" />
      <p className="text-sm text-gray-700">
        {done}/{total} products ({pct}%)
      </p>
      {!isComplete && done > 0 && (
        <p className="text-sm text-gray-400 mt-1">
          ~{formatDuration(remainingSec)} remaining
        </p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
        <StatCard label="In Scope" value={inScopeCount} color="green" />
        <StatCard label="Excluded" value={excludedCount} color="amber" />
        <StatCard label="Errors" value={errorCount} color="red" />
        <StatCard label="Avg s/product" value={avgPerProduct.toFixed(1)} />
      </div>

      <LiveFeed events={events} />

      {isComplete && (
        <Button onClick={() => navigate(`/results/${jobId}`)} className="mt-6">
          View Results →
        </Button>
      )}
    </div>
  );
}
