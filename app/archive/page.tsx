import type { Metadata } from "next";
import Link from "next/link";
import { getEditorialItems, SITE_URL } from "../lib/editorial-archive";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Editorial Archive | Global AI Report",
  description: "Permanent Global AI Report editorial coverage and source links.",
  alternates: { canonical: `${SITE_URL}/archive` },
};

export default async function ArchivePage() {
  const items = await getEditorialItems();

  return (
    <main>
      <h1>Global AI Report Editorial Archive</h1>
      <ul>
        {items.map((item) => (
          <li key={item.slug}>
            <Link href={`/editorial/${item.slug}`}>{item.headline}</Link>
            <br />
            <time dateTime={new Date(item.published).toISOString()}>
              {item.published}
            </time>
          </li>
        ))}
      </ul>
    </main>
  );
}

