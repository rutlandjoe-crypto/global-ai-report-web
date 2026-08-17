import assert from "node:assert/strict";
import test from "node:test";

import {
  buildInfrastructureFinanceWatch,
  buildPublisherLicensingLedger,
  getRecentEditorialIntelligenceStories,
} from "../lib/structuredIntelligence.ts";

test("finance watch uses only supported story values", () => {
  const items = buildInfrastructureFinanceWatch([{
    headline: "Microsoft announces $4 billion AI data center investment",
    snapshot: "Microsoft plans to build an AI data center campus.",
    key_data: ["Key people or organizations: Microsoft"],
    why_it_matters: ["The project adds compute capacity."],
    source_name: "Example News",
    published: "2026-08-16",
    url: "https://example.com/finance",
  }]);

  assert.equal(items.length, 1);
  assert.equal(items[0].url, "https://example.com/finance");
  assert.deepEqual(items[0].fields.find((field) => field.label === "Reported value"), {
    label: "Reported value",
    value: "$4 billion",
  });
});

test("finance watch rejects infrastructure stories without a capital event", () => {
  assert.equal(buildInfrastructureFinanceWatch([{
    headline: "A tour of an AI data center",
    url: "https://example.com/tour",
  }]).length, 0);
});

test("licensing ledger preserves reported negotiations as unconfirmed", () => {
  const items = buildPublisherLicensingLedger([{
    headline: "OpenAI reportedly negotiating a news licensing deal",
    snapshot: "The publisher and OpenAI are in talks over journalism archives.",
    key_data: ["Key people or organizations: OpenAI, The Daily Ledger"],
    content_owner: "The Daily Ledger",
    source_name: "Example News",
    published: "2026-08-16",
    url: "https://example.com/licensing",
  }]);

  assert.equal(items.length, 1);
  assert.equal(items[0].fields.find((field) => field.label === "Agreement / status")?.value, "Reported negotiation");
  assert.equal(items[0].fields.find((field) => field.label === "Publisher / content owner")?.value, "The Daily Ledger");
  assert.equal(items[0].fields.some((field) => field.label === "Payment / usage model"), false);
});

test("recent durable editorial stories use permanent Global AI Report URLs", () => {
  const stories = getRecentEditorialIntelligenceStories([{
    slug: "2026-08-13-nvidia-plan-example-com",
    headline: "Nvidia's new $500B plan is risky but brilliant, especially for aging GPUs",
    context: "Financiers would keep lending for AI buildouts and compute capacity.",
    keyData: ["Key people or organizations: Nvidia"],
    whyItMatters: ["The plan affects AI infrastructure finance."],
    whatToWatch: [],
    storyAngles: [],
    sourceName: "Example News",
    sourceUrl: "https://example.com/nvidia",
    published: "2026-08-13T15:08:00Z",
  }], "https://www.globalaireport.news/");

  const items = buildInfrastructureFinanceWatch(stories);
  assert.equal(items.length, 1);
  assert.equal(items[0].url, "https://www.globalaireport.news/editorial/2026-08-13-nvidia-plan-example-com");
  assert.equal(items[0].source, "Example News");
});

test("licensing ledger recognizes sourced talks to pay publishers for AI news use", () => {
  const items = buildPublisherLicensingLedger([{
    headline: "Apple in talks to pay publishers to provide Siri with current news: report",
    snapshot: "The reported discussions concern payments for publisher news content.",
    source_name: "Example News",
    published: "2026-08-13",
    url: "https://www.globalaireport.news/editorial/apple-publishers",
  }]);

  assert.equal(items.length, 1);
  assert.equal(items[0].fields.find((field) => field.label === "Agreement / status")?.value, "Reported negotiation");
  assert.equal(items[0].fields.find((field) => field.label === "Payment / usage model")?.value, "Publisher payment");
});

test("recent archive selection excludes stale and nonqualifying items", () => {
  const stories = getRecentEditorialIntelligenceStories([
    {
      slug: "recent",
      headline: "A routine AI product update",
      context: "A company changed a product setting.",
      keyData: [], whyItMatters: [], whatToWatch: [], storyAngles: [],
      sourceName: "Example News", sourceUrl: "https://example.com/recent", published: "2026-08-17",
    },
    {
      slug: "stale",
      headline: "Microsoft announces $4 billion AI data center investment",
      context: "The capital commitment will build compute capacity.",
      keyData: [], whyItMatters: [], whatToWatch: [], storyAngles: [],
      sourceName: "Example News", sourceUrl: "https://example.com/stale", published: "2026-06-01",
    },
  ], "https://www.globalaireport.news");

  assert.equal(stories.length, 1);
  assert.equal(buildInfrastructureFinanceWatch(stories).length, 0);
  assert.equal(buildPublisherLicensingLedger(stories).length, 0);
});
