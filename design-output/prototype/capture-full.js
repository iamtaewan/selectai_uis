const path = require("path");
const fs = require("fs");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");
const sharp = require("sharp");

const root = path.resolve(__dirname, "..", "..");
const htmlPath = path.resolve(__dirname, "index.html");
const outputDir = path.resolve(root, "design-output", "full-size", "png");
fs.mkdirSync(outputDir, { recursive: true });

const pages = [
  ["PG-00", "PG-00-onboarding-full.png", "온보딩"],
  ["PG-01", "PG-01-connections-full.png", "커넥션"],
  ["PG-02", "PG-02-permissions-full.png", "권한 점검"],
  ["PG-03", "PG-03-profiles-full.png", "프로파일 목록"],
  ["PG-03a", "PG-03a-profile-editor-full.png", "프로파일 생성"],
  ["PG-03b", "PG-03b-profile-detail-full.png", "프로파일 상세"],
  ["PG-04", "PG-04-playground-full.png", "플레이그라운드"],
  ["PG-05", "PG-05-chat-full.png", "챗봇"],
  ["PG-05a", "PG-05a-chat-history-full.png", "대화 이력"],
  ["PG-06", "PG-06-enrichment-full.png", "증강 비교"],
  ["PG-07", "PG-07-dashboard-full.png", "대시보드"],
  ["PG-08", "PG-08-settings-full.png", "설정"],
];

const chromeExecutable = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

async function launchBrowser() {
  const options = {
    headless: true,
    args: ["--font-render-hinting=medium", "--disable-dev-shm-usage"],
  };
  if (fs.existsSync(chromeExecutable)) {
    options.executablePath = chromeExecutable;
  }
  return chromium.launch(options);
}

async function captureFullSize(browser) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1400 },
    deviceScaleFactor: 1,
    colorScheme: "light",
  });
  const page = await context.newPage();
  const base = pathToFileURL(htmlPath).toString();
  for (const [id, file] of pages) {
    await page.goto(`${base}?page=${encodeURIComponent(id)}&full=1`, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(outputDir, file), fullPage: false });
    console.log(`captured ${file}`);
  }
  await context.close();
}

async function mobileCheck(browser) {
  const ids = ["PG-03a", "PG-04", "PG-06", "PG-08"];
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    deviceScaleFactor: 2,
    colorScheme: "light",
  });
  const page = await context.newPage();
  const base = pathToFileURL(htmlPath).toString();
  const results = [];
  for (const id of ids) {
    await page.goto(`${base}?page=${encodeURIComponent(id)}&full=1`, { waitUntil: "networkidle" });
    const metrics = await page.evaluate(() => {
      const doc = document.documentElement;
      return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, bodyWidth: document.body.scrollWidth };
    });
    results.push({ id, ok: metrics.scrollWidth <= metrics.clientWidth + 1 && metrics.bodyWidth <= metrics.clientWidth + 1, metrics });
  }
  await context.close();
  return results;
}

async function makeContactSheet() {
  const thumbWidth = 318;
  const thumbHeight = 309;
  const labelHeight = 34;
  const gap = 20;
  const cols = 4;
  const rows = Math.ceil(pages.length / cols);
  const width = cols * thumbWidth + (cols + 1) * gap;
  const height = rows * (thumbHeight + labelHeight) + (rows + 1) * gap;
  const composites = [];

  for (let i = 0; i < pages.length; i++) {
    const [, file, label] = pages[i];
    const col = i % cols;
    const row = Math.floor(i / cols);
    const left = gap + col * (thumbWidth + gap);
    const top = gap + row * (thumbHeight + labelHeight + gap);
    const inputPath = path.join(outputDir, file);
    const thumbBuffer = await sharp(inputPath).resize(thumbWidth, thumbHeight, { fit: "cover", position: "top" }).png().toBuffer();
    const text = `${file.replace(".png", "")}  ${label}`;
    const labelSvg = Buffer.from(`
      <svg width="${thumbWidth}" height="${labelHeight}" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#FFFFFF"/>
        <text x="10" y="22" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" font-weight="700" fill="#312D2A">${escapeXml(text)}</text>
      </svg>
    `);
    composites.push({ input: thumbBuffer, left, top });
    composites.push({ input: labelSvg, left, top: top + thumbHeight });
  }

  await sharp({
    create: { width, height, channels: 4, background: "#FBF9F8" },
  })
    .composite(composites)
    .png()
    .toFile(path.join(outputDir, "INDEX-contact-sheet-full.png"));
  console.log("captured INDEX-contact-sheet-full.png");
}

function escapeXml(value) {
  return value.replace(/[<>&'"]/g, (char) => ({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
  }[char]));
}

(async () => {
  const browser = await launchBrowser();
  try {
    await captureFullSize(browser);
    const mobile = await mobileCheck(browser);
    await makeContactSheet();
    console.log("mobile-check", JSON.stringify(mobile, null, 2));
    if (mobile.some((r) => !r.ok)) {
      process.exitCode = 2;
    }
  } finally {
    await browser.close();
  }
})();
