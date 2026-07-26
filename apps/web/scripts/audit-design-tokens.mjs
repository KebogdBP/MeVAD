import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

async function sourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map((entry) => {
      const target = path.join(directory, entry.name);
      return entry.isDirectory() ? sourceFiles(target) : [target];
    }),
  );
  return files.flat();
}

const legacyStylesheet = await readFile("src/app/globals.css", "utf8");
const colors =
  legacyStylesheet.match(
    /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)/g,
  ) ?? [];
const spacing =
  legacyStylesheet.match(
    /(?:margin|padding|gap|inset|top|right|bottom|left|width|height|min-width|min-height|max-width|max-height)[^:{}]*:\s*[^;{}]*\b\d+(?:\.\d+)?(?:px|rem)\b/g,
  ) ?? [];
const fingerprint = createHash("sha256")
  .update(JSON.stringify({ colors, spacing }))
  .digest("hex");
const approvedLegacyFingerprint =
  "18530b243c05b5029540f68d86933ba87813d8425daf6779b22c702160a54d9c";
const componentLiterals = [];
for (const file of (await sourceFiles("src"))
  .filter((candidate) => /\.(ts|tsx)$/.test(candidate))
  .sort()) {
  const source = await readFile(file, "utf8");
  const literals =
    source.match(
      /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|\b\d+(?:\.\d+)?(?:px|rem)\b/g,
    ) ?? [];
  if (literals.length > 0) {
    componentLiterals.push([file.replaceAll("\\", "/"), literals]);
  }
}
const componentFingerprint = createHash("sha256")
  .update(JSON.stringify(componentLiterals))
  .digest("hex");
const approvedComponentFingerprint =
  "a10bb5da0eaf7a8180727afb52c65a9ab1372e5fa3392b3f7e1437a8eea420ce";

if (
  fingerprint !== approvedLegacyFingerprint ||
  componentFingerprint !== approvedComponentFingerprint
) {
  throw new Error(
    [
      "Raw color or spacing values changed in globals.css.",
      "Use a design token from tokens.css. If a legacy exception is unavoidable,",
      "document it in PHASE_7_UI_GUIDELINES.md and review the fingerprint update.",
      `Stylesheet fingerprint: ${fingerprint}`,
      `Component fingerprint: ${componentFingerprint}`,
    ].join("\n"),
  );
}

console.log(
  `Design-token gate passed (${colors.length} legacy color and ${spacing.length} spacing literals frozen).`,
);
