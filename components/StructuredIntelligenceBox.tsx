import type { IntelligenceItem } from "@/lib/structuredIntelligence";

export default function StructuredIntelligenceBox({
  title,
  description,
  items,
}: {
  title: string;
  description: string;
  items: IntelligenceItem[];
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-black uppercase tracking-wide text-blue-700">GSR Structured Intelligence</p>
      <h2 className="mt-1 text-xl font-black text-slate-950">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>

      {items.length ? (
        <div className="mt-4 space-y-4">
          {items.map((item) => (
            <article key={`${item.headline}-${item.url}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="font-black leading-6 text-slate-950">{item.headline}</h3>
              <dl className="mt-3 grid gap-2 text-sm">
                {item.fields.map((field) => (
                  <div key={`${item.url}-${field.label}`} className="grid gap-1 border-b border-slate-200 pb-2 sm:grid-cols-[11rem_1fr]">
                    <dt className="font-black text-slate-600">{field.label}</dt>
                    <dd className="leading-5 text-slate-800">{field.value}</dd>
                  </div>
                ))}
              </dl>
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex text-sm font-black text-blue-800 underline underline-offset-4"
              >
                Read original source · {item.source} <span aria-hidden="true">↗</span>
              </a>
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
          No qualifying sourced developments are in the current report. The ledger will update when the existing AI feeds carry a supported item.
        </p>
      )}
    </section>
  );
}
