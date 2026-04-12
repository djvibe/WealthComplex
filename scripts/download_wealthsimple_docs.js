#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const readline = require("node:readline/promises");
const { stdin, stdout, env } = require("node:process");
const { chromium } = require("/home/djvibe/.nvm/versions/node/v20.20.0/lib/node_modules/@playwright/cli/node_modules/playwright");

const rootDir = path.resolve(__dirname, "..");
const profileDir = env.PROFILE_DIR || path.join(rootDir, "working", "browser-profiles", "wealthsimple-capture");
const outputDir = env.OUTPUT_DIR || path.join(rootDir, "working", "wealthsimple-docs");
const logFile = env.LOG_FILE || path.join(outputDir, "download.log");
const docsUrl =
  process.argv[2] ||
  env.DOCS_URL ||
  "https://my.wealthsimple.com/app/docs";
const loadMoreLimit = Number.parseInt(env.LOAD_MORE_LIMIT || "20", 10);
const maxDocs = Number.parseInt(env.MAX_DOCS || "200", 10);
const quickFilterSweep = env.QUICK_FILTER_SWEEP !== "0";
const startDate = env.START_DATE || "";
const endDate = env.END_DATE || "";
const quickFilterNames = [
  "2025 taxes",
  "Account documents",
  "Performance statements",
  "2024 taxes",
  "My uploads",
];
const documentTypePattern = /(tax document|account document|performance statement|my upload|uploaded document)/i;

function safeName(value) {
  return value
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "") || "document";
}

function hash(value) {
  return crypto.createHash("sha1").update(value).digest("hex").slice(0, 10);
}

async function log(message) {
  const line = `[docs] ${message}`;
  console.log(line);
  await fs.appendFile(logFile, `${line}\n`);
}

async function promptForReady() {
  console.log(`Documents URL: ${docsUrl}`);
  console.log(`Output directory: ${outputDir}`);
  console.log(`Profile directory: ${profileDir}`);
  console.log("If Wealthsimple shows a login page, complete login first.");
  console.log("Then navigate to the documents view or let the script do it after login.");
  console.log("Review the browser window, adjust filters if needed, then press Enter here.");
  const rl = readline.createInterface({ input: stdin, output: stdout });
  await rl.question("Press Enter when the documents list is ready... ");
  rl.close();
}

async function pageState(page) {
  return await page.evaluate(() => ({
    href: location.href,
    title: document.title,
    body: (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 500),
  }));
}

async function findBestWealthsimplePage(context) {
  const candidates = [];
  for (const page of context.pages()) {
    try {
      const state = await pageState(page);
      const url = state.href || "";
      if (!url.startsWith("https://my.wealthsimple.com/")) {
        continue;
      }
      const score =
        url.includes("/app/docs") ? 4 :
        url.includes("/app/login") ? 1 :
        url.includes("/app/") ? 3 :
        2;
      candidates.push({ page, state, score });
    } catch {
    }
  }

  candidates.sort((a, b) => b.score - a.score);
  return candidates[0] || null;
}

async function ensureDocsPage(page) {
  const targetUrl = new URL(docsUrl);
  if (startDate) {
    targetUrl.searchParams.set("startDate", startDate);
  }
  if (endDate) {
    targetUrl.searchParams.set("endDate", endDate);
  }
  await page.goto(targetUrl.toString(), { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
}

async function waitForDocsReady(page) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const state = await pageState(page);
    const onDocs = state.href.startsWith("https://my.wealthsimple.com/app/docs");
    const looksReady =
      state.body.includes("Documents") &&
      (
        state.body.includes("Request documents") ||
        state.body.includes("Upload documents") ||
        state.body.includes("Load more") ||
        state.body.includes("Open")
      );
    if (onDocs && looksReady) {
      return state;
    }
    await page.waitForTimeout(1000);
  }
  return await pageState(page);
}

async function loadAllDocs(page) {
  for (let i = 0; i < loadMoreLimit; i += 1) {
    const button = page.getByRole("button", { name: "Load more" });
    if (!(await button.count())) {
      break;
    }
    if (!(await button.first().isVisible().catch(() => false))) {
      break;
    }
    await button.first().click();
    await page.waitForTimeout(1500);
    await log(`clicked Load more (${i + 1})`);
  }
}

async function clearFilters(page) {
  const clearButton = page.getByRole("button", { name: "Clear" });
  if (!(await clearButton.count())) {
    return;
  }
  const visible = await clearButton.first().isVisible().catch(() => false);
  if (!visible) {
    return;
  }
  await clearButton.first().click();
  await page.waitForTimeout(1200);
  await page.waitForLoadState("networkidle").catch(() => {});
  await log("cleared active document filters");
}

