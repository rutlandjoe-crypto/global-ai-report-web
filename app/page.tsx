import fs from "fs";
import path from "path";
import { headers } from "next/headers";

import EditorialStandard from "@/components/EditorialStandard";
import SocialIconLinks from "@/app/SocialIconLinks";

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
  ["Sports", "https://www.globalsportsreport.com"],
  ["AI", "https://www.globalaireport.news"],
  ["Politics", "https://www.globalpoliticsreport.com"],
  ["Entertainment", "https://www.globalentertainmentreport.com"],
  ["Betting", "https://www.globalbettingreport.com"],
];

const BAD_CONTENT_PHRASES = [
  "source refresh",
  "refresh needed",
  "needed before publication",
  "strict mode",
  "current-day update pending",
  "feed checked",
  "required date",
  "rebuild distribution",
  "bad or stale",
  "not allowed onto the homepage",
  "no verified data point attached yet",
  "no current items available",
  "undefined",
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

  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean).join(" • ");
  }

  if (typeof value === "object") {
    return Object.values(value).map(cleanText).filter(Boolean).join(" • ");
  }

  return String(value)
    .replace(/Ã¢â‚¬â€/g, "â€”")
    .replace(/Ã¢â‚¬â€œ/g, "â€“")
    .replace(/Ã¢â‚¬Ëœ/g, "'")
    .replace(/Ã¢â‚¬â„¢/g, "'")
    .replace(/Ã¢â‚¬Å“/g, '"')
    .replace(/Ã¢â‚¬ï¿½/g, '"')
    .replace(/Ã‚/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeText(value: any): string {
  return cleanText(value).toLowerCase();
}

function isBadContent(value: any): boolean {
  const text = normalizeText(value);
  if (!text) return true;
  return BAD_CONTENT_PHRASES.some((phrase) => text.includes(phrase));
}

function unique(items: string[]): string[] {
  const seen = new Set<string>();

  return items
    .map(cleanText)
    .filter((item) => item && !isBadContent(item))
    .filter((item) => {
      const key = item.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function asList(value: any): string[] {
  if (!value) return [];

  if (Array.isArray(value)) {
    return unique(value.flatMap((item) => cleanText(item).split(/\n|•|\|/)));
  }

  if (typeof value === "object") {
    return unique(Object.values(value).flatMap((item) => cleanText(item).split(/\n|•|\|/)));
  }

  return unique(cleanText(value).split(/\n|•|\|/));
}

function normalizeStory(story: AnyObj, index: number): AnyObj {
  return {
    ...story,
    id: cleanText(story.id || story.key || `ai-story-${index}`),
    key: cleanText(story.key || story.id || `ai-story-${index}`),
    label: cleanText(story.label || story.category || story.source || "AI Watch"),
    headline:
      cleanText(story.headline) ||
      cleanText(story.title) ||
      cleanText(story.name) ||
      `AI Development ${index + 1}`,
    title:
      cleanText(story.title) ||
      cleanText(story.headline) ||
      cleanText(story.name) ||
      `AI Development ${index + 1}`,
    summary:
      cleanText(story.summary) ||
      cleanText(story.snapshot) ||
      cleanText(story.description) ||
      cleanText(story.body) ||
      "Editors are tracking how this AI development may affect companies, policy, infrastructure or research.",
    snapshot:
      cleanText(story.snapshot) ||
      cleanText(story.summary) ||
      cleanText(story.description) ||
      cleanText(story.body) ||
      "Editors are tracking how this AI development may affect companies, policy, infrastructure or research.",
    key_data: asList(story.key_data || story.keyData || story.data || story.metrics).slice(0, 8),
    why_it_matters: asList(story.why_it_matters || story.whyItMatters || story.why).slice(0, 6),
    what_to_watch: asList(story.what_to_watch || story.whatToWatch || story.watch).slice(0, 8),
    story_angles: asList(story.story_angles || story.storyAngles || story.angles).slice(0, 6),
  };
}

function getStories(report: AnyObj): AnyObj[] {
  const collections = [
    report.homepage_cards,
    report.live_newsroom,
    report.stories,
    report.cards,
    report.sections,
    report.news,
    report.headlines,
    report.items,
    report.articles,
  ];

  for (const candidates of collections) {
    if (Array.isArray(candidates) && candidates.length) {
      return candidates
        .filter((story) => story && typeof story === "object")
        .map((story, index) => normalizeStory(story, index));
    }

    if (candidates && typeof candidates === "object") {
      return Object.entries(candidates).flatMap(([key, item]: [string, any], index) => {
        if (Array.isArray(item)) {
          return item
            .filter((story) => story && typeof story === "object")
            .map((story, itemIndex) =>
              normalizeStory(
                {
                  id: `${key}-${itemIndex}`,
                  key,
                  label: key,
                  ...story,
                },
                itemIndex
              )
            );
        }

        if (item && typeof item === "object") {
          return [
            normalizeStory(
              {
                id: key,
                key,
                label: item.label || item.category || key,
                ...item,
              },
              index
            ),
          ];
        }

        return [];
      });
    }
  }

  return [];
}

function getSpotlightStories(report: AnyObj, key: "live_newsroom" | "editor_signals"): AnyObj[] {
  const raw = report[key];
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item) => item && typeof item === "object")
    .map((item, index) => normalizeStory(item, index));
}

function storyTitle(story: AnyObj, index: number): string {
  return (
    cleanText(story.headline) ||
    cleanText(story.title) ||
    cleanText(story.name) ||
    `AI Development ${index + 1}`
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
    "Editors are tracking how this AI development may affect companies, policy, infrastructure or research."
  );
}

function storyLabel(story: AnyObj): string {
  return cleanText(story.label) || cleanText(story.category) || cleanText(story.source) || "AI Watch";
}

function storySignal(story: AnyObj, index: number): string {
  return cleanText(`${storyLabel(story)}: ${storyTitle(story, index)}`);
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-black uppercase tracking-wide text-blue-800">
        {cleanText(title)}
      </h2>
      {children}
    </section>
  );
}

function EditorsBookshelf() {
  const books = [
    ["The Coming Wave", "Mustafa Suleyman"],
    ["Co-Intelligence", "Ethan Mollick"],
    ["Superagency", "Reid Hoffman & Greg Beato"],
  ];

  return (
    <Block title="Editor's Bookshelf">
      <div className="space-y-2">
        {books.map(([title, author]) => (
          // TODO: Replace this Amazon search URL with the final Amazon Associates URL.
          <a
            key={title}
            href={`https://www.amazon.com/s?k=${encodeURIComponent(`${title} ${author}`)}&tag=gsrai-20`}
            target="_blank"
            rel="sponsored noopener noreferrer"
            className="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 hover:bg-blue-50"
          >
            <span className="block text-sm font-bold text-blue-900">{title}</span>
            <span className="mt-1 block text-xs text-slate-600">{author}</span>
          </a>
        ))}
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-500">
        As an Amazon Associate, GSR Network earns from qualifying purchases.
      </p>
    </Block>
  );
}

function LineList({ items }: { items: string[] }) {
  const safe = unique(items).slice(0, 8);

  if (!safe.length) {
    return (
      <p className="text-sm leading-6 text-slate-700">
        The next update will surface the clearest AI developments across companies, policy, infrastructure and research.
      </p>
    );
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
  const safe = unique(items).slice(0, 6);

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
  const angles = asList(story.story_angles || story.storyAngles || story.angles);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="mb-2 text-xs font-black uppercase tracking-wide text-blue-700">
        {storyLabel(story)}
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

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">Key Data</p>
          <LineList items={keyData.length ? keyData : ["The clearest available signal will appear here as the story develops."]} />
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">Why It Matters</p>
          <LineList items={why.length ? why : ["This affects AI coverage priorities, enterprise adoption, policy direction or market strategy."]} />
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">What To Watch</p>
          <LineList items={watch.length ? watch : ["Monitor the next company, model, policy, infrastructure or market response."]} />
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-slate-600">Story Angles</p>
          <LineList items={angles.length ? angles : ["The strongest AI stories usually connect a company move, technical shift, policy response or business consequence."]} />
        </div>
      </div>
    </article>
  );
}


function SponsorPlacementBlock() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-3">
      <div className="rounded-2xl border border-black/10 bg-white/90 p-5 shadow-sm">
        <p className="text-xs font-black uppercase tracking-[0.25em] text-neutral-500">
          Partner Spotlight
        </p>
        <h2 className="mt-2 text-xl font-black text-neutral-950">
          Partnership opportunities are available across the GSR Network.
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
          Reach readers through clean, clearly labeled placements across Sports, Betting, AI, Politics and Entertainment — built around journalistic integrity.
        </p>
      </div>
    </section>
  );
}

