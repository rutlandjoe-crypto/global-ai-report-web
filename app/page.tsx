import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type JsonObject = { [key: string]: any };

// ✅ RELIABLE LIVE STREAM (WORKING)
const VIDEO_URL = "https://www.youtube.com/embed/21X5lGlDOfg?rel=0";

function readReport(): JsonObject {
  try {
    const filePath = path.join(process.cwd(), "public", "latest_report.json");
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch {
    return {
      headline: "AI Report Loading",
      snapshot: "",
      sections: [],
    };
  }
}

function asText(v: any): string {
  if (!v) return "";
  return String(v).trim();
}

function asList(v: any): string[] {
  if (!v) return [];

  if (Array.isArray(v)) {
    return v.map((x) => asText(x)).filter(Boolean);
  }

  if (typeof v === "string") {
    return v
      .split(/\n|•|- /)
      .map((x) => x.trim())
      .filter(Boolean);
  }

  return [];
}

function getSections(report: JsonObject): any[] {
  if (Array.isArray(report.sections)) return report.sections;
  if (report.sections && typeof report.sections === "object") {
    return Object.values(report.sections);
  }
  return [];
}

// 🔥 CLEAN NEWS LINE
function NewsLine({ item }: { item: any }) {
  const headline = asText(item.headline);
  const url = item.url || "#";
  const context = asText(item.snapshot);

  return (
    <div className="py-2 border-b border-neutral-800">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="block text-lg font-bold text-white hover:text-blue-400"
      >
        {headline}
      </a>

      {context && (
        <div className="text-sm text-neutral-400 mt-1">
          {context}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const report = readReport();

  const headline = asText(report.headline);
  const snapshot = asText(report.snapshot);
  const updated = asText(report.updated_at || report.generated_at);

  const sections = getSections(report);
  const keyStorylines = asList(report.key_storylines);

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-6xl mx-auto px-4 py-6">

        {/* HEADER */}
        <header className="border-b border-neutral-800 pb-6 mb-6">

          <div className="grid lg:grid-cols-[1.2fr_1fr] gap-6 items-start">

            {/* LEFT SIDE */}
            <div>
              <div className="text-xs uppercase font-black tracking-widest text-blue-400 mb-2">
                GLOBAL AI REPORT
              </div>

              <h1 className="text-4xl font-extrabold leading-tight">
                {headline}
              </h1>

              {snapshot && (
                <p className="text-base text-neutral-400 mt-3 max-w-2xl">
                  {snapshot}
                </p>
              )}

              <div className="text-xs text-neutral-500 mt-3">
                Updated {updated}
              </div>
            </div>

            {/* RIGHT SIDE — BIG VIDEO */}
            <div>
              <div className="text-xs font-bold mb-2 text-blue-400">
                LIVE AI COVERAGE
              </div>

              <div className="aspect-video bg-black rounded-xl overflow-hidden border border-neutral-800">
                <iframe
                  src={VIDEO_URL}
                  title="Live AI Video"
                  allow="autoplay; encrypted-media"
                  allowFullScreen
                  className="w-full h-full"
                />
              </div>

              <div className="text-xs text-neutral-500 mt-2">
                Live AI news stream
              </div>
            </div>

          </div>
        </header>

        {/* KEY STORYLINES */}
        <section className="mb-6">
          {keyStorylines.map((s, i) => (
            <div key={i} className="py-2 border-b border-neutral-800">
              <div className="text-base font-semibold text-white">
                {s}
              </div>
            </div>
          ))}
        </section>

        {/* MAIN NEWS */}
        <section>
          {sections.map((s: any, i: number) => (
            <NewsLine key={i} item={s} />
          ))}
        </section>

        {/* TOOLKIT */}
        <section className="mt-8 border-t border-neutral-800 pt-6">
          <div className="text-xs uppercase font-black text-blue-400 mb-3">
            Journalist Toolkit
          </div>

          <div className="space-y-2 text-sm">
            <a href="https://www.reuters.com" target="_blank" className="block hover:underline">Reuters</a>
            <a href="https://www.bloomberg.com" target="_blank" className="block hover:underline">Bloomberg</a>
            <a href="https://www.ft.com" target="_blank" className="block hover:underline">Financial Times</a>
            <a href="https://www.theinformation.com" target="_blank" className="block hover:underline">The Information</a>
            <a href="https://techcrunch.com" target="_blank" className="block hover:underline">TechCrunch</a>
          </div>
        </section>

      </div>
    </main>
  );
}