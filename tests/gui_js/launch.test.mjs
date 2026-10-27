// launch.mjs (stage G3b): the key of a launch and the calls of the server API,
// which both pages of the app use. The browser's window and fetch are
// replaced by small stand-ins for each test.
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import {
  ApiError,
  LAUNCH_KEY_HEADER,
  addressValue,
  callWithKey,
  readLaunchKey,
  readStorage,
  writeStorage,
} from "../../src/garmin_running_data_normalizer/gui/static/launch.mjs";

const realFetch = globalThis.fetch;

afterEach(() => {
  delete globalThis.window;
  globalThis.fetch = realFetch;
});

// A tab: its address, its history, and its storage, which can refuse.
function tab({ hash = "", pathname = "/view", stored = {}, storage = "works" } = {}) {
  const items = new Map(Object.entries(stored));
  const replaced = [];
  const refuse = () => {
    if (storage === "throws") {
      throw new Error("storage is not allowed");
    }
  };
  globalThis.window = {
    location: { hash, pathname },
    history: {
      replaceState(...args) {
        replaced.push(args);
      },
    },
    sessionStorage: {
      getItem(name) {
        refuse();
        return items.has(name) ? items.get(name) : null;
      },
      setItem(name, value) {
        refuse();
        items.set(name, String(value));
      },
    },
  };
  return { items, replaced };
}

test("the key of the address is kept for this tab and the address loses its fragment", () => {
  const { items, replaced } = tab({ hash: "#key=abc&theme=dark&output=run" });
  assert.equal(readLaunchKey(), "abc");
  assert.equal(items.get("launchKey"), "abc");
  assert.deepEqual(replaced, [[null, "", "/view"]]);
});

test("the output of the address is read before the key removes the fragment", () => {
  tab({ hash: "#key=abc&theme=dark&output=run" });
  assert.equal(addressValue("output"), "run");
  assert.equal(addressValue("other"), null);
  readLaunchKey();
  window.location.hash = "";
  assert.equal(addressValue("output"), null);
});

test("without a key in the address, the key of this tab is used and the address stays", () => {
  const { replaced } = tab({ hash: "#theme=dark", stored: { launchKey: "kept" } });
  assert.equal(readLaunchKey(), "kept");
  assert.deepEqual(replaced, []);
  tab({ hash: "" });
  assert.equal(readLaunchKey(), null);
  // An escaped "&" is part of the key.
  tab({ hash: "#key=a%26output%3Drun" });
  assert.equal(readLaunchKey(), "a&output=run");
});

test("without storage, the key of the address still works", () => {
  const { replaced } = tab({ hash: "#key=abc", storage: "throws" });
  assert.equal(readLaunchKey(), "abc");
  assert.deepEqual(replaced, [[null, "", "/view"]]);
  assert.equal(readStorage("launchKey"), null);
  writeStorage("language", "ja");
});

// The requests that a stand-in fetch was given, and its answer.
function answering(status, body) {
  const requests = [];
  globalThis.fetch = async (path, options) => {
    requests.push([path, options]);
    return {
      ok: status === 200,
      status,
      async json() {
        if (body === undefined) {
          throw new SyntaxError("not JSON");
        }
        return body;
      },
    };
  };
  return requests;
}

test("a request is a POST of JSON with the key, never cached and without cookies", async () => {
  const requests = answering(200, { status: "ok" });
  assert.deepEqual(await callWithKey("abc", "/api/view/open", { output: "run" }), { status: "ok" });
  assert.deepEqual(requests, [
    [
      "/api/view/open",
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Launch-Key": "abc" },
        body: '{"output":"run"}',
        cache: "no-store",
        credentials: "omit",
      },
    ],
  ]);
  assert.equal(LAUNCH_KEY_HEADER, "X-Launch-Key");
  // Without a payload, the body is an empty object.
  await callWithKey("abc", "/api/heartbeat");
  assert.equal(requests[1][1].body, "{}");
});

test("without a key, nothing is sent and the page reads it as refused", async () => {
  const requests = answering(200, {});
  for (const key of [null, ""]) {
    await assert.rejects(callWithKey(key, "/api/status"), (error) => {
      assert.ok(error instanceof ApiError);
      assert.deepEqual([error.status, error.code, error.detail], [403, null, null]);
      return true;
    });
  }
  assert.deepEqual(requests, []);
});

test("an answer other than 200 gives its code, and the version that made an output", async () => {
  answering(422, { error: "OUTPUT_OTHER_VERSION", version: "2.0.1" });
  await assert.rejects(callWithKey("abc", "/api/view/open"), (error) => {
    assert.deepEqual([error.status, error.code, error.detail], [422, "OUTPUT_OTHER_VERSION", { version: "2.0.1" }]);
    return true;
  });
  answering(409, { error: "VIEW_NOT_OPEN" });
  await assert.rejects(callWithKey("abc", "/api/view/series"), (error) => {
    assert.deepEqual([error.status, error.code, error.detail], [409, "VIEW_NOT_OPEN", null]);
    return true;
  });
  // A refused key, an answer that is not JSON, and values of another form.
  answering(403, undefined);
  await assert.rejects(callWithKey("abc", "/api/status"), (error) => {
    assert.deepEqual([error.status, error.code, error.detail], [403, null, null]);
    return true;
  });
  answering(422, { error: 7, version: 2 });
  await assert.rejects(callWithKey("abc", "/api/status"), (error) => {
    assert.deepEqual([error.code, error.detail], [null, null]);
    return true;
  });
});

test("an answer of 200 that is not JSON is null", async () => {
  answering(200, undefined);
  assert.equal(await callWithKey("abc", "/api/heartbeat"), null);
});
