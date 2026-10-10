import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  DEFAULT_LANGUAGE,
  chooseLanguage,
  formatMessage,
  translate,
} from "../../src/garmin_running_data_normalizer/gui/static/i18n.mjs";

const AVAILABLE = ["en", "ja"];

test("English is the default language", () => {
  assert.equal(DEFAULT_LANGUAGE, "en");
});

test("a stored choice wins over the browser languages", () => {
  assert.equal(chooseLanguage(AVAILABLE, "ja", ["en-US"]), "ja");
  assert.equal(chooseLanguage(AVAILABLE, "en", ["ja-JP"]), "en");
});

test("the first available browser language is chosen by its primary subtag", () => {
  assert.equal(chooseLanguage(AVAILABLE, null, ["fr-FR", "ja-JP", "en-US"]), "ja");
  assert.equal(chooseLanguage(AVAILABLE, null, ["EN-gb"]), "en");
  assert.equal(chooseLanguage(AVAILABLE, "de", ["ja"]), "ja");
});

test("unavailable or missing languages fall back to English", () => {
  assert.equal(chooseLanguage(AVAILABLE, "de", ["fr-FR"]), "en");
  assert.equal(chooseLanguage(AVAILABLE, undefined, []), "en");
  assert.equal(chooseLanguage(AVAILABLE, null, undefined), "en");
  assert.equal(chooseLanguage(AVAILABLE, null, [null, 7, ""]), "en");
});

test("placeholders are filled by name and unknown ones stay visible", () => {
  assert.equal(formatMessage("Version {version}", { version: "1.7.0" }), "Version 1.7.0");
  assert.equal(formatMessage("{a} and {b}", { a: "x" }), "x and {b}");
  assert.equal(formatMessage("{count} files", { count: 3 }), "3 files");
  assert.equal(formatMessage("{value}", { value: "$& and $1" }), "$& and $1");
  assert.equal(formatMessage("{toString}", {}), "{toString}");
  assert.equal(formatMessage("No placeholder"), "No placeholder");
});

test("missing messages fall back to English, then to the key", () => {
  const catalogs = {
    en: { "app.title": "Title", "app.version": "Version {version}" },
    ja: { "app.title": "タイトル" },
  };
  assert.equal(translate(catalogs, "ja", "app.title"), "タイトル");
  assert.equal(translate(catalogs, "ja", "app.version", { version: "2.0.0" }), "Version 2.0.0");
  assert.equal(translate(catalogs, "fr", "app.title"), "Title");
  assert.equal(translate(catalogs, "ja", "app.unknown"), "app.unknown");
  assert.equal(translate({}, "ja", "app.title"), "app.title");
});

test("inherited properties and non-text values are not messages", () => {
  assert.equal(translate({ en: {} }, "en", "toString"), "toString");
  assert.equal(translate({ en: { "a.b": "x" } }, "__proto__", "a.b"), "x");
  assert.equal(translate({ en: { "a.b": 5 }, ja: { "a.b": null } }, "ja", "a.b"), "a.b");
});

test("the page script parses as a module", () => {
  const appPath = fileURLToPath(
    new URL("../../src/garmin_running_data_normalizer/gui/static/app.mjs", import.meta.url),
  );
  const result = spawnSync(process.execPath, ["--check", appPath], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
});
