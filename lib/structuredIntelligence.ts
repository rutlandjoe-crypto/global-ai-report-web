export type IntelligenceStory = Record<string, unknown>;

export type IntelligenceField = {
  label: string;
  value: string;
};

export type IntelligenceItem = {
  headline: string;
  url: string;
  source: string;
  fields: IntelligenceField[];
};

export type EditorialIntelligenceStory = {
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

const RECENT_EDITORIAL_WINDOW_DAYS = 45;

const AI_COMPANIES = [
  "OpenAI",
  "Anthropic",
  "Google",
  "Microsoft",
  "Meta",
  "Amazon",
  "Apple",
  "Nvidia",
  "xAI",
  "Perplexity",
  "Mistral",
  "Cohere",
  "Adobe",
  "IBM",
  "Oracle",
];

function text(value: unknown): string {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

function list(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(text).filter(Boolean);
  const valueText = text(value);
  return valueText ? [valueText] : [];
}

function storyText(story: IntelligenceStory): string {
  return [
    story.headline,
    story.title,
    story.snapshot,
    story.summary,
    story.description,
    story.context,
  ]
    .map(text)
    .filter(Boolean)
    .join(" ");
}

export function getRecentEditorialIntelligenceStories(
  items: EditorialIntelligenceStory[],
  siteUrl: string,
  windowDays = RECENT_EDITORIAL_WINDOW_DAYS,
): IntelligenceStory[] {
  const datedItems = items
    .map((item) => ({ item, timestamp: new Date(item.published).getTime() }))
    .filter(({ timestamp }) => Number.isFinite(timestamp));
  const newestTimestamp = Math.max(...datedItems.map(({ timestamp }) => timestamp));
  if (!Number.isFinite(newestTimestamp)) return [];

  const cutoff = newestTimestamp - windowDays * 24 * 60 * 60 * 1000;
  return datedItems
    .filter(({ timestamp }) => timestamp >= cutoff)
    .sort((a, b) => b.timestamp - a.timestamp)
    .map(({ item }) => ({
      headline: item.headline,
      snapshot: item.context,
      key_data: item.keyData,
      why_it_matters: item.whyItMatters,
      what_to_watch: item.whatToWatch,
      story_angles: item.storyAngles,
      source_name: item.sourceName,
      source_url: item.sourceUrl,
      published: item.published,
      url: `${siteUrl.replace(/\/$/, "")}/editorial/${item.slug}`,
    }));
}

function headline(story: IntelligenceStory): string {
  return text(story.headline) || text(story.title);
}

function sourceUrl(story: IntelligenceStory): string {
  const url = text(story.url) || text(story.source_url) || text(story.link);
  return /^https?:\/\//i.test(url) ? url : "";
}

function sourceName(story: IntelligenceStory): string {
  return text(story.source_name) || text(story.source_label) || text(story.publisher) || "Original source";
}

function published(story: IntelligenceStory): string {
  return text(story.published) || text(story.published_at) || text(story.date);
}

function firstWhy(story: IntelligenceStory): string {
  return list(story.why_it_matters || story.whyItMatters || story.why)[0] || "";
}

function firstMatch(input: string, choices: Array<[RegExp, string]>): string {
  return choices.find(([pattern]) => pattern.test(input))?.[1] || "";
}

function moneyValue(input: string): string {
  return (
    input.match(/\$\s?\d[\d,.]*(?:\.\d+)?\s?(?:trillion|billion|million|thousand|tn|bn|m|t|b|k)?\b/i)?.[0] || ""
  ).replace(/\s+/g, " ");
}

function organizations(story: IntelligenceStory): string {
  const supportedLine = list(story.key_data).find((item) =>
    /^(?:key people or organizations|company \/ organization|companies \/ organizations):/i.test(item)
  );
  if (supportedLine) return supportedLine.replace(/^[^:]+:\s*/, "");

  const input = storyText(story);
  return AI_COMPANIES.filter((company) => new RegExp(`\\b${company.replace("xAI", "xAI")}\\b`, "i").test(input))
    .slice(0, 4)
    .join(", ");
}

function publisherCounterparty(story: IntelligenceStory): string {
  return text(story.publisher_content_owner) || text(story.content_owner) || text(story.publisher_partner);
}

function status(input: string): string {
  return firstMatch(input, [
    [/\b(settlement|settled)\b/i, "Settlement"],
    [/\b(lawsuit|sued|court challenge|complaint)\b/i, "Lawsuit / dispute"],
    [/\b(reportedly|reported negotiation|in talks|negotiat(?:e|ing|ions))\b/i, "Reported negotiation"],
    [/\b(expired|ended|terminated)\b/i, "Expired / ended"],
    [/\b(announced|unveiled|will invest|plans? to|agreed|signed)\b/i, "Announced"],
    [/\b(completed|closed|operational|opened)\b/i, "Completed / operational"],
  ]);
}

function licensingStatus(input: string): string {
  return firstMatch(input, [
    [/\b(settlement|settled)\b/i, "Settlement"],
    [/\b(lawsuit|sued|court challenge|complaint)\b/i, "Lawsuit / dispute"],
    [/\b(reportedly|reported negotiation|in talks|negotiat(?:e|ing|ions))\b/i, "Reported negotiation"],
    [/\b(expired|ended|terminated)\b/i, "Expired / ended arrangement"],
    [/\b(signed|agreed|licensing agreement|content agreement|licensing deal)\b/i, "Confirmed agreement"],
    [/\b(announced partnership|partners? with|partnership)\b/i, "Announced partnership"],
  ]);
}

function itemFrom(story: IntelligenceStory, fields: IntelligenceField[]): IntelligenceItem | null {
  const itemHeadline = headline(story);
  const url = sourceUrl(story);
  if (!itemHeadline || !url) return null;

  return {
    headline: itemHeadline,
    url,
    source: sourceName(story),
    fields: fields.filter((field) => Boolean(field.value)),
  };
}

function uniqueItems(items: Array<IntelligenceItem | null>, limit = 5): IntelligenceItem[] {
  const seen = new Set<string>();
  return items.filter((item): item is IntelligenceItem => {
    if (!item) return false;
    const key = item.headline.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, limit);
}

export function buildInfrastructureFinanceWatch(stories: IntelligenceStory[]): IntelligenceItem[] {
  const infrastructure = /\b(data cent(?:er|re)s?|semiconductor|chips?|gpu|compute|cloud infrastructure|power|utility|utilities|nuclear|energy|grid|construction|campus|infrastructure)\b/i;
  const capital = /\b(financ(?:e|ing|ier|iers)|funding|investment|invests?|capital expenditure|capex|debt|lend(?:er|ers|ing)?|loan|bond|private equity|infrastructure fund|partnership|agreement|commitment|spending|buildout|construction project)\b/i;

  return uniqueItems(
    stories.filter((story) => {
      const input = storyText(story);
      return infrastructure.test(input) && capital.test(input) && Boolean(sourceUrl(story));
    }).map((story) => {
      const input = storyText(story);
      const category = firstMatch(input, [
        [/\bdata cent(?:er|re)s?\b/i, "AI data centers"],
        [/\b(semiconductor|chips?|gpu)\b/i, "Chips / compute"],
        [/\bcloud infrastructure\b/i, "Cloud infrastructure"],
        [/\b(nuclear|power|utility|utilities|energy|grid)\b/i, "Power / energy"],
        [/\bconstruction|campus\b/i, "AI construction"],
      ]);
      const financingType = firstMatch(input, [
        [/\bdebt|lend(?:er|ers|ing)?|loan|bond\b/i, "Debt financing"],
        [/\bprivate equity\b/i, "Private equity"],
        [/\binfrastructure fund\b/i, "Infrastructure fund"],
        [/\bcapital expenditure|capex\b/i, "Capital expenditure"],
        [/\bpartnership|agreement\b/i, "Partnership / agreement"],
        [/\bfunding|investment|invests?\b/i, "Investment / funding"],
      ]);

      return itemFrom(story, [
        { label: "Company / organizations", value: organizations(story) },
        { label: "Transaction or project", value: headline(story) },
        { label: "Reported value", value: moneyValue(input) },
        { label: "Financing / investment type", value: financingType },
        { label: "Infrastructure category", value: category },
        { label: "Status", value: status(input) },
        { label: "Announcement / report date", value: published(story) },
        { label: "Why it matters", value: firstWhy(story) },
      ]);
    })
  );
}

export function buildPublisherLicensingLedger(stories: IntelligenceStory[]): IntelligenceItem[] {
  const contentOwner = /\b(publisher|publishing|news(?:room|paper| organization)?|media compan(?:y|ies)|content owner|archive|journalism|books?|authors?|images?|photo(?:graphy|s)?|information provider)\b/i;
  const relationship = /\b(licens(?:e|ed|ing)|content agreement|training.data|attribution|revenue.sharing|usage.payment|pay(?:ment|s|ing)? (?:a )?publishers?|partnership|settlement|lawsuit|copyright|negotiat(?:e|ing|ions)|in talks|deal)\b/i;
  const ai = new RegExp(`\\b(?:AI|artificial intelligence|${AI_COMPANIES.join("|")})\\b`, "i");

  return uniqueItems(
    stories.filter((story) => {
      const input = storyText(story);
      return ai.test(input) && contentOwner.test(input) && relationship.test(input) && Boolean(sourceUrl(story));
    }).map((story) => {
      const input = storyText(story);
      const aiCompanies = AI_COMPANIES.filter((company) => new RegExp(`\\b${company}\\b`, "i").test(input)).join(", ");
      const relationshipType = firstMatch(input, [
        [/\bsettlement|settled\b/i, "Settlement"],
        [/\blawsuit|sued|court challenge|copyright dispute\b/i, "Lawsuit / dispute"],
        [/\bpay(?:ment|s|ing)? (?:a )?publishers?\b/i, "Publisher content payment"],
        [/\brevenue.sharing|usage.payment\b/i, "Revenue sharing / usage payment"],
        [/\btraining.data\b/i, "Training-data agreement"],
        [/\battribution\b/i, "Attribution arrangement"],
        [/\blicens(?:e|ed|ing)\b/i, "Content licensing"],
        [/\bpartnership\b/i, "Publisher-AI partnership"],
        [/\bnegotiat(?:e|ing|ions)\b/i, "Reported negotiation"],
      ]);
      const content = firstMatch(input, [
        [/\barchives?\b/i, "Archives"],
        [/\bjournalism|news(?:room|paper)?\b/i, "Journalism / news content"],
        [/\bbooks?|authors?\b/i, "Books / authored work"],
        [/\bimages?|photo(?:graphy|s)?\b/i, "Images / photography"],
        [/\btraining.data\b/i, "Training data"],
      ]);
      const usageModel = firstMatch(input, [
        [/\brevenue.sharing\b/i, "Revenue sharing"],
        [/\bpay(?:ment|s|ing)? (?:a )?publishers?\b/i, "Publisher payment"],
        [/\busage.payment|pay(?:ment|s|ing) per use\b/i, "Usage payment"],
        [/\blicens(?:e|ing) fee\b/i, "Licensing fee"],
      ]);

      return itemFrom(story, [
        { label: "AI company / platform", value: aiCompanies },
        { label: "Publisher / content owner", value: publisherCounterparty(story) },
        { label: "Deal or relationship type", value: relationshipType },
        { label: "Content involved", value: content },
        { label: "Payment / usage model", value: usageModel },
        { label: "Agreement / status", value: licensingStatus(input) },
        { label: "Announcement / report date", value: published(story) },
        { label: "Why it matters", value: firstWhy(story) },
      ]);
    })
  );
}
