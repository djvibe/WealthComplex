#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const readline = require("node:readline/promises");
const { stdin, stdout, env } = require("node:process");
const { chromium } = require("/home/djvibe/.nvm/versions/node/v20.20.0/lib/node_modules/@playwright/cli/node_modules/playwright");

const rootDir = path.resolve(__dirname, "..");
const outputRoot = env.OUTPUT_DIR || path.join(rootDir, "working", "wealthsimple-ui-mirror");
const profileDir = env.PROFILE_DIR || path.join(rootDir, "working", "browser-profiles", "wealthsimple-capture");
const firstRoute = process.argv[2] || env.FIRST_ROUTE || "https://my.wealthsimple.com/app/home";
const maxPages = Number.parseInt(env.MAX_PAGES || "12", 10);
const waitMs = Number.parseInt(env.WAIT_MS || "4000", 10);
const logFilePath = env.LOG_FILE || path.join(outputRoot, "capture.log");
const allowedOrigin = "https://my.wealthsimple.com";
const defaultSeedRoutes = [
  "https://my.wealthsimple.com/app/home",
  "https://my.wealthsimple.com/app/net-worth",
  "https://my.wealthsimple.com/app/holdings-dashboard",
  "https://my.wealthsimple.com/app/move",
  "https://my.wealthsimple.com/app/activity",
  "https://my.wealthsimple.com/app/tax-onboarding",
  "https://my.wealthsimple.com/app/reward-centre",
  "https://my.wealthsimple.com/app/account-selection",
  "https://my.wealthsimple.com/app/insights",
];

const captureableTypes = new Set(["document", "stylesheet", "image", "font", "script"]);
const assetManifest = {};
const routeManifest = [];
const assetWrites = new Map();
const queue = Array.from(new Set([firstRoute, ...defaultSeedRoutes]));
const seenRoutes = new Set();
let assetCounter = 0;

function normalizeRoute(rawUrl) {
  const parsed = new URL(rawUrl);
  parsed.hash = "";
  return parsed.href;
}

function safeName(value) {
  return value.replace(/[^a-zA-Z0-9._/-]+/g, "-").replace(/^-+|-+$/g, "") || "index";
}

function shaName(value) {
  return crypto.createHash("sha1").update(value).digest("hex").slice(0, 12);
}

function extensionFromContentType(contentType) {
  const value = (contentType || "").split(";")[0].trim().toLowerCase();
  const mapping = new Map([
    ["text/css", ".css"],
    ["text/html", ".html"],
    ["application/javascript", ".js"],
    ["text/javascript", ".js"],
    ["application/json", ".json"],
    ["image/png", ".png"],
    ["image/jpeg", ".jpg"],
    ["image/gif", ".gif"],
    ["image/webp", ".webp"],
    ["image/svg+xml", ".svg"],
    ["font/woff2", ".woff2"],
    ["font/woff", ".woff"],
    ["font/ttf", ".ttf"],
    ["font/otf", ".otf"],
  ]);

  return mapping.get(value) || "";
}

function localAssetPath(rawUrl, contentType) {
  const parsed = new URL(rawUrl);
  let pathname = parsed.pathname;
  if (!pathname || pathname.endsWith("/")) {
    pathname = `${pathname}index`;
  }

  const ext = path.extname(pathname);
  const inferredExt = ext || extensionFromContentType(contentType);
  const basePath = ext ? pathname.slice(0, -ext.length) : pathname;
  const querySuffix = parsed.search ? `--${shaName(parsed.search)}` : "";

  return path.join(
    "assets",
    safeName(parsed.hostname),
    `${basePath}${querySuffix}${inferredExt}`.replace(/^\/+/, ""),
  );
}

function pageOutputDir(rawUrl) {
  const parsed = new URL(rawUrl);
  const routeName = safeName(`${parsed.pathname}${parsed.search ? `-${shaName(parsed.search)}` : ""}`);
  return path.join(outputRoot, "pages", routeName);
}

async function log(message) {
  const line = `[capture] ${message}`;
  console.log(line);
  await fs.appendFile(logFilePath, `${line}\n`);
}

