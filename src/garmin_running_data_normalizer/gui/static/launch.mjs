// The key of a launch and the calls of the server API, for the two pages of
// this app (stage G3b): the normalization page (app.mjs) and the view page
// (view.mjs) read the key and call the API here only, so that these rules of
// the launch are written once. The state of a page's connection stays in the
// page.

import { fragmentValue } from "./flow.mjs";

export const LAUNCH_KEY_HEADER = "X-Launch-Key";
const LAUNCH_KEY_STORAGE = "launchKey";

export class ApiError extends Error {
  constructor(status, code, detail = null) {
    super(`API request failed with HTTP ${status}`);
    this.status = status;
    this.code = code;
    // The version that made an output that this version cannot check
    // (stage B5b).
    this.detail = detail;
  }
}

export function readStorage(name) {
  try {
    return window.sessionStorage.getItem(name);
  } catch {
    return null;
  }
}

export function writeStorage(name, value) {
  try {
    window.sessionStorage.setItem(name, value);
  } catch {
    // Without storage, the page still works until it is reloaded.
  }
}

// The key arrives in the URL fragment, which is never sent to the server, and
// the colors that the settings remember after it (stage G3a). Keep the key for
// this tab only, and remove the fragment, the colors too, from the address bar
// and the history.
export function readLaunchKey() {
  const fromFragment = fragmentValue(window.location.hash, "key");
  if (fromFragment) {
    writeStorage(LAUNCH_KEY_STORAGE, fromFragment);
    window.history.replaceState(null, "", window.location.pathname);
    return fromFragment;
  }
  return readStorage(LAUNCH_KEY_STORAGE);
}

// What the address of a page says besides the key and the colors (stage
// G3b): the output that the view page opens first. Read it before the key,
// whose reading removes the fragment.
export function addressValue(name) {
  return fragmentValue(window.location.hash, name);
}

// A request of the API: a POST of JSON with the key, never from the cache and
// without the cookies of the browser. An answer other than 200 throws an
// ApiError with the code of the server; a page without the key throws one as
// the server would refuse it. A request kept alive goes on after the page is
// hidden or closed (stage K2 of v2.2.0: the view that waits to be remembered).
export async function callWithKey(key, path, payload = {}, { keepalive = false } = {}) {
  if (!key) {
    throw new ApiError(403, null);
  }
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", [LAUNCH_KEY_HEADER]: key },
    body: JSON.stringify(payload),
    cache: "no-store",
    credentials: "omit",
    ...(keepalive ? { keepalive: true } : {}),
  });
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    throw new ApiError(
      response.status,
      typeof body?.error === "string" ? body.error : null,
      typeof body?.version === "string" ? { version: body.version } : null,
    );
  }
  return body;
}
