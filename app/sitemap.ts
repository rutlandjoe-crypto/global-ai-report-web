import type { MetadataRoute } from "next";
import { getEditorialItems, SITE_URL } from "./lib/editorial-archive";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const items = await getEditorialItems();

  return [
    {
      url: `${SITE_URL}/`,
      lastModified: new Date(),
      changeFrequency: "hourly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/archive`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.8,
    },
    ...items.map((item) => ({
      url: `${SITE_URL}/editorial/${item.slug}`,
      lastModified: new Date(item.published),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
}