function AdvertiseWithGsrBlock() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-6">
      <div className="rounded-2xl border border-black/10 bg-white/90 p-5 shadow-sm">
        <p className="text-xs font-black uppercase tracking-[0.25em] text-neutral-500">
          Advertise With GSR Network
        </p>
        <h2 className="mt-2 text-xl font-black text-neutral-950">
          Sponsorship, partnership, affiliate and custom campaign opportunities are open.
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
          GSR Network offers clearly labeled placements for brands, events, data companies, media partners and vertical-specific advertisers across all five platforms.
        </p>
      </div>
    </section>
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
        story_angles: ["Follow the strongest business, product, policy or infrastructure thread."],
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
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className={
                  name === "AI"
                    ? "text-blue-200 hover:text-white"
                    : "text-white hover:text-blue-200"
                }
              >
                {name}
              </a>
              {index < GSR_NETWORK.length - 1 ? <span className="text-blue-400">•</span> : null}
            </span>
          ))}
        </div>
      </div>

      <div className="border-b border-neutral-800 bg-neutral-950 text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-5 py-2 text-xs font-bold uppercase tracking-wide">
          <span className="text-neutral-400">Follow GSR:</span>
          <SocialIconLinks hoverClassName="hover:border-sky-300" />
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
      <EditorialStandard />
      <SponsorPlacementBlock />


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

          <EditorsBookshelf />

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
            <StoryCard key={story.id || index} story={story} index={index} />
          ))}
        </section>
      </section>
      <AdvertiseWithGsrBlock />


      <footer className="border-t border-slate-300 bg-white">
        <div className="mx-auto max-w-7xl px-5 py-6">
          <p className="text-sm font-medium text-slate-700">
            Â© {new Date().getFullYear()} {SITE.name}. {SITE.tagline}
          </p>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-500">
            {SITE.descriptor}
          </p>
        </div>
      </footer>
    </main>
  );
}


