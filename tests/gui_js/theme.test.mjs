// theme.js (stage G3a): the colors that the person chose, set before the page
// is drawn, from this tab's storage or else from the fragment of the address
// that a launch opens. The script runs as the page runs it, in a context of
// its own, with a tab's storage and address. Everything that it touches is
// watched, so that a script that writes more than the data-theme attribute of
// the root element fails.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

import * as flow from "../../src/garmin_running_data_normalizer/gui/static/flow.mjs";

const SOURCE = readFileSync(
  new URL("../../src/garmin_running_data_normalizer/gui/static/theme.js", import.meta.url),
  "utf8",
);

// An object that tells what was read of it beyond the names it may read, and
// what was written or removed.
function watched(target, name, readable, touched) {
  return new Proxy(target, {
    get(object, property) {
      if (!readable.includes(property)) {
        touched.push(`read ${name}.${String(property)}`);
      }
      return object[property];
    },
    set(object, property, value) {
      touched.push(`write ${name}.${String(property)}`);
      object[property] = value;
      return true;
    },
    defineProperty(object, property, descriptor) {
      touched.push(`define ${name}.${String(property)}`);
      return Reflect.defineProperty(object, property, descriptor);
    },
    deleteProperty(object, property) {
      touched.push(`delete ${name}.${String(property)}`);
      return Reflect.deleteProperty(object, property);
    },
  });
}

function run({ stored = null, hash = "", storage = "works" } = {}) {
  const items = new Map(stored === null ? [] : [["theme", stored]]);
  const touched = [];
  const sessionStorage = {
    getItem(name) {
      if (storage === "throws") {
        throw new Error("storage is not allowed");
      }
      return items.has(name) ? items.get(name) : null;
    },
    setItem(name, value) {
      if (storage === "throws") {
        throw new Error("storage is not allowed");
      }
      items.set(name, String(value));
    },
  };
  const values = {};
  const dataset = new Proxy(values, {
    set(object, property, value) {
      if (property !== "theme") {
        touched.push(`write dataset.${String(property)}`);
      }
      object[property] = value;
      return true;
    },
    deleteProperty(object, property) {
      touched.push(`delete dataset.${String(property)}`);
      return Reflect.deleteProperty(object, property);
    },
  });
  const documentElement = watched({ dataset }, "documentElement", ["dataset"], touched);
  const document = watched({ documentElement }, "document", ["documentElement"], touched);
  const location = watched({ hash }, "location", ["hash"], touched);
  const window = watched({ sessionStorage, location }, "window", ["sessionStorage", "location"], touched);
  vm.runInNewContext(SOURCE, { window, document, URLSearchParams });
  assert.deepEqual(touched, [], "theme.js touched more than the data-theme attribute");
  return { theme: values.theme, attributes: Object.keys(values), stored: items.get("theme") ?? null };
}

test("this tab's choice comes first, then the colors in the address", () => {
  assert.deepEqual(run({ stored: "light", hash: "#key=k&theme=dark" }), { theme: "light", attributes: ["theme"], stored: "light" });
  assert.deepEqual(run({ stored: "dark" }), { theme: "dark", attributes: ["theme"], stored: "dark" });
  // "auto" in this tab follows the browser, also when the address says Dark.
  assert.deepEqual(run({ stored: "auto", hash: "#key=k&theme=dark" }), { theme: undefined, attributes: [], stored: "auto" });
  // The address of a launch: its colors go to this tab's storage for a
  // reload, which has no fragment.
  assert.deepEqual(run({ hash: "#key=k&theme=dark" }), { theme: "dark", attributes: ["theme"], stored: "dark" });
  assert.deepEqual(run({ hash: "#theme=light&key=k" }), { theme: "light", attributes: ["theme"], stored: "light" });
  assert.deepEqual(run({ hash: "#key=k" }), { theme: undefined, attributes: [], stored: null });
  assert.deepEqual(run(), { theme: undefined, attributes: [], stored: null });
});

test("values of another form are not taken", () => {
  assert.deepEqual(run({ stored: "blue", hash: "#key=k&theme=dark" }), { theme: "dark", attributes: ["theme"], stored: "dark" });
  for (const hash of ["#key=k&theme=blue", "#key=k&theme=Dark", "#key=k&theme=auto", "#key=k&theme=", "#theme"]) {
    assert.deepEqual(run({ hash }), { theme: undefined, attributes: [], stored: null }, hash);
  }
});

test("without storage, the address still gives the colors", () => {
  assert.deepEqual(run({ storage: "throws", hash: "#key=k&theme=dark" }), { theme: "dark", attributes: ["theme"], stored: null });
  assert.deepEqual(run({ storage: "throws" }), { theme: undefined, attributes: [], stored: null });
});

test("theme.js reads the fragment as the page reads the key", () => {
  for (const hash of ["#key=k&theme=dark", "#theme=light&key=k", "#key=a%26theme%3Ddark", "#key=k&theme=light&theme=dark", "#key=k"]) {
    const theme = flow.fragmentValue(hash, "theme");
    assert.equal(run({ hash }).theme, theme === "light" || theme === "dark" ? theme : undefined, hash);
  }
  // A key with "&theme=dark" in it, escaped, is a key and no colors.
  assert.equal(flow.fragmentValue("#key=a%26theme%3Ddark", "key"), "a&theme=dark");
  assert.equal(run({ hash: "#key=a%26theme%3Ddark" }).theme, undefined);
});
