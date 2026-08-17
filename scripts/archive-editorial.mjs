import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REQUIRED_FIELDS = ["headline", "snapshot", "url", "source_name", "published"];

export function isEditorialStory(value) {
  const hasRequiredFields = Boolean(
    value &&
      typeof value === "object" &&
      REQUIRED_FIELDS.every(
        (field) => typeof value[field] === "string" && value[field].trim(),
      ),
  );

  if (!hasRequiredFields || Number.isNaN(new Date(value.published).getTime())) {
    return false;
  }

  try {
    new URL(value.url);
    return true;
  } catch {
    return false;
  }
}

export function storyKey(story) {
  const date = new Date(story.published).toISOString().slice(0, 10);
  const headline = story.headline
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 72);
  const source = new URL(story.url).hostname
    .replace(/^www\./, "")
    .replace(/[^a-z0-9]+/g, "-");

  return `${date}-${headline}-${source}`;
}

export function mergeEditorialStories(archived, reports) {
  const unique = new Map();

  for (const story of archived) {
    if (isEditorialStory(story)) unique.set(storyKey(story), story);
  }

  for (const report of reports) {
    const newsroom = Array.isArray(report?.live_newsroom)
      ? report.live_newsroom
      : [];

    for (const story of newsroom) {
      if (isEditorialStory(story)) unique.set(storyKey(story), story);
    }
  }

  return [...unique.values()].sort((a, b) => {
    const aTime = new Date(a.published).getTime();
    const bTime = new Date(b.published).getTime();
    return (Number.isNaN(bTime) ? 0 : bTime) - (Number.isNaN(aTime) ? 0 : aTime);
  });
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

function reportsFromHistory(repoRoot, sinceCommit) {
  const range = sinceCommit ? `${sinceCommit}..HEAD` : "HEAD";
  const hashes = execFileSync(
    "git",
    ["log", "--format=%H", range, "--", "public/latest_report.json"],
    { cwd: repoRoot, encoding: "utf8" },
  )
    .split(/\r?\n/)
    .filter(Boolean);

  return hashes.flatMap((hash) => {
    try {
      const json = execFileSync(
        "git",
        ["show", `${hash}:public/latest_report.json`],
        { cwd: repoRoot, encoding: "utf8", maxBuffer: 20 * 1024 * 1024 },
      );
      return [JSON.parse(json)];
    } catch {
      return [];
    }
  });
}

export function updateArchive({ reportPath, archivePath, historicalReports = [] }) {
  const report = readJson(reportPath, {});
  const archived = readJson(archivePath, []);
  const merged = mergeEditorialStories(
    Array.isArray(archived) ? archived : [],
    [...historicalReports, report],
  );
  const output = `${JSON.stringify(merged, null, 2)}\n`;
  const previous = fs.existsSync(archivePath)
    ? fs.readFileSync(archivePath, "utf8")
    : "";

  if (output !== previous) {
    fs.mkdirSync(path.dirname(archivePath), { recursive: true });
    fs.writeFileSync(archivePath, output, "utf8");
  }

  return { changed: output !== previous, count: merged.length };
}

const isMain = process.argv[1] &&
  fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);

if (isMain) {
  const repoRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
  const reportPath = path.join(repoRoot, "public", "latest_report.json");
  const archivePath = path.join(repoRoot, "public", "editorial-archive.json");
  const sinceIndex = process.argv.indexOf("--history-since");
  const historicalReports = sinceIndex >= 0
    ? reportsFromHistory(repoRoot, process.argv[sinceIndex + 1])
    : [];
  const result = updateArchive({ reportPath, archivePath, historicalReports });
  console.log(
    `Editorial archive: ${result.count} stories (${result.changed ? "updated" : "unchanged"}).`,
  );
}
