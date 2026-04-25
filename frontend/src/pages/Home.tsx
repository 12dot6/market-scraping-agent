import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { UrlInput, parseUrls, validateUrls } from "@/components/UrlInput";
import { FileUpload } from "@/components/FileUpload";
import { JobCard } from "@/components/JobCard";
import { getJobs, postJob, type JobSummary } from "@/lib/api";

const TERMINAL = new Set<JobSummary["status"]>(["complete", "failed"]);

export default function Home() {
  const [urlText, setUrlText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const { data: recentJobs } = useQuery({
    queryKey: ["jobs"],
    queryFn: getJobs,
    refetchInterval: (query) => {
      const jobs = query.state.data;
      if (!jobs || jobs.length === 0) return 3000;
      return jobs.every((j) => TERMINAL.has(j.status)) ? false : 3000;
    },
  });

  const urls = parseUrls(urlText);
  const invalidUrls = validateUrls(urls);
  const canSubmit = urls.length > 0 && invalidUrls.length === 0 && !submitting;

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const { job_id } = await postJob(urls);
      navigate(`/jobs/${job_id}`);
    } catch {
      // error handling in E5-S2
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Formulation Wiki</h1>
        <p className="mt-1 text-sm text-gray-500">
          Paste product URLs to scrape and classify hair dye ingredients.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        <h2 className="text-base font-semibold text-gray-800">New Scraping Job</h2>

        <UrlInput value={urlText} onChange={setUrlText} invalidUrls={invalidUrls} />

        <div className="flex items-center gap-3 pt-1">
          <Button disabled={!canSubmit} onClick={handleSubmit} className="flex-shrink-0">
            {submitting ? "Starting…" : "Start Scraping"}
          </Button>
          <FileUpload onParsed={(parsed) => setUrlText(parsed.join("\n"))} />
          {urls.length > 0 && (
            <span className="text-sm text-gray-400 ml-auto">
              {urls.length} URL{urls.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Recent Runs</h2>
        {recentJobs && recentJobs.length > 0 ? (
          recentJobs.map((job) => <JobCard key={job.id} job={job} />)
        ) : (
          <p className="text-sm text-gray-400 italic">No runs yet.</p>
        )}
      </div>
    </div>
  );
}