async function applyQuickFilter(page, name) {
  const button = page.getByRole("button", { name });
  if (!(await button.count())) {
    await log(`quick filter not found: ${name}`);
    return false;
  }
  await button.first().click();
  await page.waitForTimeout(1800);
  await page.waitForLoadState("networkidle").catch(() => {});
  await log(`applied quick filter: ${name}`);
  return true;
}

async function collectDocCandidates(page) {
  return await page.evaluate(() => {
    const text = value => (value || "").replace(/\s+/g, " ").trim();
    const buttons = Array.from(document.querySelectorAll("button"));
    const openButtons = buttons.filter(button => text(button.textContent) === "Open");
    return openButtons.map((button, index) => {
      const card =
        button.parentElement?.parentElement?.parentElement ||
        button.closest('[role="listitem"]') ||
        button.closest("li") ||
        button.closest("article") ||
        button.closest("section") ||
        button.parentElement;
      const cardText = text(card?.innerText || "");
      return {
        index,
        label: text(button.getAttribute("aria-label")) || "Open",
        card_text: cardText.slice(0, 500),
      };
    }).filter(candidate => /tax document|account document|performance statement|my upload|uploaded document/i.test(candidate.card_text));
  });
}

async function findOpenButtonIndex(page, cardText) {
  return await page.evaluate(targetCardText => {
    const text = value => (value || "").replace(/\s+/g, " ").trim();
    const buttons = Array.from(document.querySelectorAll("button"));
    const openButtons = buttons.filter(button => text(button.textContent) === "Open");
    return openButtons.findIndex(button => {
      const card =
        button.parentElement?.parentElement?.parentElement ||
        button.closest('[role="listitem"]') ||
        button.closest("li") ||
        button.closest("article") ||
        button.closest("section") ||
        button.parentElement;
      const currentText = text(card?.innerText || "").slice(0, 500);
      const looksLikeDocument = /tax document|account document|performance statement|my upload|uploaded document/i.test(currentText);
      return looksLikeDocument && currentText === targetCardText;
    });
  }, cardText);
}

async function waitForPopupTarget(popup) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    const url = popup.url();
    if (url && url !== "about:blank" && /^https?:/i.test(url)) {
      return url;
    }
    await popup.waitForTimeout(500).catch(() => {});
  }
  return popup.url();
}

async function writeManifest(manifest) {
  const manifestPath = path.join(outputDir, "manifest.json");
  await fs.writeFile(
    manifestPath,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        docs_url: docsUrl,
        start_date: startDate || null,
        end_date: endDate || null,
        count: manifest.length,
        files: manifest,
      },
      null,
      2,
    ),
  );
  return manifestPath;
}

async function downloadDocFromCurrentList(context, page, doc, index, total) {
  if (!documentTypePattern.test(doc.card_text)) {
    await log(`skipping non-document candidate: ${doc.card_text}`);
    return {
      index: index + 1,
      file: null,
      source_url: null,
      card_text: doc.card_text,
      filters: doc.filters,
      error: "candidate did not match document row pattern",
    };
  }

  const buttonIndex = await findOpenButtonIndex(page, doc.card_text);
  if (buttonIndex < 0) {
    await log(`document not found in current list: ${doc.card_text}`);
    return {
      index: index + 1,
      file: null,
      source_url: null,
      card_text: doc.card_text,
      filters: doc.filters,
      error: "open button not found",
    };
  }

  const openButton = page.getByRole("button", { name: "Open" }).nth(buttonIndex);
  const popupPromise = context.waitForEvent("page", { timeout: 15000 });
  await openButton.click();

  let popup;
  try {
    popup = await popupPromise;
  } catch {
    await log(`popup timeout for document ${index + 1}: ${doc.card_text}`);
    return {
      index: index + 1,
      file: null,
      source_url: null,
      card_text: doc.card_text,
      filters: doc.filters,
      error: "popup timeout",
    };
  }

  await popup.waitForLoadState("domcontentloaded").catch(() => {});
  const pdfUrl = await waitForPopupTarget(popup);
  if (!pdfUrl || pdfUrl === "about:blank" || !/^https?:/i.test(pdfUrl)) {
    await log(`popup did not resolve to a document URL for ${doc.card_text}: ${pdfUrl || "<empty>"}`);
    await popup.close().catch(() => {});
    return {
      index: index + 1,
      file: null,
      source_url: pdfUrl || null,
      card_text: doc.card_text,
      filters: doc.filters,
      error: "popup did not resolve to a document URL",
    };
  }
  const titlePart = safeName(doc.card_text.split(" Tax document ")[0].slice(0, 120));
  const fileName = `${String(index + 1).padStart(3, "0")}-${titlePart}-${hash(pdfUrl)}.pdf`;
  const filePath = path.join(outputDir, fileName);

  try {
    await downloadToFile(pdfUrl, filePath);
    await log(`downloaded ${index + 1}/${total}: ${fileName}`);
    return {
      index: index + 1,
      file: fileName,
      source_url: pdfUrl,
      card_text: doc.card_text,
      filters: doc.filters,
    };
  } catch (error) {
    await log(`download failed ${index + 1}/${total}: ${String(error)}`);
    return {
      index: index + 1,
      file: null,
      source_url: pdfUrl,
      card_text: doc.card_text,
      filters: doc.filters,
      error: String(error),
    };
  } finally {
    await popup.close().catch(() => {});
  }
}

