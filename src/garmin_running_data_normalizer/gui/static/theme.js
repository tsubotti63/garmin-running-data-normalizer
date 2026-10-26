// The colors that the person chose (stage G3a), set before the page is drawn,
// so that a page in Dark never shows Light first. This is a classic script in
// the head of the page, which runs before anything is drawn; app.mjs sets the
// colors again from the settings when the page starts.
//
// The choice is this tab's, or else the one that the launch put after the key
// in the fragment of the address, which the browser never sends; the values
// there are separated by "&", and read as app.mjs reads the key. The script
// writes nothing but the data-theme attribute of the root element.
(() => {
  const STORAGE = "theme";
  const CHOICES = ["auto", "light", "dark"];
  let choice = null;
  try {
    choice = window.sessionStorage.getItem(STORAGE);
  } catch {
    choice = null;
  }
  if (!CHOICES.includes(choice)) {
    const fromAddress = new URLSearchParams(window.location.hash.slice(1)).get("theme");
    choice = fromAddress === "light" || fromAddress === "dark" ? fromAddress : null;
    if (choice !== null) {
      try {
        // A reload has no fragment: app.mjs removes it with the key.
        window.sessionStorage.setItem(STORAGE, choice);
      } catch {
        // Without storage, a reload is drawn in the browser's colors until
        // the page has the settings.
      }
    }
  }
  if (choice === "light" || choice === "dark") {
    document.documentElement.dataset.theme = choice;
  }
})();
