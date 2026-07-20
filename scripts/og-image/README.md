# Social-share image (`og-image.png`)

`../../og-image.png` is the 1200×630 card shown when the site is shared (the
`og:image` / `twitter:image` in `index.html`). It's rendered from
[`card.html`](card.html) — a self-contained page (no external fonts/tiles) so a
headless browser captures it instantly and identically every time.

## Regenerate

From the repo root, with Chrome installed:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 `
  --window-size=1200,630 `
  --screenshot="og-image.png" `
  "file:///$((Resolve-Path scripts/og-image/card.html).Path -replace '\\','/')"
```

(macOS/Linux: swap the Chrome path for `google-chrome` / `chromium` and use a
normal `file://` URL.)

Edit `card.html` to change the design, then re-run the command. Keep the output
at **1200×630** to match the `og:image:width` / `height` tags in `index.html`.