async function writeAsset(response) {
  const url = response.url();
  const contentType = response.headers()["content-type"] || "";
  const resourceType = response.request().resourceType();

  if (!/^https?:/i.test(url) || !captureableTypes.has(resourceType)) {
    return;
  }

  if (assetWrites.has(url)) {
    await assetWrites.get(url);
    return;
  }

  const writer = (async () => {
    try {
      const body = await response.body();
      const relativePath = localAssetPath(url, contentType);
      const absolutePath = path.join(outputRoot, relativePath);

      await fs.mkdir(path.dirname(absolutePath), { recursive: true });
      await fs.writeFile(absolutePath, body);

      assetManifest[url] = {
        local_path: relativePath,
        status: response.status(),
        content_type: contentType,
        resource_type: resourceType,
      };
      assetCounter += 1;
      await log(`asset ${assetCounter}: ${resourceType} ${response.status()} ${url} -> ${relativePath}`);
    } catch (error) {
      assetManifest[url] = {
        error: String(error),
        status: response.status(),
        content_type: contentType,
        resource_type: resourceType,
      };
      await log(`asset error: ${url} (${String(error)})`);
    }
  })();

  assetWrites.set(url, writer);
  await writer;
}

async function promptForLogin() {
  console.log("Opening Wealthsimple in a headed persistent browser session.");
  console.log("1. Complete login in the browser window if prompted.");
  console.log("2. Navigate to the part of the app you want captured.");
  console.log("3. Return here and press Enter to start the mirror capture.");
  console.log("");
  console.log(`Output directory: ${outputRoot}`);
  console.log(`Log file: ${logFilePath}`);
  console.log(`Profile directory: ${profileDir}`);
  console.log(`Seed route: ${firstRoute}`);
  console.log(`Max pages: ${maxPages}`);

  const rl = readline.createInterface({ input: stdin, output: stdout });
  await rl.question("Press Enter once the app is visible and ready to capture... ");
  rl.close();
}

