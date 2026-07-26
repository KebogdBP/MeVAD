import Link from "next/link";

import { toolPages } from "@/lib/tool-pages";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-summary">
        <Link className="brand footer-brand" href="/" aria-label="MeVAD home">
          <span className="brand-mark" aria-hidden="true">↓</span>
          <span className="brand-copy">
            <strong>MeVAD</strong>
            <small>Media workspace</small>
          </span>
        </Link>
        <p>Built for permitted media processing with temporary results.</p>
      </div>
      <nav className="footer-links" aria-label="Media tools">
        {toolPages.map((tool) => (
          <Link href={`/${tool.slug}`} key={tool.slug}>
            {tool.name}
          </Link>
        ))}
      </nav>
      <a href="https://github.com/KebogdBP/MeVAD">View source</a>
    </footer>
  );
}
