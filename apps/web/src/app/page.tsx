import Link from "next/link";

import { MediaWorkspace } from "@/components/media-workspace";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { absoluteUrl } from "@/lib/site";
import { toolPages } from "@/lib/tool-pages";

export default function HomePage() {
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "@id": `${absoluteUrl("/")}#application`,
    name: "MeVAD",
    url: absoluteUrl("/"),
    applicationCategory: "MultimediaApplication",
    operatingSystem: "Any",
    browserRequirements: "Requires a modern web browser",
    description:
      "A web workspace for analyzing online media, downloading video, extracting audio, cutting clips and creating GIF loops.",
    featureList: [
      "Video downloads",
      "Audio extraction",
      "Precise clip cutting",
      "GIF and video loops",
    ],
    isAccessibleForFree: true,
  };

  return (
    <main>
      <a className="skip-link" href="#workspace">
        Skip to media workspace
      </a>
      <SiteHeader />

      <section className="hero-layout" aria-labelledby="hero-title">
        <div className="hero-copy">
          <div className="eyebrow">
            <span aria-hidden="true">✦</span>
            One link · four media tools
          </div>
          <h1 id="hero-title">
            Make online media
            <em> yours to shape.</em>
          </h1>
          <p className="hero-lede">
            Analyze once, then download video, extract audio, cut a precise clip or
            create a lightweight loop — all in one calm workspace.
          </p>

          <div className="hero-actions">
            <a className="hero-primary" href="#workspace">
              Start with a link
              <span aria-hidden="true">↓</span>
            </a>
            <Link className="hero-secondary" href="/how-it-works">
              <span className="play-dot" aria-hidden="true">▶</span>
              See how it works
            </Link>
          </div>

          <ul className="trust-row" aria-label="Product assurances">
            <li>
              <span aria-hidden="true">◒</span>
              No account needed
            </li>
            <li>
              <span aria-hidden="true">◇</span>
              Temporary files
            </li>
            <li>
              <span aria-hidden="true">⌁</span>
              Clear job progress
            </li>
          </ul>
        </div>

        <div className="workspace-stage">
          <div className="stage-glow stage-glow-peach" aria-hidden="true" />
          <div className="stage-glow stage-glow-mint" aria-hidden="true" />
          <MediaWorkspace />
          <div className="floating-proof proof-fast" aria-hidden="true">
            <span>↯</span>
            <div><strong>Fast presets</strong><small>Complexity stays hidden</small></div>
          </div>
          <div className="floating-proof proof-private" aria-hidden="true">
            <span>✓</span>
            <div><strong>Private by design</strong><small>Results auto-expire</small></div>
          </div>
        </div>
      </section>

      <section className="feature-section" id="features" aria-labelledby="features-title">
        <div className="section-heading">
          <span>Built around the task</span>
          <h2 id="features-title">Four tools. One predictable workflow.</h2>
          <p>Useful controls when you need them, sensible defaults when you don’t.</p>
        </div>

        <div className="bento-grid">
          <article className="bento-card bento-primary">
            <div className="bento-icon">▣</div>
            <span className="bento-kicker">All-in-one workspace</span>
            <h3>Switch outputs, not websites.</h3>
            <p>
              The same analyzed link powers video, audio, clip and loop actions without
              repeating the slow part.
            </p>
            <div className="format-ribbon" aria-label="Available actions">
              <span>MP4</span><span>MP3</span><span>CLIP</span><span>GIF</span>
            </div>
          </article>

          <article className="bento-card">
            <div className="bento-icon mint">✂</div>
            <span className="bento-kicker">Precise clipping</span>
            <h3>Fast cut or exact boundaries.</h3>
            <p>Choose speed for quick trims or accurate re-encoding for precise output.</p>
          </article>

          <article className="bento-card">
            <div className="bento-icon gold">↻</div>
            <span className="bento-kicker">Loop controls</span>
            <h3>GIFs that fit the destination.</h3>
            <p>Balance width, frame rate, quality and speed with a live size estimate.</p>
          </article>

          <article className="bento-card bento-wide" id="safety">
            <div>
              <span className="bento-kicker">Durable and transparent</span>
              <h3>Progress you can trust.</h3>
              <p>
                Jobs can retry safely, be cancelled explicitly and show when a finished
                result will expire.
              </p>
            </div>
            <div className="progress-demo" aria-hidden="true">
              <div className="progress-demo-head">
                <span><i /> Processing media</span>
                <strong>68%</strong>
              </div>
              <div><span /></div>
              <small>Preparing output · temporary workspace</small>
            </div>
          </article>
        </div>
      </section>

      <section className="how-section" id="how-it-works" aria-labelledby="how-title">
        <div className="section-heading compact">
          <span>How it works</span>
          <h2 id="how-title">From link to result in three clear steps.</h2>
        </div>
        <ol className="steps-list">
          <li>
            <b>01</b>
            <div><h3>Paste a link</h3><p>We analyze metadata before any full media download begins.</p></div>
          </li>
          <li>
            <b>02</b>
            <div><h3>Choose an action</h3><p>Pick a format, quality or a precise time range.</p></div>
          </li>
          <li>
            <b>03</b>
            <div><h3>Follow the job</h3><p>Track progress, cancel safely and download the temporary result.</p></div>
          </li>
        </ol>
      </section>

      <section className="tool-directory" aria-labelledby="tools-title">
        <div className="section-heading compact">
          <span>Explore by task</span>
          <h2 id="tools-title">A focused page for every core media action.</h2>
          <p>Start with the outcome you need, then use the same secure workspace.</p>
        </div>
        <div className="tool-link-grid">
          {toolPages.map((tool) => (
            <Link href={`/${tool.slug}`} key={tool.slug}>
              <span aria-hidden="true">{tool.icon}</span>
              <div>
                <strong>{tool.name}</strong>
                <small>{tool.description}</small>
              </div>
              <b aria-hidden="true">→</b>
            </Link>
          ))}
        </div>
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
