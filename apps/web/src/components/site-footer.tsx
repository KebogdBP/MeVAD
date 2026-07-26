import Link from "next/link";

import { toolPages } from "@/lib/tool-pages";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-summary">
        <Link className="brand footer-brand" href="/">
          <span className="brand-mark" aria-hidden="true">↓</span>
          <span className="brand-copy">
            <strong>MeVAD</strong>
            <small>Media workspace</small>
          </span>
        </Link>
        <p>Built for permitted media processing with temporary results.</p>
        <a href="https://github.com/KebogdBP/MeVAD">View source on GitHub</a>
      </div>
      <div className="footer-navigation">
        <nav className="footer-links" aria-label="Media tools">
          <strong>Tools</strong>
          {toolPages.map((tool) => (
            <Link href={`/${tool.slug}`} key={tool.slug}>
              {tool.name}
            </Link>
          ))}
        </nav>
        <nav className="footer-links" aria-label="Product information">
          <strong>Product</strong>
          <Link href="/how-it-works">How it works</Link>
          <Link href="/supported-sites">Supported sources</Link>
        </nav>
        <nav className="footer-links" aria-label="Legal information">
          <strong>Legal</strong>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/copyright">Copyright</Link>
        </nav>
      </div>
    </footer>
  );
}
