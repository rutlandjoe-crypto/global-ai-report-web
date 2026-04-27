import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type AnyObj = Record<string, any>;

const SITE = {
  name: "Global Politics Report",
  tagline: "Built for journalists, by a journalist.",
  topic: "Politics",
  videoUrl:
    process.env.NEXT_PUBLIC_GPR_VIDEO_URL ||
    "https://www.youtube.com/embed/1Y3FQ8F7vLE",
};

const TOOLKIT = [
  ["AP Politics", "https://apnews.com/hub/politics"],
  ["Reuters Politics", "https://www.reuters.com/world/us/"],
  ["Federal Register", "https://www.federalregister.gov/"],
  ["Congress.gov", "https://www.congress.gov/"],
  ["FEC Data", "https://www.fec.gov/data/"],
];

function readReport(): AnyObj {
  try {
    const file = path.join(process.cwd(), "public", "latest_report.json");
    const raw = fs.readFileSync(file, "utf8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function cleanText(value: any): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean).join(" • ");
  if (typeof value === "object") {
    return Object.values(value).map(cleanText).filter(Boolean).join(" • ");
  }
  return String(value).replace(/\s+/g, " ").trim();
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
    report.stories ||
    report.news ||
    report.headlines ||
    report.items ||
    report.articles ||
    report.sections ||
    [];

  if (Array.isArray(candidates)) return candidates.filter(Boolean);

  if (typeof candidates === "object") {
    return Object.values(candidates).flatMap((item: any) =>
      Array.isArray(item) ? item : [item]
    );
  }

  return [];
}

function storyTitle(story: AnyObj, index: number): string {
  return (
    cleanText(story.headline) ||
    cleanText(story.title) ||
    cleanText(story.name) ||
    `Politics Storyline ${index + 1}`
  );
}

function storyUrl(story: AnyObj): string {
  return cleanText(story.url) || cleanText(story.link) || cleanText(story.source_url) || "#";
}

function storySummary(story: AnyObj): string {
  return (
    cleanText(story.summary) ||
    cleanText(story.snapshot) ||
    cleanText(story.description) ||
    cleanText(story.body) ||
    "Political development flagged for newsroom monitoring."
  );
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

function StoryCard({ story, index }: { story: AnyObj; index: number }) {
  const title = storyTitle(story, index);
  const url = storyUrl(story);
  const summary = storySummary(story);

  const keyData = asList(story.key_data || story.keyData || story.data || story.metrics);
  const why = asList(story.why_it_matters || story.whyItMatters || story.why);
  const watch = asList(story.what_to_watch || story.whatToWatch || story.watch);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="mb-2 text-xs font-black uppercase tracking-wide text-red-700">
        Politics Watch
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
          <LineList items={why.length ? why : ["This affects political coverage priorities."]} />
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">What To Watch</p>
          <LineList items={watch.length ? watch : ["Monitor next official action or response."]} />
        </div>
      </div>
    </article>
  );
}

export default function Page() {
  const report = readReport();

  const headline =
    cleanText(report.headline) ||
    cleanText(report.title) ||
    "Politics Newsroom Watch: Major Developments Under Review";

  const snapshot =
    cleanText(report.snapshot) ||
    cleanText(report.summary) ||
    cleanText(report.body) ||
    "A live politics briefing built for journalists tracking power, policy, campaigns and public institutions.";

  const updated =
    cleanText(report.updated_at) ||
    cleanText(report.generated_at) ||
    cleanText(report.published_at) ||
    "Update time unavailable";

  let stories = getStories(report).filter((story) => story && typeof story === "object");

  if (!stories.length) {
    stories = [
      {
        headline: headline,
        summary: snapshot,
        key_data: ["Latest politics report generated from public data and news inputs."],
        why_it_matters: ["Editors need a fast read on what deserves coverage now."],
        what_to_watch: ["Refresh the content engine and verify source links."],
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

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="border-b border-slate-300 bg-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-5 py-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-sm font-black uppercase tracking-wide text-red-700">
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

          <div className="rounded-2xl border border-slate-300 bg-slate-950 p-3 shadow-sm">
            <div className="aspect-video overflow-hidden rounded-xl bg-black">
              <iframe
                src={SITE.videoUrl}
                title="Politics live video"
                allow="autoplay; encrypted-media; picture-in-picture"
                allowFullScreen
                className="h-full w-full"
              />
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-300">
              Live video module. If a provider blocks playback, the news cards below remain fully active.
            </p>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[0.75fr_1.25fr]">
        <aside className="space-y-6">
          <Block title="Editor Signals">
            <LineList
              items={
                signals.length
                  ? signals
                  : [
                      "Track the strongest hard-news development.",
                      "Prioritize verified source links.",
                      "Watch policy, campaign and institutional impact.",
                    ]
              }
            />
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
                "Power: Who gains leverage?",
                "Policy: What changes for citizens or institutions?",
                "Money: Who is funding, spending or benefiting?",
                "Accountability: What needs verification?",
                "Next: What happens today, tomorrow or this week?",
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
        <div className="mx-auto max-w-7xl px-5 py-6 text-sm text-slate-600">
          © {new Date().getFullYear()} {SITE.name}. {SITE.tagline}
        </div>
      </footer>
    </main>
  );
}