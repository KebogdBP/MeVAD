export interface InfoSection {
  title: string;
  paragraphs: readonly string[];
  bullets?: readonly string[];
}

export interface InfoStep {
  title: string;
  description: string;
}

export interface InfoPage {
  slug: string;
  title: string;
  description: string;
  eyebrow: string;
  headline: string;
  lede: string;
  updated?: string;
  notice?: string;
  steps?: readonly InfoStep[];
  sections: readonly InfoSection[];
}

export const infoPages = [
  {
    slug: "how-it-works",
    title: "How MeVAD Works — From Media Link to Temporary Result",
    description:
      "Learn how MeVAD analyzes a permitted media link, exposes source-aware options, runs a trackable job and delivers a temporary result.",
    eyebrow: "A transparent workflow",
    headline: "From a permitted link to a temporary result.",
    lede:
      "MeVAD separates analysis from processing, so you can inspect what is available before a media job starts.",
    steps: [
      {
        title: "Analyze the link",
        description:
          "Paste a public, permitted source URL. MeVAD retrieves metadata and available actions without intentionally downloading the complete media during analysis.",
      },
      {
        title: "Choose the outcome",
        description:
          "Select video, audio, a clip or a loop, then review the source-aware formats, quality controls and practical estimates.",
      },
      {
        title: "Follow the job",
        description:
          "Processing runs as a durable job with explicit states, progress, retry-safe behavior and cancellation where the backend supports it.",
      },
      {
        title: "Save before expiry",
        description:
          "Successful jobs expose a temporary result. Download it before the displayed expiry time because storage is not permanent.",
      },
    ],
    sections: [
      {
        title: "Analysis comes before processing",
        paragraphs: [
          "The first request is for metadata: title, duration, thumbnail, detected streams and the actions the source can support. This keeps the product honest about what is actually available for a particular link.",
          "Availability can change when a source is private, requires authentication, is region-restricted, uses protected delivery or changes its public interface.",
        ],
      },
      {
        title: "Controls follow the selected task",
        paragraphs: [
          "Video choices come from detected formats. Audio extraction exposes codec and bitrate controls. Cutting validates the time range, while loop creation balances duration, dimensions, frame rate, speed and quality.",
          "Size values are estimates when the source or encoder cannot provide a guaranteed final size. The interface labels estimates instead of presenting them as exact promises.",
        ],
      },
      {
        title: "Jobs are visible and temporary",
        paragraphs: [
          "A processing request becomes a job with a stable identifier and status. The workspace can reconnect to that job, show progress and distinguish success, failure and cancellation.",
          "Results are temporary by design. The deployment controls the retention window, and the completed job should show an expiry time whenever that information is available.",
        ],
      },
    ],
  },
  {
    slug: "supported-sites",
    title: "Supported Media Sources — Compatibility Without Guesswork",
    description:
      "Understand how MeVAD checks public media sources, what supported and partial compatibility mean, and why availability can change by link.",
    eyebrow: "Compatibility is link-specific",
    headline: "Support is verified by analysis, not a logo wall.",
    lede:
      "A source is usable when MeVAD can inspect the submitted public link and return real metadata and actions for that link.",
    notice:
      "MeVAD does not promise permanent compatibility with a named platform and does not ask for passwords, cookies or access tokens to bypass source restrictions.",
    sections: [
      {
        title: "What the compatibility states mean",
        paragraphs: [
          "A supported link returns metadata plus at least one usable action. A partially supported link may expose only some streams, formats or actions. An unavailable link cannot be processed safely with the current analyzer.",
        ],
        bullets: [
          "Supported: metadata and one or more source-aware actions are available.",
          "Partial: useful metadata is available, but formats or actions are limited.",
          "Unavailable: analysis fails or the source cannot be accessed without unsupported credentials or restrictions.",
        ],
      },
      {
        title: "Sources that may work",
        paragraphs: [
          "The analyzer is designed for publicly accessible media pages, creator or social posts that expose usable media, audio-first pages and direct media URLs. Actual compatibility depends on the individual URL and the source response at analysis time.",
          "The reliable test is to paste a link and inspect the returned metadata. MeVAD should never fabricate formats that the source did not expose.",
        ],
      },
      {
        title: "Common reasons a link is unavailable",
        paragraphs: [
          "Private or deleted content, sign-in requirements, geographic restrictions, DRM or encrypted delivery, bot protection, rate limits and upstream changes can all prevent analysis or processing.",
          "Do not submit credentials or attempt to work around access controls. The source service terms and the rights attached to the media continue to apply.",
        ],
      },
      {
        title: "Report a compatibility regression",
        paragraphs: [
          "If a previously working public source stops analyzing, open a repository issue with a non-sensitive example URL or a redacted reproduction. Never include account cookies, authorization headers, private links or personal credentials.",
        ],
      },
    ],
  },
  {
    slug: "privacy",
    title: "Privacy Notice — How MeVAD Handles Links, Jobs and Results",
    description:
      "Read what MeVAD processes during link analysis and media jobs, how temporary results and local preferences work, and what remains to confirm before launch.",
    eyebrow: "Privacy notice",
    headline: "Process only what the media workflow needs.",
    lede:
      "This notice describes the current product behavior and the minimum data needed to analyze links, run jobs and deliver temporary results.",
    updated: "2026-07-27",
    notice:
      "Public-launch draft: operator identity, a direct private legal contact, deployment providers and jurisdiction-specific disclosures must be completed before production launch.",
    sections: [
      {
        title: "Information the service processes",
        paragraphs: [
          "MeVAD processes the source URL you submit, metadata returned during analysis, selected output settings, job identifiers and status, and temporary input or output artifacts needed to complete the requested task.",
          "Infrastructure may create operational and security logs such as timestamps, request identifiers, error categories and network information. Logging is designed to avoid storing URL credentials, cookies and raw upstream details, but the production logging configuration must be reviewed before launch.",
        ],
        bullets: [
          "Submitted source URL and source metadata.",
          "Chosen format, quality, time range and other job settings.",
          "Job status, progress, identifiers and temporary result metadata.",
          "Operational and security events required to run and protect the service.",
        ],
      },
      {
        title: "Why this information is used",
        paragraphs: [
          "The information is used to analyze the requested source, validate options, process the selected output, show job progress, deliver the result, diagnose failures and protect the service from abuse.",
          "The frontend includes a disabled-by-default first-party measurement capability for page views, workflow stages, Core Web Vitals and error categories. When enabled, it uses no analytics cookies or persistent visitor identifier and excludes query strings, submitted media URLs, job IDs, error messages and stack traces.",
        ],
      },
      {
        title: "Retention and local preferences",
        paragraphs: [
          "Media results are temporary. The default application configuration retains completed results for up to 24 hours, but a production deployment can configure a different window and should display the actual expiry time.",
          "The browser stores the light or dark theme preference locally under the key “mevad-theme”. Clearing site data removes that preference. MeVAD currently has no user accounts or saved personal media library.",
        ],
      },
      {
        title: "Sharing, security and external sources",
        paragraphs: [
          "A production service may rely on hosting, storage, queueing and monitoring providers to operate the workflow. Those providers, their locations and the retention period for telemetry must be documented before measurement is enabled. Information may also be disclosed when legally required or necessary to investigate abuse or protect the service.",
          "No online system can promise absolute security. Source sites have their own privacy practices, and following or submitting a third-party URL does not make MeVAD responsible for that site.",
        ],
      },
      {
        title: "Questions and privacy choices",
        paragraphs: [
          "Do not submit private links, embedded credentials or media you are not permitted to process. You can cancel a supported active job, download or ignore a result, clear local site data and avoid using the service.",
          "Until a private contact is published, open a general GitHub issue requesting a private channel and do not include personal data in the public issue. Applicable access, deletion or objection rights depend on the operator and jurisdiction, which must be finalized before launch.",
        ],
      },
    ],
  },
  {
    slug: "terms",
    title: "Terms of Use — Permitted and Responsible Use of MeVAD",
    description:
      "Review the rules for lawful media processing, prohibited uses, temporary result availability and third-party source responsibilities in MeVAD.",
    eyebrow: "Terms of use",
    headline: "Use MeVAD for media you may lawfully process.",
    lede:
      "These terms set the acceptable-use boundary for the public product while keeping source rights and restrictions visible.",
    updated: "2026-07-27",
    notice:
      "Public-launch draft: the legal operator, governing law, dispute terms and direct contact must be completed and reviewed before these terms can govern a production service.",
    sections: [
      {
        title: "Your permission and responsibility",
        paragraphs: [
          "You may use MeVAD only for content you own, are authorized to process, is in the public domain, or may otherwise lawfully use. You are responsible for the submitted URL, selected action and resulting file.",
          "A publicly reachable link does not automatically grant permission to download, copy, modify or redistribute its media. Source terms, licenses, privacy rights and applicable laws continue to apply.",
        ],
      },
      {
        title: "Prohibited use",
        paragraphs: [
          "You must not use the service to infringe intellectual-property or privacy rights, bypass DRM or access controls, obtain private or restricted content, distribute malware, impersonate another person, or violate applicable law.",
        ],
        bullets: [
          "No credentials, cookies, tokens or attempts to defeat authentication.",
          "No abusive automation, denial-of-service behavior or interference with operation.",
          "No unlawful, exploitative or rights-infringing media processing.",
          "No probing for vulnerabilities outside an authorized security process.",
        ],
      },
      {
        title: "Temporary service and third-party sources",
        paragraphs: [
          "MeVAD does not provide permanent storage. Jobs and results can expire, fail or become unavailable, and you are responsible for saving a permitted result before its displayed expiry.",
          "Compatibility depends on third-party sources that MeVAD does not control. The service may change, limit or suspend processing to protect users, infrastructure, rights holders or source services.",
        ],
      },
      {
        title: "Disclaimers and responsibility limits",
        paragraphs: [
          "The pre-launch software is provided on an as-available basis without a promise that every source, format or job will work. Estimates, metadata and compatibility results can be incomplete or change.",
          "Any warranty exclusions, liability limits, indemnity terms and consumer-law exceptions require jurisdiction-specific legal review before public launch and are not asserted by this draft.",
        ],
      },
      {
        title: "Enforcement, changes and contact",
        paragraphs: [
          "Access may be limited when use creates legal, security or operational risk. Material changes should be dated and presented before they take effect for a production service.",
          "Until a direct private contact is published, use the repository issue tracker for general questions without including personal, confidential or legally sensitive information.",
        ],
      },
    ],
  },
  {
    slug: "copyright",
    title: "Copyright Policy — Permitted Use and Reporting Guidance",
    description:
      "Learn MeVAD’s copyright-use boundary, what to include in an infringement report, and which legal contact details remain required before launch.",
    eyebrow: "Copyright policy",
    headline: "Rights and permission come before processing.",
    lede:
      "MeVAD is intended for media you own, may use with permission, that is in the public domain, or that applicable law otherwise allows you to process.",
    updated: "2026-07-27",
    notice:
      "Pre-launch limitation: MeVAD has not published a designated copyright agent or private notice address. It does not claim DMCA safe-harbor status. These details must be completed before public launch.",
    sections: [
      {
        title: "Respect rights attached to the source",
        paragraphs: [
          "MeVAD processing does not transfer ownership or grant a license. You remain responsible for determining whether downloading, extracting, cutting, converting, sharing or publishing a result is permitted.",
          "The service must not be used to remove rights controls, access private media or evade technical restrictions. When permission is unclear, do not process the content.",
        ],
      },
      {
        title: "What a copyright report should contain",
        paragraphs: [
          "A rights holder or authorized representative should provide enough information to identify the work, locate the allegedly infringing material and permit a meaningful response.",
        ],
        bullets: [
          "A physical or electronic signature of the authorized person.",
          "Identification of the copyrighted work, or a representative list for multiple works.",
          "The precise location of the material at issue, such as a job or result reference when available.",
          "Contact information for the reporting party.",
          "A good-faith statement that the disputed use is not authorized.",
          "A statement that the report is accurate and, under penalty of perjury, that the reporter is authorized to act.",
        ],
      },
      {
        title: "How to request a private reporting channel",
        paragraphs: [
          "Until a private copyright address is published, open a general GitHub issue asking the maintainer to provide a private channel. Do not put names, addresses, signatures, phone numbers or other sensitive notice details in a public issue.",
          "The production operator must publish a monitored private address, document the review and preservation process, and determine whether designation with the U.S. Copyright Office or another jurisdiction-specific mechanism is appropriate.",
        ],
      },
      {
        title: "Responses, counter-notices and repeat misuse",
        paragraphs: [
          "The operator should preserve relevant records, evaluate complete reports, restrict access when appropriate and notify affected users when lawful and possible. A counter-notice process must be finalized with legal review before production.",
          "Repeated or serious misuse may lead to blocked jobs, sources or access. Because MeVAD currently has no accounts, enforcement controls must be designed around jobs, requests and infrastructure without collecting unnecessary identity data.",
        ],
      },
    ],
  },
] as const satisfies readonly InfoPage[];

export const infoPageMap: ReadonlyMap<string, InfoPage> = new Map(
  infoPages.map((page) => [page.slug, page]),
);
