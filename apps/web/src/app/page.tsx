import { MediaWorkspace } from "@/components/media-workspace";

export default function HomePage() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#" aria-label="MeVAD home">
          <span className="brand-mark" aria-hidden="true">
            M
          </span>
          <span>MeVAD</span>
        </a>
        <nav aria-label="Main navigation">
          <a href="#workspace">Workspace</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <span className="privacy-pill">Files auto-expire</span>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <div className="eyebrow">
          <span />
          One link. Every media action.
        </div>
        <h1 id="hero-title">
          Make online media
          <em> yours to use.</em>
        </h1>
        <p>
          Analyze a link once, then download video, extract audio, cut a clip or create
          a loop — without jumping between tools.
        </p>
      </section>

      <MediaWorkspace />

      <section className="trust-grid" id="how-it-works" aria-label="How MeVAD works">
        <article>
          <span>01</span>
          <h2>Paste a link</h2>
          <p>We inspect metadata first. The full media is downloaded only after you choose.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Choose an action</h2>
          <p>Clear presets hide codec complexity while keeping the useful controls close.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Get your result</h2>
          <p>Follow durable progress, cancel safely and see exactly when files disappear.</p>
        </article>
      </section>

      <footer>
        <span>MeVAD · Media workspace</span>
        <span>Built for clarity, control and trust.</span>
      </footer>
    </main>
  );
}
