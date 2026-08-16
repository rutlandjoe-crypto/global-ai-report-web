import assert from "node:assert/strict";
import test from "node:test";

import {
  buildInfrastructureFinanceWatch,
  buildPublisherLicensingLedger,
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
