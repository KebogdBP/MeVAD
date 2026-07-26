import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { absoluteUrl, siteConfig } from "@/lib/site";
import { toolPageMap, toolPages } from "@/lib/tool-pages";

export const dynamicParams = false;

export function generateStaticParams() {
  return toolPages.map((tool) => ({ tool: tool.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ tool: string }>;
}): Promise<Metadata> {
  const { tool: slug } = await params;
  const tool = toolPageMap.get(slug);
  if (!tool) return {};

  const path = `/${tool.slug}`;
  return {
    title: tool.title,
    description: tool.description,
    keywords: [...tool.keywords],
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      url: path,
      title: tool.title,
      description: tool.description,
      images: [
        {
          url: siteConfig.ogImage,
          width: 1200,
          height: 630,
          alt: "MeVAD — one link, four media tools",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: tool.title,
      description: tool.description,
      images: [siteConfig.ogImage],
    },
  };
}

export default async function ToolLandingPage({
  params,
}: {
  params: Promise<{ tool: string }>;
}) {
  const { tool: slug } = await params;
  const tool = toolPageMap.get(slug);
  if (!tool) notFound();

  const pageUrl = absoluteUrl(`/${tool.slug}`);
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebPage",
        "@id": `${pageUrl}#webpage`,
        url: pageUrl,
        name: tool.title,
        description: tool.description,
        isPartOf: {
          "@type": "WebSite",
          "@id": `${siteConfig.url}#website`,
          name: siteConfig.name,
          url: siteConfig.url.toString(),
        },
      },
      {
        "@type": "WebApplication",
        "@id": `${pageUrl}#application`,
        name: `MeVAD ${tool.name}`,
        url: pageUrl,
        description: tool.description,
        applicationCategory: "MultimediaApplication",
        operatingSystem: "Any",
        browserRequirements: "Requires a modern web browser",
        isAccessibleForFree: true,
        featureList: tool.benefits.map((benefit) => benefit.title),
      },
      {
        "@type": "FAQPage",
        "@id": `${pageUrl}#faq`,
        mainEntity: tool.faqs.map((faq) => ({
          "@type": "Question",
          name: faq.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: faq.answer,
          },
        })),
      },
    ],
  };

  return (
    <main className="tool-page">
      <a className="skip-link" href="#tool-content">
        Skip to tool details
      </a>
      <SiteHeader />

      <section
        className="tool-hero"
        id="tool-content"
        aria-labelledby="tool-title"
      >
        <div className="hero-copy">
          <div className="eyebrow">
            <span aria-hidden="true">{tool.icon}</span>
            {tool.eyebrow}
          </div>
          <h1 id="tool-title">{tool.headline}</h1>
          <p className="hero-lede">{tool.lede}</p>
          <div className="hero-actions">
            <Link className="hero-primary" href="/#workspace">
              Open the workspace
              <span aria-hidden="true">↘</span>
            </Link>
            <a className="hero-secondary" href="#how-it-works">
              How it works
            </a>
          </div>
          <p className="legal-note">
            Process only content you own, have permission to use, or may process
            under applicable law and source terms.
          </p>
        </div>

        <aside className="tool-proof" aria-label={`${tool.name} output options`}>
          <span className="tool-proof-icon" aria-hidden="true">{tool.icon}</span>
          <small>Available output paths</small>
          <h2>{tool.name}</h2>
          <div className="format-ribbon">
            {tool.formats.map((format) => <span key={format}>{format}</span>)}
          </div>
          <ul>
            <li>Analyze metadata first</li>
            <li>Choose settings before processing</li>
            <li>Temporary result with clear job progress</li>
          </ul>
        </aside>
      </section>

      <section className="feature-section tool-benefits" aria-labelledby="benefits-title">
        <div className="section-heading">
          <span>Designed around the task</span>
          <h2 id="benefits-title">Useful control without workflow clutter.</h2>
        </div>
        <div className="bento-grid">
          {tool.benefits.map((benefit, index) => (
            <article className={index === 0 ? "bento-card bento-primary" : "bento-card"} key={benefit.title}>
              <span className="bento-kicker">0{index + 1}</span>
              <h3>{benefit.title}</h3>
              <p>{benefit.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="how-section" id="how-it-works" aria-labelledby="tool-how-title">
        <div className="section-heading compact">
          <span>How it works</span>
          <h2 id="tool-how-title">From permitted link to temporary result.</h2>
        </div>
        <ol className="steps-list">
          {tool.steps.map((step, index) => (
            <li key={step.title}>
              <b>0{index + 1}</b>
              <div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="faq-section" aria-labelledby="faq-title">
        <div className="section-heading compact">
          <span>Common questions</span>
          <h2 id="faq-title">{tool.name} FAQ</h2>
        </div>
        <div className="faq-list">
          {tool.faqs.map((faq) => (
            <details key={faq.question}>
              <summary>{faq.question}</summary>
              <p>{faq.answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="tool-cta" aria-labelledby="tool-cta-title">
        <div>
          <span>One calm workspace</span>
          <h2 id="tool-cta-title">Ready to work with a permitted link?</h2>
        </div>
        <Link className="hero-primary" href="/#workspace">
          Start with a link
          <span aria-hidden="true">→</span>
        </Link>
      </section>

      <SiteFooter />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(structuredData).replace(/</g, "\\u003c"),
        }}
      />
    </main>
  );
}
