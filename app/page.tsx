import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type AnyObj = Record<string, any>;

const SITE = {
  name: "Global AI Report",
  tagline: "Built for journalists, by a journalist.",
  topic: "AI",
  descriptor:
    "Global AI Report tracks artificial intelligence across business, policy, infrastructure and innovation, delivering journalist-ready signals on the fastest-moving sector in the global economy.",
};

const DEFAULT_VIDEO =
  process.env.NEXT_PUBLIC_GAI_VIDEO_URL ||
  "https://www.youtube.com/embed/21X5lGlDOfg?rel=0&autoplay=1&mute=1";

const FALLBACK_VIDEO_LINK = "https://www.youtube.com/";

const TOOLKIT = [
  ["OpenAI", "https://openai.com"],
  ["Google AI", "https://ai.google"],
  ["NVIDIA News", "https://nvidia.com/en-us/news/"],
  ["Hugging Face", "https://huggingface.co"],
  ["MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/"],
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

function normalizeVideoUrl(value: any): string {
  const cleaned = cleanText(value) || DEFAULT_VIDEO;

  const needsRel = !cleaned.includes("rel=");
  const needsAutoplay = !cleaned.includes("autoplay=");
  const needsMute = !cleaned.includes("mute=");

  const params = [
    needsRel ? "rel=0" : "",
    needsAutoplay ? "autoplay=1" : "",
    needsMute ? "mute=1" : "",
  ].filter(Boolean);

  if (!params.length) return cleaned;

  return `${cleaned}${cleaned.includes("?") ? "&" : "?"}${params.join("&")}`;
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
    `AI Storyline ${index + 1}`
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
    "AI development flagged for newsroom monitoring."
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

function VideoModule({ videoUrl }: { videoUrl: string }) {
  return (
    <div className="rounded-2xl border border-slate-300 bg-slate-950 p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs font-black uppercase tracking-wide text-blue-300">
          Live Coverage
        </p>

        <a
          href={FALLBACK_VIDEO_LINK}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-full border border-blue-300 px-3 py-1 text-xs font-bold text-blue-200 hover:bg-blue-300 hover:text-slate-950"
        >
          Open Live Coverage
        </a>
      </div>

      <div className="aspect-video overflow-hidden rounded-xl bg-black">
        <iframe
          src={videoUrl}
          title="AI live video"
          allow="autoplay; encrypted-media; picture-in-picture"
          allowFullScreen
          className="h-full w-full"
        />
      </div>

      <p className="mt-3 text-xs leading-5 text-slate-300">
        If the embedded provider blocks playback, use the Open Live Coverage button.
      </p>
    </div>
  );
}

export default function Page() {
  const report = readReport();
  const videoUrl = normalizeVideoUrl(report.video_url);

  const headline =
    cleanText(report.headline) ||
    "AI Newsroom Watch: Major Developments Under Review";

  const snapshot =
    cleanText(report.snapshot) ||
    "A live AI briefing built for journalists tracking companies, models, infrastructure, policy and global competition.";

  const updated =
    cleanText(report.updated_at) ||
    cleanText(report.generated_at) ||
    "Update time unavailable";

  let stories = getStories(report).filter((story) => story && typeof story === "object");

  if (!stories.length) {
    stories = [
      {
        headline,
        summary: snapshot,
        key_data: ["Latest AI report generated from live feeds."],
        why_it_matters: ["Editors need fast clarity in a rapidly evolving sector."],
        what_to_watch: ["Next model release, policy move or company response."],
      },
    ];
  }

  const leadStories = stories.slice(0, 10);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
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

          <VideoModule videoUrl={videoUrl} />
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-5 py-6 space-y-6">
        {leadStories.map((story, index) => (
          <div key={index} className="bg-white p-5 rounded-2xl shadow">
            <h2 className="font-bold text-xl">{storyTitle(story, index)}</h2>
            <p className="mt-2 text-sm text-slate-700">{storySummary(story)}</p>
          </div>
        ))}
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
      </footer>
    </main>
  );
}