async function downloadToFile(url, destination) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const arrayBuffer = await response.arrayBuffer();
  await fs.writeFile(destination, Buffer.from(arrayBuffer));
}

async function main() {
  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(logFile, "");

  const context = await chromium.launchPersistentContext(profileDir, {
    channel: "chrome",
    headless: false,
    viewport: null,
  });

  try {
    const existing = await findBestWealthsimplePage(context);
    const page = existing?.page || context.pages()[0] || (await context.newPage());
    if (existing) {
      await log(`reusing existing tab: ${existing.state.href}`);
    } else {
      await log("no existing Wealthsimple tab found; opening documents page");
    }

    const current = await pageState(page).catch(() => null);
    if (!current || !current.href.startsWith("https://my.wealthsimple.com/app/docs")) {
      await ensureDocsPage(page);
    }

    await promptForReady();
    await ensureDocsPage(page);
    const readyState = await waitForDocsReady(page);
    await log(`page after login/ready check: ${readyState.href}`);

    if (!readyState.href.startsWith("https://my.wealthsimple.com/app/docs")) {
      throw new Error(`Expected documents page after login, got ${readyState.href}`);
    }

    await clearFilters(page);

    const sweepFilters = quickFilterSweep ? [null, ...quickFilterNames] : [null];
    const docsMap = new Map();

    for (const filterName of sweepFilters) {
      await page.goto(docsUrl, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle").catch(() => {});
      await page.waitForTimeout(1500);
      await clearFilters(page);

      if (filterName) {
        const applied = await applyQuickFilter(page, filterName);
        if (!applied) {
          continue;
        }
      } else {
        await log("collecting from unfiltered documents view");
      }

      await loadAllDocs(page);
      const docs = await collectDocCandidates(page);
      for (const doc of docs) {
        const key = doc.card_text;
        if (!docsMap.has(key)) {
          docsMap.set(key, {
            ...doc,
            filters: filterName ? [filterName] : ["all"],
          });
        } else if (filterName) {
          const existing = docsMap.get(key);
          if (!existing.filters.includes(filterName)) {
            existing.filters.push(filterName);
          }
        }
      }
      await log(`collected ${docs.length} openable documents from ${filterName || "all"}`);
    }

    const manifest = [];
    let downloadCount = 0;

    for (const filterName of sweepFilters) {
      if (downloadCount >= maxDocs) {
        break;
      }

      await ensureDocsPage(page);
      await clearFilters(page);

      if (filterName) {
        const applied = await applyQuickFilter(page, filterName);
        if (!applied) {
          continue;
        }
      } else {
        await log("collecting from unfiltered documents view");
      }

      await loadAllDocs(page);
      const docs = await collectDocCandidates(page);
      const newDocs = [];
      for (const doc of docs) {
        const key = doc.card_text;
        if (!docsMap.has(key)) {
          const record = {
            ...doc,
            filters: filterName ? [filterName] : ["all"],
          };
          docsMap.set(key, record);
          newDocs.push(record);
        } else if (filterName) {
          const existing = docsMap.get(key);
          if (!existing.filters.includes(filterName)) {
            existing.filters.push(filterName);
          }
        }
      }
      await log(`collected ${docs.length} openable documents from ${filterName || "all"}`);

      for (const doc of newDocs) {
        if (downloadCount >= maxDocs) {
          break;
        }
        const result = await downloadDocFromCurrentList(context, page, doc, downloadCount, maxDocs);
        manifest.push(result);
        downloadCount += 1;
        await writeManifest(manifest);
      }
    }

    await log(`finished with ${manifest.length} attempted downloads`);
    const manifestPath = await writeManifest(manifest);

    console.log("");
    console.log("Documents download complete.");
    console.log(`- Log: ${logFile}`);
    console.log(`- Manifest: ${manifestPath}`);
    console.log(`- Files: ${outputDir}/`);
  } finally {
    await context.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
