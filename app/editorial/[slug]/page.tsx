import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  getEditorialItems,
  seededEditorialItems,
  SITE_URL,
} from "../../lib/editorial-archive";

type Props = { params: Promise<{ slug: string }> };

export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return seededEditorialItems.map(({ slug }) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const item = (await getEditorialItems()).find((entry) => entry.slug === slug);

  if (!item) return {};

  return {
    title: `${item.headline} | Global AI Report`,
    description: item.context.slice(0, 160),
    alternates: { canonical: `${SITE_URL}/editorial/${item.slug}` },
  };
}

export default async function EditorialPage({ params }: Props) {
  const { slug } = await params;
  const item = (await getEditorialItems()).find((entry) => entry.slug === slug);

  if (!item) notFound();

  return (
    <article>
      <h1>{item.headline}</h1>
      <time dateTime={new Date(item.published).toISOString()}>
        {item.published}
      </time>
      <p>{item.context}</p>
      <p>
        Source: <a href={item.sourceUrl}>{item.sourceName}</a>
      </p>
    </article>
  );
}