async function capturePage(page, targetUrl) {
  await log(`page ${routeManifest.length + 1}: navigating to ${targetUrl}`);
  await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(waitMs);
  await page.evaluate(async () => {
    const distance = Math.max(600, Math.floor(window.innerHeight * 0.9));
    const maxSteps = 12;
    for (let step = 0; step < maxSteps; step += 1) {
      window.scrollBy(0, distance);
      await new Promise(resolve => window.setTimeout(resolve, 250));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(800);

  const metadata = await page.evaluate(() => {
    const hrefs = Array.from(document.querySelectorAll("a[href]"))
      .map(anchor => anchor.href)
      .filter(Boolean);
    const resourceUrls = new Set();

    for (const element of document.querySelectorAll("[src], [href]")) {
      const value = element.getAttribute("src") || element.getAttribute("href");
      if (!value) {
        continue;
      }

      try {
        resourceUrls.add(new URL(value, document.baseURI).href);
      } catch {
      }
    }

    return {
      title: document.title,
      hrefs,
      resource_urls: Array.from(resourceUrls),
    };
  });
  const domSnapshot = await page.evaluate(() => {
    const text = value => (value || "").replace(/\s+/g, " ").trim();
    const limitText = (value, max = 160) => text(value).slice(0, max);

    return {
      captured_at: new Date().toISOString(),
      location: {
        href: location.href,
        origin: location.origin,
        pathname: location.pathname,
        search: location.search,
        hash: location.hash,
      },
      document: {
        title: document.title,
        lang: document.documentElement.lang || null,
        dir: document.documentElement.dir || null,
        body_text_sample: limitText(document.body?.innerText || "", 1000),
      },
      headings: Array.from(document.querySelectorAll("h1, h2, h3")).slice(0, 30).map(node => ({
        tag: node.tagName.toLowerCase(),
        text: limitText(node.textContent, 200),
      })),
      links: Array.from(document.querySelectorAll("a[href]")).slice(0, 120).map(node => ({
        href: node.href,
        text: limitText(node.textContent, 160),
        aria_label: node.getAttribute("aria-label"),
      })),
      buttons: Array.from(document.querySelectorAll("button, [role=button], [role=menuitem], [role=tab]"))
        .slice(0, 120)
        .map(node => ({
          tag: node.tagName.toLowerCase(),
          role: node.getAttribute("role"),
          text: limitText(node.textContent, 160),
          aria_label: node.getAttribute("aria-label"),
          aria_selected: node.getAttribute("aria-selected"),
        })),
      forms: Array.from(document.querySelectorAll("form")).slice(0, 20).map((form, index) => ({
        index,
        action: form.getAttribute("action"),
        method: form.getAttribute("method"),
        input_count: form.querySelectorAll("input, select, textarea").length,
      })),
      landmarks: Array.from(document.querySelectorAll("header, nav, main, aside, footer, section"))
        .slice(0, 40)
        .map(node => ({
          tag: node.tagName.toLowerCase(),
          aria_label: node.getAttribute("aria-label"),
          text_sample: limitText(node.textContent, 200),
        })),
      assets: {
        stylesheets: Array.from(document.querySelectorAll('link[rel="stylesheet"], link[as="style"], link[rel="preload"][href]'))
          .slice(0, 80)
          .map(node => ({
            rel: node.getAttribute("rel"),
            as: node.getAttribute("as"),
            href: node.href || node.getAttribute("href"),
          })),
        scripts: Array.from(document.querySelectorAll("script[src]")).slice(0, 120).map(node => node.src),
        images: Array.from(document.images).slice(0, 120).map(node => ({
          src: node.currentSrc || node.src,
          alt: node.alt || null,
        })),
        fonts: Array.from(document.querySelectorAll('link[href*="font"], link[href*="woff"], link[href*="woff2"]'))
          .slice(0, 80)
          .map(node => node.href || node.getAttribute("href")),
      },
      counts: {
        anchors: document.querySelectorAll("a[href]").length,
        buttons: document.querySelectorAll("button, [role=button], [role=menuitem], [role=tab]").length,
        images: document.images.length,
        forms: document.forms.length,
      },
    };
  });

  const outputDir = pageOutputDir(page.url());
  const htmlPath = path.join(outputDir, "index.html");
  const screenshotPath = path.join(outputDir, "page.png");
  const metaPath = path.join(outputDir, "meta.json");
  const domPath = path.join(outputDir, "dom.json");
  const html = await page.content();

  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(htmlPath, html);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await fs.writeFile(
    metaPath,
    JSON.stringify(
      {
        captured_at: new Date().toISOString(),
        page_url: page.url(),
        title: metadata.title,
        discovered_links: metadata.hrefs,
        resource_urls: metadata.resource_urls,
      },
      null,
      2,
      ),
    );
  await fs.writeFile(domPath, JSON.stringify(domSnapshot, null, 2));

  routeManifest.push({
    url: page.url(),
    title: metadata.title,
    local_html: path.relative(outputRoot, htmlPath),
    screenshot: path.relative(outputRoot, screenshotPath),
    meta: path.relative(outputRoot, metaPath),
    dom: path.relative(outputRoot, domPath),
  });

  await log(
    `page saved: ${page.url()} -> ${path.relative(outputRoot, htmlPath)} | screenshot -> ${path.relative(outputRoot, screenshotPath)} | dom -> ${path.relative(outputRoot, domPath)}`,
  );

  for (const href of metadata.hrefs) {
    try {
      const discovered = new URL(normalizeRoute(href));
      if (
        discovered.origin === allowedOrigin &&
        discovered.pathname.startsWith("/app/") &&
        !seenRoutes.has(discovered.href)
      ) {
        queue.push(discovered.href);
        await log(`queued page: ${discovered.href}`);
      }
    } catch {
    }
  }
}

async function main() {
  await fs.mkdir(outputRoot, { recursive: true });
  await fs.mkdir(profileDir, { recursive: true });
  await fs.writeFile(logFilePath, "");
  await log(`capture started: output=${outputRoot}`);

  const context = await chromium.launchPersistentContext(profileDir, {
    channel: "chrome",
    headless: false,
    viewport: null,
  });

  try {
    const page = context.pages()[0] || (await context.newPage());
    page.on("response", response => {
      void writeAsset(response);
    });

    await page.goto(firstRoute, { waitUntil: "domcontentloaded" });
    await promptForLogin();

    while (queue.length > 0 && routeManifest.length < maxPages) {
      const targetUrl = queue.shift();
      if (!targetUrl || seenRoutes.has(targetUrl)) {
        continue;
      }

      const normalizedTarget = normalizeRoute(targetUrl);
      const parsedTarget = new URL(normalizedTarget);
      if (parsedTarget.origin !== allowedOrigin || !parsedTarget.pathname.startsWith("/app/")) {
        continue;
      }

      seenRoutes.add(normalizedTarget);
      await capturePage(page, normalizedTarget);
    }

    await Promise.all(assetWrites.values());

    const manifestPath = path.join(outputRoot, "manifest.json");
    await fs.writeFile(
      manifestPath,
      JSON.stringify(
        {
          generated_at: new Date().toISOString(),
          allowed_origin: allowedOrigin,
          max_pages: maxPages,
          pages: routeManifest,
          assets: assetManifest,
        },
        null,
        2,
      ),
    );

    await log(`capture finished: pages=${routeManifest.length} assets=${Object.keys(assetManifest).length}`);
    console.log("");
    console.log("Capture complete.");
    console.log(`- Log: ${logFilePath}`);
    console.log(`- Manifest: ${manifestPath}`);
    console.log(`- Pages: ${path.join(outputRoot, "pages")}/`);
    console.log(`- Assets: ${path.join(outputRoot, "assets")}/`);
  } finally {
    await context.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
