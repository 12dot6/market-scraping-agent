import { useRef } from "react";
import { Button } from "@/components/ui/button";

interface FileUploadProps {
  onParsed: (urls: string[]) => void;
}

function parseInputFile(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith("#"));
}

export function FileUpload({ onParsed }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      onParsed(parseInputFile(text));
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  return (
    <>
      <input
        type="file"
        accept=".txt"
        style={{ display: "none" }}
        ref={inputRef}
        onChange={handleChange}
      />
      <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
        Upload input.txt
      </Button>
    </>
  );
}
