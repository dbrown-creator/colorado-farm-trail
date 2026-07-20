# Social-share image (`og-image.png`)

`../../og-image.png` is the 1200×630 card shown when the site is shared (the
`og:image` / `twitter:image` in `index.html`). It's a **render of the actual
landing page** at 1200×630, so the share preview always matches the live design
(branding over the map, in the viewer's default theme).

## Regenerate

1. Serve the site locally from the repo root (the map's `fetch` needs http, not
   `file://`):

   ```powershell
   python -m http.server 8899 --bind 127.0.0.1
   ```

2. Render the landing page with headless Chrome. The isolated `--user-data-dir`
   avoids clashing with an already-open Chrome, and `--virtual-time-budget` gives
   the map tiles + markers time to finish loading before the shot:

   ```powershell
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" `
     --headless=old --disable-gpu --no-first-run `
     --user-data-dir="$env:TEMP\cft-og-render" `
     --hide-scrollbars --force-device-scale-factor=1 --window-size=1200,630 `
     --virtual-time-budget=15000 `
     --screenshot="og-image.png" `
     "http://127.0.0.1:8899/index.html"
   ```

The page loads in its **landing state** (hero branding over the map) — exactly
what we want for the card. Keep the output at **1200×630** to match the
`og:image:width` / `height` tags in `index.html`.

> Tip: for a lighter/dark variant, run the render with the OS (or Chrome
> `--force-dark-mode`) set accordingly — the page is theme-aware.
