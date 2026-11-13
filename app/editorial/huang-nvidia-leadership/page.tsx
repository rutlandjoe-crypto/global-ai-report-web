import type { Metadata } from "next";
import { SITE_URL } from "../../lib/editorial-archive";
import { huangColumn, huangParagraphs } from "../../lib/huang-column";

const canonical = `${SITE_URL}${huangColumn.path}`;

export const metadata: Metadata = {
  title: `${huangColumn.headline} | Global AI Report`,
  description: "Joe Rutland on the questions Nvidia’s board still faces after Jensen Huang’s resignation.",
  authors: [{ name: huangColumn.author }],
  alternates: { canonical },
  openGraph: {
    type: "article",
    url: canonical,
    title: huangColumn.headline,
  },
};

export default function HuangColumnPage() {
  return (
    <main className="bg-slate-100 px-5 py-10 text-slate-950">
      <article className="mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:p-10">
        <header>
          <h1 className="text-3xl font-black leading-tight md:text-5xl">
            {huangColumn.headline}
          </h1>
          <p className="mt-4 font-bold">By {huangColumn.author}</p>
          <p className="italic">{huangColumn.series}</p>
          <time className="text-sm text-slate-600" dateTime={huangColumn.date}>
            {huangColumn.displayDate}
          </time>
        </header>
        <div className="mt-6 space-y-5 text-lg leading-8 text-slate-700">
          {huangParagraphs.map(({ text, sources }) => (
            <p key={text}>
              {text}
              {sources.map(({ label, url }) => (
                <a key={url} href={url} className="ml-2 text-sm font-medium text-blue-800 underline">
                  {label}
                </a>
              ))}
            </p>
          ))}
        </div>
      </article>
    </main>
  );
}
