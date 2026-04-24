import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Global AI Report",
  description: "Automated AI journalism support for the modern newsroom.",
};

type JsonObject = { [key: string]: any };

const VIDEO_URL =
  process.env.NEXT_PUBLIC_GAI_VIDEO_URL ||
  "https://www.youtube.com/embed/live_stream?channel=UCUMZ7gohGI9HcU9VNsr2FJQ&autoplay=1&mute=1";

function readLatestReport(): JsonObject {
  const filePath = path.join(process.cwd(), "public", "latest_report.json");

  try {
    if (!fs.existsSync(filePath)) {
      return {
        title: "GLOBAL AI REPORT",
        generated_date: new Date().toLocaleString("en-US", {
          timeZone: "America/New_York",
        }),
        headline: "Latest report file not found.",
        snapshot: "Add public/latest_report.json to display live data.",
        key_storylines: [],
        sections: [],
      };
    }

    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = JSON.parse(raw);

    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (e) {
    return {
      title: "GLOBAL AI REPORT",
      generated_date: new Date().toLocaleString("en-US", {
        timeZone: "America/New_York",
      }),
      headline: "Error loading report.",
      snapshot: "Check public/latest_report.json.",
      key_storylines: [],
      sections: [],
    };
  }
}

function asText(value: any): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function asArray(value: any): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") return item;
      if (typeof item === "number" || typeof item === "boolean") return String(item);
      if (item && typeof item === "object") {
        return Object.entries(item)
          .map(([key, val]) => `${cleanLabel(key)}: ${asText(val)}`)
          .filter(Boolean)
          .join(" | ");
      }
      return "";
    })
    .filter(Boolean);
}

function cleanLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim();
}

function SectionCard({ section }: { section: JsonObject }) {
  const title = asText(section.title) || asText(section.name) || "AI Coverage";
  const headline = asText(section.headline);
  const snapshot = asText(section.snapshot);
  const keyStorylines = asArray(section.key_storylines || section.content || section.items);

  return (
    <section className="rounded-3xl border border-blue-900/40 bg-[#111827] p-5 shadow-2xl shadow-black/30">
      <div className="mb-4 flex items-center justify-between gap-3 border-b border-blue-900/40 pb-3">
        <h2 className="text-lg font-bold uppercase tracking-[0.18em] text-white">
          {title}
        </h2>
        <span className="rounded-full border border-blue-500/30 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-blue-300">
          Live Desk
        </span>
      </div>

      <div className="space-y-4">
        {headline ? (
          <div className="rounded-2xl border border-blue-900/30 bg-[#0a0f1c] p-4">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400">
              Headline
            </div>
            <p className="text-sm leading-6 text-zinc-100">{headline}</p>
          </div>
        ) : null}

        {snapshot ? (
          <div className="rounded-2xl border border-blue-900/30 bg-[#0a0f1c] p-4">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400">
              Snapshot
            </div>
            <p className="text-sm leading-6 text-zinc-300">{snapshot}</p>
          </div>
        ) : null}

        {keyStorylines.length ? (
          <div className="rounded-2xl border border-blue-900/30 bg-[#0a0f1c] p-4">
            <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400">
              Key Storylines
            </div>
            <ul className="space-y-2">
              {keyStorylines.map((item, idx) => (
                <li key={idx} className="ml-5 list-disc text-sm leading-6 text-zinc-300">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}

export default function Page() {
  const data = readLatestReport();

  const title = asText(data.title) || "GLOBAL AI REPORT";
  const generatedDate =
    asText(data.generated_date) ||
    asText(data.generated_at) ||
    asText(data.updated_at) ||
    new Date().toLocaleString("en-US", {
      timeZone: "America/New_York",
    });

  const headline = asText(data.headline);
  const snapshot = asText(data.snapshot);
  const keyStorylines = asArray(data.key_storylines);

  const sections = Array.isArray(data.sections)
    ? data.sections.filter((section: any) => section && typeof section === "object")
    : [];

  return (
    <main className="min-h-screen bg-[#0a0f1c] text-white">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <header className="mb-6 rounded-3xl border border-blue-900/40 bg-[#0f172a] p-5 shadow-2xl shadow-black/40">
          <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="space-y-4">
              <div className="inline-flex w-fit rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-400">
                AI Intelligence Desk
              </div>

              <div>
                <h1 className="text-3xl font-black uppercase tracking-[0.16em] text-white sm:text-4xl">
                  {title}
                </h1>
                <p className="mt-2 text-sm text-blue-400">Updated: {generatedDate}</p>
              </div>

              {headline ? (
                <div className="rounded-2xl border border-blue-900/40 bg-[#0a0f1c] p-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400">
                    Headline
                  </div>
                  <p className="text-base leading-7 text-zinc-100">{headline}</p>
                </div>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                {snapshot ? (
                  <div className="rounded-2xl border border-blue-900/40 bg-[#111827] p-4">
                    <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400">
                      Snapshot
                    </div>
                    <p className="text-sm leading-6 text-zinc-300">{snapshot}</p>
                  </div>
                ) : null}

                <div className="rounded-2xl border border-blue-900/40 bg-[#111827] p-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400">
                    Newsroom Note
                  </div>
                  <p className="text-sm leading-6 text-zinc-300">
                    This report is an automated summary intended to support, not replace,
                    human technology journalism.
                  </p>
                </div>
              </div>

              {keyStorylines.length ? (
                <div className="rounded-2xl border border-blue-900/40 bg-[#111827] p-4">
                  <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400">
                    Key Storylines
                  </div>
                  <ul className="space-y-2">
                    {keyStorylines.map((item, idx) => (
                      <li key={idx} className="ml-5 list-disc text-sm leading-6 text-zinc-300">
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>

            <div className="overflow-hidden rounded-3xl border border-blue-900/40 bg-[#0f172a] shadow-2xl shadow-black/40">
              <div className="border-b border-blue-900/40 px-4 py-3 text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                AI / Tech Live Video
              </div>

              <div className="aspect-video w-full bg-[#020617]">
                <iframe
                  src={VIDEO_URL}
                  title="Bloomberg Technology Live"
                  allow="autoplay; encrypted-media; picture-in-picture"
                  allowFullScreen
                  className="h-full w-full"
                />
              </div>
            </div>
          </div>
        </header>

        {sections.length ? (
          <section className="mb-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-[0.22em] text-blue-300">
                Coverage
              </h2>
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              {sections.map((section: JsonObject, idx: number) => (
                <SectionCard key={idx} section={section} />
              ))}
            </div>
          </section>
        ) : null}

        <footer className="rounded-3xl border border-blue-900/40 bg-[#0f172a] p-5 text-center shadow-2xl shadow-black/40">
          <p className="text-xs uppercase tracking-[0.22em] text-blue-400">
            Global AI Report
          </p>
          <p className="mt-2 text-sm text-zinc-400">
            Automated AI journalism support for the modern newsroom.
          </p>
        </footer>
      </div>
    </main>
  );
}