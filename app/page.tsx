import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type JsonObject = { [key: string]: any };

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
      };
    }

    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch (e) {
    return {
      title: "GLOBAL AI REPORT",
      generated_date: new Date().toLocaleString("en-US", {
        timeZone: "America/New_York",
      }),
      headline: "Error loading report.",
      snapshot: "Check JSON file.",
    };
  }
}

export default function Page() {
  const data = readLatestReport();

  return (
    <main className="min-h-screen bg-[#0a0f1c] text-white">
      <div className="mx-auto max-w-7xl px-4 py-6">

        {/* HEADER */}
        <header className="mb-6 rounded-3xl border border-blue-900/40 bg-[#0f172a] p-5">

          {/* NEW HEADER LABEL */}
          <div className="mb-4 inline-flex w-fit rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-400">
            AI Intelligence Desk
          </div>

          <h1 className="text-3xl font-bold uppercase tracking-wide">
            GLOBAL AI REPORT
          </h1>

          <p className="text-sm text-blue-400 mt-1">
            Updated: {data.generated_date}
          </p>
        </header>

        {/* TOP GRID */}
        <div className="grid gap-6 lg:grid-cols-2">

          {/* LEFT SIDE - REPORT */}
          <section className="rounded-3xl border border-blue-900/40 bg-[#111827] p-5">
            <h2 className="text-lg font-bold mb-4 text-blue-300">TOP STORIES</h2>

            <ul className="space-y-3 text-sm text-zinc-300">
              {data.sections?.[0]?.content?.map((item: string, i: number) => (
                <li key={i} className="list-disc ml-5">
                  {item}
                </li>
              ))}
            </ul>
          </section>

          {/* RIGHT SIDE - VIDEO */}
          <div className="overflow-hidden rounded-3xl border border-blue-900/40 bg-[#0f172a]">

            <div className="border-b border-blue-900/40 px-4 py-3 text-xs uppercase tracking-widest text-blue-400">
              AI / Tech Live Video
            </div>

            <div className="aspect-video w-full bg-[#020617]">
<iframe
  src="https://www.youtube.com/embed/live_stream?channel=UCUMZ7gohGI9HcU9VNsr2FJQ&autoplay=1&mute=1"
  title="Bloomberg Technology Live"
  allow="autoplay; encrypted-media; picture-in-picture"
  allowFullScreen
  className="w-full h-full"
/>
            </div>

          </div>
        </div>

      </div>
    </main>
  );
}