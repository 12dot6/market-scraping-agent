import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

interface UrlInputProps {
  value: string;
  onChange: (v: string) => void;
  invalidUrls: string[];
}

export function parseUrls(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
}

export function extractDomains(urls: string[]): string[] {
  const domains = new Set<string>();
  for (const url of urls) {
    try {
      domains.add(new URL(url).hostname.replace("www.", ""));
    } catch {
      // skip invalid
    }
  }
  return [...domains];
}

export function validateUrls(urls: string[]): string[] {
  return urls.filter((u) => {
    try {
      new URL(u);
      return false;
    } catch {
      return true;
    }
  });
}

export function UrlInput({ value, onChange, invalidUrls }: UrlInputProps) {
  const urls = parseUrls(value);
  const domains = extractDomains(urls);

  return (
    <div className="space-y-2">
      <Textarea
        className="min-h-[120px] font-mono text-sm"
        placeholder="Paste one URL per line…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={6}
      />
      {invalidUrls.length > 0 && (
        <p className="text-sm text-red-600">
          {invalidUrls.length} invalid URL{invalidUrls.length > 1 ? "s" : ""}:{" "}
          {invalidUrls.slice(0, 3).join(", ")}
          {invalidUrls.length > 3 ? ` +${invalidUrls.length - 3} more` : ""}
        </p>
      )}
      {domains.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {domains.map((d) => (
            <Badge key={d} variant="secondary">
              {d}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
