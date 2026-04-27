import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type JsonObject = { [key: string]: any };

// ✅ CLEAN VIDEO (NO PARAM BREAK)
const VIDEO_URL = "https://www.youtube.com/embed/21X5lGlDOfg";

function readReport(): JsonObject {
  try {
    const filePath = path.join(process.cwd(), "public", "latest_report.json");
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch {
    return {
      site: "Global AI Report",
      brand: "Built for journalists, by a journalist.",
      headline: "AI Report Loading",
      snapshot: "Latest AI intelligence will appear here.",
      sections: [],
    };
  }
}

function asText(v: any): string {
  if (v === null || v === undefined) return "";
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

// ✅ FIX: HANDLE OBJECT + ARRAY
function getSections(report: JsonObject): any[] {
  if (Array.isArray(report.sections)) return report.sections;

  if (report.sections && typeof report.sections === "object") {
    return Object.values(report.sections);
  }

  return [];
}

function Card({ section }: { section: any }) {
  return (
    <article className="rounded-3xl bg-white p-6 shadow-xl">
      <span className="text-xs font-black uppercase tracking-widest text-blue-600">
        {section.title}
      </span>

      <h2 className="mt-3 text-2xl font-black text-slate-900">
        {section.headline}
      </h2>

      {section.snapshot && (
        <p className="mt-4 text-base leading-7 text-slate-700">
          {section.snapshot}
        </p>
      )}

      {section.key_storylines?.length > 0 && (
        <div className="mt-5 space-y-3">
          {section.key_storylines.map((item: string, i: number) => (
            <div
              key={i}
              className="border-l-4 border-blue-600 bg-slate-50 px-4 py-3 text-sm font-semibold"
            >
              {item}
            </div>
          ))}
        </div>
      )}
    </article>
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
      <div className="mx-auto max-w-7xl px-5 py-6">

        <header className="grid gap-8 border-b border-neutral-800 pb-10 lg:grid-cols-[1.2fr_0.8fr]">

          <div>
            <div className="mb-4 flex gap-3">
              <span className="bg-blue-700 px-4 py-2 text-xs font-black uppercase tracking-widest">
                GLOBAL AI REPORT
              </span>

              <span className="border border-neutral-600 px-4 py-2 text-xs font-black uppercase tracking-widest">
                BUILT FOR JOURNALISTS
              </span>
            </div>

            <h1 className="text-5xl font-black leading-tight">
              {headline}
            </h1>

            <p className="mt-5 text-lg text-neutral-300 max-w-3xl">
              {snapshot}
            </p>

            <div className="mt-5 flex gap-3">
              <span className="bg-white text-black px-4 py-2 text-xs font-bold rounded-full">
                UPDATED {updated}
              </span>

              <span className="border border-blue-500 px-4 py-2 text-xs font-bold rounded-full text-blue-300">
                {sections.length} REPORTS
              </span>
            </div>
          </div>

          {/* ✅ FIXED VIDEO */}
          <div className="rounded-3xl bg-neutral-900 p-5">
            <div className="text-xs font-black uppercase text-blue-400 mb-2">
              LIVE AI VIDEO
            </div>

            <div className="aspect-video rounded-xl overflow-hidden bg-black">
<iframe
  src={`${VIDEO_URL}?autoplay=1&mute=1`}
  title="Live Video"
  allow="autoplay; encrypted-media"
  allowFullScreen
  className="w-full h-full rounded-2xl"
/>
            </div>

            <a
              href="https://www.youtube.com/results?search_query=artificial+intelligence+news"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block text-xs text-blue-400 underline"
            >
              Open AI news stream
            </a>
          </div>
        </header>

        <section className="grid gap-4 py-6 md:grid-cols-2 lg:grid-cols-4">
          {keyStorylines.slice(0, 4).map((s, i) => (
            <div key={i} className="rounded-2xl border border-neutral-800 p-4">
              <p className="text-sm font-semibold">{s}</p>
            </div>
          ))}
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          {sections.map((s: any, i: number) => (
            <Card key={i} section={s} />
          ))}
        </section>

        <footer className="mt-10 text-center text-sm text-neutral-400">
          Global AI Report · GSR Network
        </footer>
      </div>
    </main>
  );
}