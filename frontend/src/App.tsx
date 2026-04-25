import { Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import JobProgress from "@/pages/JobProgress";
import { TooltipProvider } from "@/components/ui/tooltip";

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-gray-400 text-lg">{title} — coming soon</p>
    </div>
  );
}

export default function App() {
  return (
    <TooltipProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/jobs/:jobId" element={<JobProgress />} />
        <Route path="/results/:jobId" element={<PlaceholderPage title="Run Results" />} />
        <Route path="/results" element={<PlaceholderPage title="Ingredients" />} />
      </Routes>
    </TooltipProvider>
  );
}
