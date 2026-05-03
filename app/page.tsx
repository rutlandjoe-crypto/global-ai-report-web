import fs from "fs";
import path from "path";
import { headers } from "next/headers";

import EditorialStandard from "@/components/EditorialStandard";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

type AnyObj = Record<string, any>;

const SITE = {
  name: "Global AI Report",
  tagline: "Built for journalists, by a journalist.",
  topic: "AI",
  descriptor:
    "Global AI Report tracks artificial intelligence across business, policy, infrastructure and innovation, delivering journalist-ready signals on the fastest-moving sector in the global economy.",
};

const TOOLKIT = [
  ["OpenAI", "https://openai.com"],
  ["Google AI", "https://ai.google"],
  ["NVIDIA News", "https://www.nvidia.com/en-us/news/"],
  ["Hugging Face", "https://huggingface.co"],
  ["MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/"],
];

const GSR_NETWORK = [
  ["Sports", "https://globalsportsreport.com"],
  ["AI", "https://globalaireport.news"],
  ["Politics", "https://globalpoliticsreport.com"],
  ["Entertainment", "https://globalentertainmentreport.com"],
];

function readReportFromFile(): AnyObj {
  try {
    const file = path.join(process.cwd(), "public", "latest_report.json");
    const raw = fs.readFileSync(file, "utf8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

async function readReport(): Promise<AnyObj> {
  const fallback = readReportFromFile();

  try {
    const h = await headers();
    const host = h.get("host");

    if (!host) return fallback;

    const protocol = host.includes("localhost") ? "http" : "https";
    const url = `${protocol}://${host}/latest_report.json?cacheBust=${Date.now()}`;

    const res = await fetch(url, {
      cache: "no-store",
      next: { revalidate: 0 },
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
        Pragma: "no-cache",
        Expires: "0",
      },
    });

    if (!res.ok) return fallback;

    const data = await res.json();
    return data && typeof data === "object" ? data : fallback;
  } catch {
    return fallback;
  }
}

function cleanText(value: any): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean).join(" • ");
  if (typeof value === "object") {
    return Object.values(value).map(cleanText).filter(Boolean).join(" • ");
  }

  return String(value)
    .replace(/â€”/g, "—")
    .replace(/â€“/g, "–")
    .replace(/â€˜/g, "'")
    .replace(/â€™/g, "'")
    .replace(/â€œ/g, '"')
    .replace(/â€�/g, '"')
    .replace(/Â/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function asList(value: any): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean);
  if (typeof value === "object") return Object.values(value).map(cleanText).filter(Boolean);

  return cleanText(value)
    .split(/\n|•|\|/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function getStories(report: AnyObj): AnyObj[] {
  const candidates =
    report.sections ||
    report.stories ||
    report.news ||
    report.headlines ||
    report.items ||
    report.articles ||
    [];

  if (Array.isArray(candidates)) return candidates.filter(Boolean);

  if (typeof candidates === "object") {
    return Object.values(candidates).flatMap((item: any) =>
      Array.isArray(item) ? item : [item]
    );
  }

  return [];
}

function getSpotlightStories(report: AnyObj, key: "live_newsroom" | "editor_signals"): AnyObj[] {
  const raw = report[key];
  if (!Array.isArray(raw)) return [];
  return raw.filter((item) => item && typeof item === "object");
}

function storyTitle(story: AnyObj, index: number): string {
  return (
    cleanText(story.headline) ||
    cleanText(story.title) ||
    cleanText(story.name) ||
    `AI Storyline ${index + 1}`
  );
}

function storyUrl(story: AnyObj): string {
  const url = cleanText(story.url) || cleanText(story.link) || cleanText(story.source_url) || "#";
  return url.startsWith("http://") || url.startsWith("https://") ? url : "#";
}

function storySummary(story: AnyObj): string {
  return (
    cleanText(story.summary) ||
    cleanText(story.snapshot) ||
    cleanText(story.description) ||
    cleanText(story.body) ||
    "AI development flagged for newsroom monitoring."
  );
}

function storyLabel(story: AnyObj): string {
  return cleanText(story.label) || cleanText(story.source) || "AI Watch";
}

function storySignal(story: AnyObj, index: number): string {
  return `${storyLabel(story)}: ${storyTitle(story, index)}`;
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-black uppercase tracking-wide text-blue-800">
        {title}
      </h2>
      {children}
    </section>
  );
}

function LineList({ items }: { items: string[] }) {
  const safe = items.filter(Boolean).slice(0, 8);

  if (!safe.length) {
    return <p className="text-sm leading-6 text-slate-700">No current items available.</p>;
  }

  return (
    <div className="space-y-2">
      {safe.map((item, i) => (
        <p key={i} className="border-b border-slate-100 pb-2 text-sm leading-6 text-slate-800">
          {item}
        </p>
      ))}
    </div>
  );
}

function NewsroomBriefing({ items }: { items: string[] }) {
  const safe = items.filter(Boolean).slice(0, 6);

  return (
    <div className="rounded-2xl border border-slate-300 bg-white p-5 shadow-sm">
      <p className="mb-3 text-xs font-black uppercase tracking-wide text-blue-800">
        Live Newsroom Briefing
      </p>

      {safe.length ? (
        <div className="space-y-2">
          {safe.map((item, i) => (
            <p key={i} className="border-b border-slate-100 pb-2 text-sm leading-6 text-slate-800">
              {item}
            </p>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-slate-700">
          Monitoring major developments across AI business, models, infrastructure, policy and enterprise adoption.
        </p>
      )}
    </div>
  );
}

function StoryCard({ story, index }: { story: AnyObj; index: number }) {
  const title = storyTitle(story, index);
  const url = storyUrl(story);
  const summary = storySummary(story);

  const keyData = asList(story.key_data || story.keyData || story.data || story.metrics);
  const why = asList(story.why_it_matters || story.whyItMatters || story.why);
  const watch = asList(story.what_to_watch || story.whatToWatch || story.watch);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="mb-2 text-xs font-black uppercase tracking-wide text-blue-700">
        AI Watch
      </p>

      <h3 className="text-xl font-black leading-tight text-slate-950">
        {url !== "#" ? (
          <a href={url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-800">
            {title}
          </a>
        ) : (
          title
        )}
      </h3>

      <p className="mt-3 text-sm leading-6 text-slate-700">{summary}</p>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">Key Data</p>
          <LineList items={keyData.length ? keyData : ["No verified data point attached yet."]} />
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">Why It Matters</p>
          <LineList items={why.length ? why : ["This affects AI coverage priorities."]} />
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">What To Watch</p>
          <LineList items={watch.length ? watch : ["Monitor the next company, model, policy or market response."]} />
        </div>
      </div>
    </article>
  );
}

export default async function Page() {
  const report = await readReport();

  const headline =
    cleanText(report.headline) ||
    cleanText(report.title) ||
    "AI Newsroom Watch: Major Developments Under Review";

  const snapshot =
    cleanText(report.snapshot) ||
    cleanText(report.summary) ||
    cleanText(report.body) ||
    "A live AI briefing built for journalists tracking companies, models, infrastructure, policy and global competition.";

  const updated =
    cleanText(report.updated_at) ||
    cleanText(report.generated_at) ||
    cleanText(report.published_at) ||
    "Update time unavailable";

  let stories = getStories(report).filter((story) => story && typeof story === "object");

  if (!stories.length) {
    stories = [
      {
        headline,
        summary: snapshot,
        key_data: ["Latest AI report generated from live feeds."],
        why_it_matters: ["Editors need fast clarity in a rapidly evolving sector."],
        what_to_watch: ["Next model release, policy move, infrastructure signal or company response."],
      },
    ];
  }

  const leadStories = stories.slice(0, 10);

  const signals = asList(
    report.key_storylines ||
      report.keyStorylines ||
      report.signals ||
      report.toplines ||
      report.takeaways
  );

  const liveNewsroomStories = getSpotlightStories(report, "live_newsroom");
  const editorSignalStories = getSpotlightStories(report, "editor_signals");

  const liveItems = liveNewsroomStories.length
    ? liveNewsroomStories.map(storySignal)
    : signals.length
      ? signals
      : [
          "Track the strongest AI business development.",
          "Prioritize verified source links.",
          "Watch model releases, infrastructure, regulation and enterprise adoption.",
          "Monitor company moves, policy shifts and market signals.",
        ];

  const editorItems = editorSignalStories.length
    ? editorSignalStories.map(storySignal)
    : signals.length
      ? signals
      : [
          "Track the strongest AI business development.",
          "Prioritize verified source links.",
          "Watch model releases, infrastructure, regulation and enterprise adoption.",
        ];

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <div className="border-b border-blue-950 bg-blue-950 text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-5 py-2 text-xs font-bold uppercase tracking-wide">
          <span className="text-blue-200">GSR Network:</span>
          {GSR_NETWORK.map(([name, url], index) => (
            <span key={name} className="flex items-center gap-3">
              <a href={url} target="_blank" rel="noopener noreferrer" className="text-white hover:text-blue-200">
                {name}
              </a>
              {index < GSR_NETWORK.length - 1 ? <span className="text-blue-400">•</span> : null}
            </span>
          ))}
        </div>
      </div>

      <header className="border-b border-slate-300 bg-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-5 py-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-sm font-black uppercase tracking-wide text-blue-700">
              {SITE.name}
            </p>

            <h1 className="mt-3 text-4xl font-black leading-tight md:text-5xl">
              {headline}
            </h1>

            <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-700">
              {snapshot}
            </p>

            <div className="mt-5 flex flex-wrap gap-3 text-sm font-bold">
              <span className="rounded-full bg-blue-900 px-4 py-2 text-white">
                {SITE.tagline}
              </span>
              <span className="rounded-full bg-slate-200 px-4 py-2 text-slate-800">
                Updated: {updated}
              </span>
            </div>
          </div>

          <NewsroomBriefing items={liveItems} />
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[0.75fr_1.25fr]">
        <aside className="space-y-6">
          <Block title="Editor Signals">
            <LineList items={editorItems} />
          </Block>

          <Block title="Journalist Toolkit">
            <div className="space-y-2">
              {TOOLKIT.map(([name, url]) => (
                <a
                  key={name}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-blue-900 hover:bg-blue-50"
                >
                  {name}
                </a>
              ))}
            </div>
          </Block>

          <Block title="Coverage Lens">
            <LineList
              items={[
                "Company: Who gains market or platform leverage?",
                "Model: What changed in capability, safety or deployment?",
                "Infrastructure: What does this mean for chips, cloud or data centers?",
                "Policy: What regulators, courts or governments may respond?",
                "Newsroom: What should journalists verify next?",
              ]}
            />
          </Block>
        </aside>

        <section className="space-y-6">
          {leadStories.map((story, index) => (
            <StoryCard key={index} story={story} index={index} />
          ))}
        </section>
      </section>

      <footer className="border-t border-slate-300 bg-white">
        <div className="mx-auto max-w-7xl px-5 py-6">
          <p className="text-sm font-medium text-slate-700">
            © {new Date().getFullYear()} {SITE.name}. {SITE.tagline}
          </p>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-500">
            {SITE.descriptor}
          </p>
        </div>
        <EditorialStandard />
      </footer>
    </main>
  );
}