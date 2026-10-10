// Page logic for the GUI. Visible text comes from the message catalogs.
// Message keys appear here only as literal strings, so that tests can check
// that every key used here exists in the catalogs and that every key is used.

import { DEFAULT_LANGUAGE, chooseLanguage, translate } from "./i18n.mjs";

const LANGUAGES = ["en", "ja"];
const LAUNCH_KEY_HEADER = "X-Launch-Key";
const LAUNCH_KEY_STORAGE = "launchKey";
const LANGUAGE_STORAGE = "language";
const HEARTBEAT_INTERVAL_MS = 30000;

const versionElement = document.getElementById("product-version");
const statusElement = document.getElementById("connection-status");
const languageSelect = document.getElementById("language-select");
const quitButton = document.getElementById("quit-button");

const state = {
  catalogs: {},
  language: DEFAULT_LANGUAGE,
  launchKey: null,
  productVersion: null,
  statusKey: null,
  heartbeatTimer: null,
};

class ApiError extends Error {
  constructor(status) {
    super(`API request failed with HTTP ${status}`);
    this.status = status;
  }
}

function t(key, params) {
  return translate(state.catalogs, state.language, key, params);
}

function readStorage(name) {
  try {
    return window.sessionStorage.getItem(name);
  } catch {
    return null;
  }
}

function writeStorage(name, value) {
  try {
    window.sessionStorage.setItem(name, value);
  } catch {
    // Without storage, the page still works until it is reloaded.
  }
}

// The key arrives in the URL fragment, which is never sent to the server. Keep
// it for this tab only, and remove it from the address bar and the history.
function readLaunchKey() {
  const fromFragment = new URLSearchParams(window.location.hash.slice(1)).get("key");
  if (fromFragment) {
    writeStorage(LAUNCH_KEY_STORAGE, fromFragment);
    window.history.replaceState(null, "", window.location.pathname);
    return fromFragment;
  }
  return readStorage(LAUNCH_KEY_STORAGE);
}

async function loadCatalog(language) {
  try {
    const response = await fetch(`/i18n/${language}.json`, {
      cache: "no-store",
      credentials: "omit",
    });
    return response.ok ? await response.json() : {};
  } catch {
    return {};
  }
}

async function callApi(path) {
  if (!state.launchKey) {
    throw new ApiError(403);
  }
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", [LAUNCH_KEY_HEADER]: state.launchKey },
    body: "{}",
    cache: "no-store",
    credentials: "omit",
  });
  if (!response.ok) {
    throw new ApiError(response.status);
  }
  return response.json();
}

function render() {
  document.documentElement.lang = state.language;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  versionElement.textContent =
    state.productVersion === null ? "" : t("app.version", { version: state.productVersion });
  statusElement.textContent = state.statusKey === null ? "" : t(state.statusKey);
  for (const option of languageSelect.options) {
    option.textContent = translate(state.catalogs, option.value, "language.name");
  }
  languageSelect.value = state.language;
}

function setStatus(key) {
  state.statusKey = key;
  render();
}

function stopHeartbeat() {
  if (state.heartbeatTimer !== null) {
    window.clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = null;
  }
}

function showFailure(error) {
  stopHeartbeat();
  quitButton.disabled = true;
  const unauthorized = error instanceof ApiError && error.status === 403;
  setStatus(unauthorized ? "status.unauthorized" : "status.unavailable");
}

function startHeartbeat() {
  state.heartbeatTimer = window.setInterval(() => {
    callApi("/api/heartbeat").catch(showFailure);
  }, HEARTBEAT_INTERVAL_MS);
}

async function quit() {
  quitButton.disabled = true;
  stopHeartbeat();
  try {
    await callApi("/api/shutdown");
    setStatus("status.stopped");
  } catch (error) {
    showFailure(error);
  }
}

function changeLanguage(language) {
  if (LANGUAGES.includes(language)) {
    state.language = language;
    writeStorage(LANGUAGE_STORAGE, language);
    render();
  }
}

async function start() {
  state.launchKey = readLaunchKey();
  const catalogs = await Promise.all(LANGUAGES.map(loadCatalog));
  state.catalogs = Object.fromEntries(
    LANGUAGES.map((language, index) => [language, catalogs[index]]),
  );
  state.language = chooseLanguage(
    LANGUAGES,
    readStorage(LANGUAGE_STORAGE),
    navigator.languages ?? [navigator.language],
  );
  for (const language of LANGUAGES) {
    const option = document.createElement("option");
    option.value = language;
    option.lang = language;
    languageSelect.append(option);
  }
  languageSelect.addEventListener("change", () => changeLanguage(languageSelect.value));
  quitButton.addEventListener("click", quit);
  render();
  try {
    const status = await callApi("/api/status");
    state.productVersion =
      typeof status.product_version === "string" ? status.product_version : null;
    quitButton.disabled = false;
    setStatus("status.connected");
    startHeartbeat();
  } catch (error) {
    showFailure(error);
  }
}

start();
