import { Link } from "react-router-dom";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { JobSummary } from "@/lib/api";

const STATUS_VARIANT: Record<JobSummary["status"], BadgeProps["variant"]> = {
  queued: "blue",
  running: "amber",
  complete: "green",
  failed: "red",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface JobCardProps {
  job: JobSummary;
}

export function JobCard({ job }: JobCardProps) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4">
      <div className="space-y-1">
        <p className="text-sm text-gray-500">{formatDate(job.created_at)}</p>
        <p className="text-sm font-medium text-gray-800">
          {job.in_scope} product{job.in_scope !== 1 ? "s" : ""} in scope
          {job.url_count > 0 && (
            <span className="ml-2 text-gray-400 font-normal">
              ({job.url_count} URL{job.url_count !== 1 ? "s" : ""})
            </span>
          )}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant={STATUS_VARIANT[job.status]}>{job.status}</Badge>
        <Link
          to={`/results/${job.id}`}
          className="text-sm font-medium text-[#7C3AED] hover:underline"
        >
          View
        </Link>
      </div>
    </div>
  );
}
