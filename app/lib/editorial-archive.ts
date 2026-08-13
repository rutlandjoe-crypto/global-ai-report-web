import { list } from "@vercel/blob";
import report from "../../public/latest_report.json";

export const SITE_URL = "https://www.globalaireport.news";

export type EditorialItem = {
  slug: string;
  headline: string;
  context: string;
  keyData: string[];
  whyItMatters: string[];
  whatToWatch: string[];
  storyAngles: string[];
  sourceName: string;
  sourceUrl: string;
  published: string;
};

type ReportItem = {
  headline?: string;
  snapshot?: string;
  url?: string;
  source_name?: string;
  published?: string;
  key_data?: unknown;
  why_it_matters?: unknown;
  what_to_watch?: unknown;
  story_angles?: unknown;
};

function toTextList(value: unknown): string[] {
  if (!value) return [];

  const values = Array.isArray(value)
    ? value
    : typeof value === "object"
      ? Object.values(value)
      : String(value).split(/\n|\u2022|\|/);

  return values
    .map((item) => String(item).replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

export function slugFor(item: ReportItem): string {
  const date = item.published
    ? new Date(item.published).toISOString().slice(0, 10)
    : "undated";
  const headline = (item.headline ?? "editorial")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 72);
  const source = item.url
    ? new URL(item.url).hostname.replace(/^www\./, "").replace(/[^a-z0-9]+/g, "-")
    : "source";

  return `${date}-${headline}-${source}`;
}

export function toEditorialItem(item: ReportItem): EditorialItem | null {
  if (
    !item.headline ||
    !item.snapshot ||
    !item.url ||
    !item.source_name ||
    !item.published
  ) {
    return null;
  }

  return {
    slug: slugFor(item),
    headline: item.headline,
    context: item.snapshot,
    keyData: toTextList(item.key_data),
    whyItMatters: toTextList(item.why_it_matters),
    whatToWatch: toTextList(item.what_to_watch),
    storyAngles: toTextList(item.story_angles),
    sourceName: item.source_name,
    sourceUrl: item.url,
    published: item.published,
  };
}

export const seededEditorialItems: EditorialItem[] = (
  report.live_newsroom as ReportItem[]
)
  .map(toEditorialItem)
  .filter((item): item is EditorialItem => item !== null);

export async function getStoredEditorialItems(): Promise<EditorialItem[]> {
  try {
    const { blobs } = await list({ prefix: "editorial/", limit: 1000 });
    const items = await Promise.all(
      blobs
        .filter((blob) => blob.pathname.endsWith(".json"))
        .map(async (blob) => {
          const response = await fetch(blob.url, { next: { revalidate: 300 } });
          return response.ok ? ((await response.json()) as EditorialItem) : null;
        }),
    );

    return items.filter((item): item is EditorialItem => item !== null);
  } catch {
    return [];
  }
}

export async function getEditorialItems(): Promise<EditorialItem[]> {
  const stored = await getStoredEditorialItems();
  const unique = new Map<string, EditorialItem>();

  [...seededEditorialItems, ...stored].forEach((item) => {
    const existing = unique.get(item.slug);
    unique.set(item.slug, {
      ...existing,
      ...item,
      keyData: item.keyData?.length ? item.keyData : existing?.keyData ?? [],
      whyItMatters: item.whyItMatters?.length
        ? item.whyItMatters
        : existing?.whyItMatters ?? [],
      whatToWatch: item.whatToWatch?.length
        ? item.whatToWatch
        : existing?.whatToWatch ?? [],
      storyAngles: item.storyAngles?.length
        ? item.storyAngles
        : existing?.storyAngles ?? [],
    });
  });

  return [...unique.values()].sort(
    (a, b) => new Date(b.published).getTime() - new Date(a.published).getTime(),
  );
}
