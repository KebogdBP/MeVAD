export interface ToolPage {
  slug: string;
  name: string;
  title: string;
  description: string;
  eyebrow: string;
  headline: string;
  lede: string;
  icon: string;
  formats: readonly string[];
  benefits: readonly {
    title: string;
    description: string;
  }[];
  steps: readonly {
    title: string;
    description: string;
  }[];
  faqs: readonly {
    question: string;
    answer: string;
  }[];
  keywords: readonly string[];
}

export const toolPages = [
  {
    slug: "video-downloader",
    name: "Video Downloader",
    title: "Online Video Downloader — Save Video with Clear Quality Controls",
    description:
      "Analyze a supported media link, inspect available formats and create a temporary video download with transparent progress.",
    eyebrow: "Video downloader",
    headline: "Download the video quality you actually need.",
    lede:
      "Paste one supported link, review its real formats and start a trackable download job. No account and no hidden full download during analysis.",
    icon: "↓",
    formats: ["MP4", "WEBM", "MKV", "AUTO"],
    benefits: [
      {
        title: "Source-aware quality",
        description:
          "Quality choices come from the formats detected for the source instead of a generic preset list.",
      },
      {
        title: "Size before action",
        description:
          "See a practical size estimate when the source provides enough stream metadata.",
      },
      {
        title: "Temporary results",
        description:
          "Completed files expose an expiry time and are removed by the storage lifecycle.",
      },
    ],
    steps: [
      {
        title: "Paste a permitted link",
        description: "Use media you own, may download or are legally allowed to process.",
      },
      {
        title: "Inspect real formats",
        description: "Choose a detected quality and the container that fits your device.",
      },
      {
        title: "Follow the job",
        description: "Track progress, cancel safely and download the temporary result.",
      },
    ],
    faqs: [
      {
        question: "Does MeVAD download the full video during analysis?",
        answer:
          "No. Analysis retrieves metadata first. A media job starts only after you choose an action and its options.",
      },
      {
        question: "Which video quality can I choose?",
        answer:
          "The workspace shows qualities detected for the specific source. Available formats vary by link.",
      },
      {
        question: "How long is the result stored?",
        answer:
          "Results are temporary. The completed job shows its expiry time when one is available.",
      },
    ],
    keywords: [
      "online video downloader",
      "download video by URL",
      "MP4 downloader",
      "WebM downloader",
    ],
  },
  {
    slug: "audio-downloader",
    name: "Audio Extractor",
    title: "Online Audio Extractor — Create MP3, M4A, Opus or WAV",
    description:
      "Extract audio from a supported media link with format, bitrate and estimated-size controls in one private workspace.",
    eyebrow: "Audio extractor",
    headline: "Turn a supported media link into clean audio.",
    lede:
      "Analyze once, choose MP3, M4A, Opus or WAV and see the output settings before the extraction job begins.",
    icon: "♪",
    formats: ["MP3", "M4A", "OPUS", "WAV"],
    benefits: [
      {
        title: "Useful audio formats",
        description:
          "Choose a compact listening format or lossless PCM output for editing workflows.",
      },
      {
        title: "Bitrate controls",
        description:
          "Select the bitrate for compressed outputs while WAV keeps an appropriate fixed path.",
      },
      {
        title: "Honest estimates",
        description:
          "Estimated size is calculated from duration and bitrate and is clearly labelled as approximate.",
      },
    ],
    steps: [
      {
        title: "Analyze the source",
        description: "Paste a supported link and review its duration and media metadata.",
      },
      {
        title: "Choose audio output",
        description: "Select the codec and bitrate appropriate for listening or editing.",
      },
      {
        title: "Download temporarily",
        description: "Follow extraction progress and save the result before it expires.",
      },
    ],
    faqs: [
      {
        question: "Can I extract MP3 from a video link?",
        answer:
          "Yes, when the analyzed source exposes an audio stream and the action is available.",
      },
      {
        question: "Which audio format should I use?",
        answer:
          "MP3 and M4A are broadly compatible, Opus is efficient, and WAV is useful for uncompressed editing workflows.",
      },
      {
        question: "Is the estimated audio size exact?",
        answer:
          "No. It is an estimate based on duration and output bitrate; the final encoded file can vary.",
      },
    ],
    keywords: [
      "extract audio from video",
      "online audio extractor",
      "video to MP3",
      "video to WAV",
    ],
  },
  {
    slug: "video-cutter",
    name: "Video Cutter",
    title: "Online Video Cutter — Cut a Precise Clip by URL",
    description:
      "Choose a start and end time, compare fast and accurate cutting modes and create a temporary clip from a supported URL.",
    eyebrow: "Video cutter",
    headline: "Cut the useful moment, not the whole workflow.",
    lede:
      "Set a precise interval after analysis, choose speed or frame-accurate output and track the clip as a durable job.",
    icon: "✂",
    formats: ["FAST CUT", "ACCURATE", "H.264", "AAC"],
    benefits: [
      {
        title: "Validated intervals",
        description:
          "The workspace checks that the end follows the start and stays within the detected duration.",
      },
      {
        title: "Two cut modes",
        description:
          "Fast mode uses nearby keyframes; accurate mode re-encodes for precise boundaries.",
      },
      {
        title: "No timeline guesswork",
        description:
          "The output preview states the clip duration and selected processing mode before creation.",
      },
    ],
    steps: [
      {
        title: "Analyze a permitted link",
        description: "Duration metadata establishes safe boundaries for the clip.",
      },
      {
        title: "Set the interval",
        description: "Enter the start and end time and choose fast or accurate mode.",
      },
      {
        title: "Create the clip",
        description: "Track the job and download the temporary result when it succeeds.",
      },
    ],
    faqs: [
      {
        question: "What is the difference between fast and accurate cutting?",
        answer:
          "Fast cutting uses the closest keyframes and avoids re-encoding. Accurate cutting re-encodes to respect precise boundaries.",
      },
      {
        question: "Can the end time exceed the source duration?",
        answer:
          "No. The interface validates the interval against the duration returned by analysis.",
      },
      {
        question: "Does cutting change the original source?",
        answer:
          "No. MeVAD creates a separate temporary result and does not modify the source.",
      },
    ],
    keywords: [
      "online video cutter",
      "cut video by URL",
      "trim video online",
      "download part of a video",
    ],
  },
  {
    slug: "video-to-gif",
    name: "Video to GIF",
    title: "Video to GIF Converter — Create a Lightweight Loop by URL",
    description:
      "Create a GIF, WebP or video loop from a supported link with duration, width, frame-rate, speed and quality controls.",
    eyebrow: "GIF and loop maker",
    headline: "Shape a short moment into a shareable loop.",
    lede:
      "Choose the exact interval, format, dimensions and frame rate while a live estimate keeps the output practical.",
    icon: "↻",
    formats: ["GIF", "WEBP", "MP4", "WEBM"],
    benefits: [
      {
        title: "Format choice",
        description:
          "Create an animated image or a compact video loop based on the destination.",
      },
      {
        title: "Size-aware controls",
        description:
          "Width, FPS, duration, speed and quality feed a live estimated output size.",
      },
      {
        title: "Safe product limits",
        description:
          "GIF and WebP intervals are limited to keep browser-friendly outputs practical.",
      },
    ],
    steps: [
      {
        title: "Find the moment",
        description: "Analyze the link and set the start and end of the short loop.",
      },
      {
        title: "Tune the output",
        description: "Choose format, width, FPS, quality, speed and repeat behavior.",
      },
      {
        title: "Create and save",
        description: "Run the job and download the result from temporary storage.",
      },
    ],
    faqs: [
      {
        question: "Can MeVAD create WebP as well as GIF?",
        answer:
          "Yes. The loop workflow supports GIF, WebP, MP4 and WebM outputs.",
      },
      {
        question: "Why is GIF duration limited?",
        answer:
          "Short limits keep animated-image file sizes and processing costs practical for browser use.",
      },
      {
        question: "Is the loop size estimate guaranteed?",
        answer:
          "No. It is a planning estimate based on dimensions, duration, frame rate, format and quality.",
      },
    ],
    keywords: [
      "video to GIF",
      "create GIF from video",
      "online GIF maker",
      "create video loop",
    ],
  },
] as const satisfies readonly ToolPage[];

export const toolPageMap: ReadonlyMap<string, ToolPage> = new Map(
  toolPages.map((tool) => [tool.slug, tool]),
);
