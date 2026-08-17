import assert from "node:assert/strict";
import { mergeEditorialStories } from "./archive-editorial.mjs";

const prior = {
  headline: "Prior story",
  snapshot: "Prior context",
  url: "https://example.com/prior",
  source_name: "Example",
  published: "2026-08-15T12:00:00Z",
};
const current = {
  headline: "Current story",
  snapshot: "Current context",
  url: "https://example.com/current",
  source_name: "Example",
  published: "2026-08-16T12:00:00Z",
};

const merged = mergeEditorialStories(
  [prior],
  [{ live_newsroom: [current, prior, { headline: "Thin story" }] }],
);

assert.deepEqual(merged, [current, prior]);
assert.equal(merged.filter((story) => story.headline === "Prior story").length, 1);
console.log("Editorial archive tests passed.");
