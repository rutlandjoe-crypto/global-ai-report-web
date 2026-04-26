import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type JsonObject = { [key: string]: any };

const VIDEO_URL =
  process.env.NEXT_PUBLIC_GAI_VIDEO_URL ||
  "https://www.youtube.com/embed/2ePf9rue1Ao"; // fallback AI stream

function readLatestReport(): JsonObject {
  const filePath = path.join(process.cwd(), "public", "latest_report.json");

  try {
    if (!fs.existsSync(filePath)) {
      return fallbackReport("Latest report file not found.", "Add public/latest_report.json to display live data.");
    }

    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch {
    return fallbackReport("Latest report could not be loaded.", "Check public/latest_report.json for valid JSON formatting.");
  }
}

function fallbackReport(headline: string, snapshot: string): JsonObject {
  return {
    title: "GLOBAL AI REPORT",
    generated_date: new Date().toLocaleString("en-US", {
      timeZone: "America/New_York",
    }),
    headline,
    snapshot,
    key_storylines: [],
    sections: [],
  };
}

function asArray(value: any): any[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === "object") return Object.values(value);
  return [];
}

function text(value: any, fallback = ""): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return fallback;
  return String(value);
}

function getUpdatedAt(report: JsonObject): string {
  return (
    text(report.updated_at) ||
    text(report.generated_at) ||
    text(report.generated_date) ||
    text(report.published_at) ||
    new Date().toLocaleString("en-US", { timeZone: "America/New_York" })
  );
}

export default function Home() {
  const report = readLatestReport();

  const title = text(report.title, "GLOBAL AI REPORT");
  const headline = text(report.headline, "AI briefing loading.");
  const snapshot = text(report.snapshot || report.body, "Latest AI intelligence will appear here.");
  const updatedAt = getUpdatedAt(report);

  const keyStorylines = asArray(report.key_storylines || report.key_points || report.storylines);
  const sections = asArray(report.sections);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <div className="mx-auto max-w-7xl px-5 py-6">
        <header className="rounded-3xl bg-white p-6 shadow-sm border border-slate-200">
          <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
            
            {/* LEFT SIDE */}
            <div>
              <p className="text-sm font-bold tracking-[0.25em] text-blue-400">
                BUILT FOR JOURNALISTS, BY A JOURNALIST
              </p>

              <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950 md:text-6xl">
                {title}
              </h1>

              <p className="mt-3 text-sm font-semibold text-red-700">
                Updated: {updatedAt} ET
              </p>

              <h2 className="mt-6 text-2xl font-extrabold leading-tight text-slate-900 md:text-3xl">
                {headline}
              </h2>

              <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-700">
                {snapshot}
              </p>

              <div className="mt-6 flex flex-wrap gap-3">
                <a
                  href="https://globalsportsreport.substack.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full bg-blue-700 px-5 py-3 text-sm font-bold text-white shadow-sm hover:bg-blue-800"
                >
                  Read the Network Briefing
                </a>

                <a
                  href="https://x.com/GlobalSportsRp"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-900 hover:bg-slate-50"
                >
                  Follow @GlobalSportsRp
                </a>
              </div>
            </div>

            {/* RIGHT SIDE VIDEO */}
            <aside className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-sm">
              <p className="text-xs font-bold tracking-[0.25em] text-blue-300">
                LIVE AI WATCH
              </p>

              <div className="mt-4 rounded-2xl overflow-hidden aspect-video">
                <iframe
                  src={`${VIDEO_URL}?autoplay=1&mute=1`}
                  title="AI Live Video"
                  allow="autoplay; encrypted-media"
                  allowFullScreen
                  className="w-full h-full"
                />
              </div>
            </aside>
          </div>
        </header>

        {/* REST STAYS SAME */}
        <section className="mt-6 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
          <aside className="rounded-3xl bg-white p-6 shadow-sm border border-slate-200">
            <p className="text-sm font-black tracking-[0.2em] text-blue-700">
              KEY STORYLINES
            </p>

            <div className="mt-5 space-y-4">
              {keyStorylines.length > 0 ? (
                keyStorylines.map((item, index) => (
                  <div key={index} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-sm font-bold leading-6 text-slate-800">
                      {text(item)}
                    </p>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-bold leading-6 text-slate-800">
                    Key storylines will populate after the next AI report update.
                  </p>
                </div>
              )}
            </div>
          </aside>

          <section className="space-y-6">
            {sections.length > 0 ? (
              sections.map((section, index) => {
                const sectionTitle = text(section.title || section.name || section.category, `AI Section ${index + 1}`);
                const sectionHeadline = text(section.headline);
                const sectionSnapshot = text(section.snapshot || section.summary || section.body);
                const sectionItems = asArray(section.items || section.key_storylines || section.points);

                return (
                  <article key={index} className="rounded-3xl bg-white p-6 shadow-sm border border-slate-200">
                    <p className="text-xs font-black tracking-[0.25em] text-red-700">
                      GLOBAL AI REPORT
                    </p>

                    <h3 className="mt-3 text-2xl font-black text-slate-950">
                      {sectionTitle}
                    </h3>

                    {sectionHeadline && (
                      <h4 className="mt-4 text-xl font-extrabold text-slate-900">
                        {sectionHeadline}
                      </h4>
                    )}

                    {sectionSnapshot && (
                      <p className="mt-4 whitespace-pre-line text-base leading-8 text-slate-700">
                        {sectionSnapshot}
                      </p>
                    )}
                  </article>
                );
              })
            ) : (
              <article className="rounded-3xl bg-white p-6 shadow-sm border border-slate-200">
                <p className="text-xs font-black tracking-[0.25em] text-red-700">
                  GLOBAL AI REPORT
                </p>

                <h3 className="mt-3 text-2xl font-black text-slate-950">
                  AI briefing ready for content
                </h3>

                <p className="mt-4 text-base leading-8 text-slate-700">
                  Once the automated AI report writes to public/latest_report.json,
                  sections will display here.
                </p>
              </article>
            )}
          </section>
        </section>

        <footer className="mt-8 rounded-3xl bg-slate-950 p-6 text-center text-sm font-semibold text-slate-300">
          Global AI Report · Part of the GSR Network · Built for journalists, by a journalist.
        </footer>
      </div>
    </main>
  );
}