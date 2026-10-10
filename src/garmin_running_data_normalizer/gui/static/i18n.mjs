// Message catalog helpers for the GUI page. They do not touch the DOM, so the
// tests in tests/gui_js run them with node --test.

export const DEFAULT_LANGUAGE = "en";

// Return the stored choice if it is available, otherwise the first browser
// language whose primary subtag is available, otherwise English.
export function chooseLanguage(available, stored, browserLanguages) {
  if (typeof stored === "string" && available.includes(stored)) {
    return stored;
  }
  for (const tag of browserLanguages ?? []) {
    if (typeof tag !== "string") {
      continue;
    }
    const primary = tag.split("-")[0].toLowerCase();
    if (available.includes(primary)) {
      return primary;
    }
  }
  return DEFAULT_LANGUAGE;
}

// Fill {name} placeholders; a placeholder without a value stays visible.
export function formatMessage(template, params = {}) {
  return template.replace(/\{([A-Za-z0-9_]+)\}/g, (placeholder, name) =>
    Object.hasOwn(params, name) ? String(params[name]) : placeholder,
  );
}

function lookup(catalogs, language, key) {
  if (!Object.hasOwn(catalogs, language)) {
    return undefined;
  }
  const catalog = catalogs[language];
  if (catalog === null || typeof catalog !== "object" || !Object.hasOwn(catalog, key)) {
    return undefined;
  }
  return typeof catalog[key] === "string" ? catalog[key] : undefined;
}

// Return the message in the language, falling back to English, then to the key.
export function translate(catalogs, language, key, params = {}) {
  const template =
    lookup(catalogs, language, key) ?? lookup(catalogs, DEFAULT_LANGUAGE, key) ?? key;
  return formatMessage(template, params);
}
