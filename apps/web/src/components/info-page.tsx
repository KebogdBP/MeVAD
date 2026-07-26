import Link from "next/link";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import type { InfoPage } from "@/lib/info-pages";
import { absoluteUrl, siteConfig } from "@/lib/site";

export function InfoPageView({ page }: { page: InfoPage }) {
  const pageUrl = absoluteUrl(`/${page.slug}`);
  const graph: Record<string, unknown>[] = [
    {
      "@type": "WebPage",
      "@id": `${pageUrl}#webpage`,
      url: pageUrl,
      name: page.title,
      description: page.description,
      dateModified: page.updated,
      isPartOf: {
        "@type": "WebSite",
        "@id": `${siteConfig.url}#website`,
        name: siteConfig.name,
        url: siteConfig.url.toString(),
      },
    },
  ];

  if (page.steps) {
    graph.push({
      "@type": "HowTo",
      "@id": `${pageUrl}#howto`,
      name: page.headline,
      description: page.lede,
      step: page.steps.map((step, index) => ({
        "@type": "HowToStep",
        position: index + 1,
        name: step.title,
        text: step.description,
      })),
    });
  }

  return (
    <main className="info-page">
      <a className="skip-link" href="#info-content">
        Skip to page content
      </a>
      <SiteHeader />

      <article id="info-content">
        <header className="info-hero">
          <div className="eyebrow">
            <span aria-hidden="true">✦</span>
            {page.eyebrow}
          </div>
          <h1>{page.headline}</h1>
          <p>{page.lede}</p>
          {page.updated ? (
            <p className="info-updated">
              Last updated: <time dateTime={page.updated}>July 27, 2026</time>
            </p>
          ) : null}
          {page.notice ? <aside className="info-notice">{page.notice}</aside> : null}
        </header>

        {page.steps ? (
          <ol className="info-steps" aria-label="MeVAD workflow">
            {page.steps.map((step, index) => (
              <li key={step.title}>
                <span>0{index + 1}</span>
                <div>
                  <h2>{step.title}</h2>
                  <p>{step.description}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : null}

        <div className="info-sections">
          {page.sections.map((section) => (
            <section key={section.title}>
              <h2>{section.title}</h2>
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
              {section.bullets ? (
                <ul>
                  {section.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}
                </ul>
              ) : null}
            </section>
          ))}
        </div>

        <aside className="info-cta" aria-labelledby="info-cta-title">
          <div>
            <span>One link · explicit choices</span>
            <h2 id="info-cta-title">Use the workspace with a permitted source.</h2>
          </div>
          <Link className="hero-primary" href="/#workspace">
            Open workspace
            <span aria-hidden="true">→</span>
          </Link>
        </aside>
      </article>

      <SiteFooter />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@graph": graph,
          }).replace(/</g, "\\u003c"),
        }}
      />
    </main>
  );
}
