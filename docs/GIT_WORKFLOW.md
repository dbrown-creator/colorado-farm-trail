# Git Workflow & Conventions

> **Ownership:** Claude (Claude Code) manages git for this project — branching,
> commits, pushes, and opening PRs. The maintainer's only git responsibility is
> **reviewing and merging PRs**. Claude does **not** merge to `main` itself; it opens
> the PR and pings the maintainer when it's ready.

## The golden rules

1. **`main` is the live site.** GitHub Pages serves this repo's `main` branch (root)
   at **https://coloradofarmtrail.com**. Anything merged to `main` deploys within a
   minute or two. So `main` must always be in a deployable state.
2. **Never commit directly to `main`.** All changes go through a short-lived branch and
   a PR. (Exception history: the custom-domain migration was pushed straight to `main`
   before this workflow existed — that's the old way, don't repeat it.)
3. **Never `git add -A` / `git add .` in this repo.** The working tree carries a lot of
   pre-existing, unrelated noise (see "Known repo debt"). Always stage **explicit
   paths** so a commit contains only what it claims to.
4. **Never delete or edit the `CNAME` file** (`coloradofarmtrail.com`). Removing it
   drops the custom domain and the site falls back to the github.io URL.

## Branching

Short-lived topic branches off the latest `main`, deleted after merge.

Naming: `<type>/<short-slug>` — e.g. `feat/passport-checkin`, `fix/map-iframe-mobile`,
`docs/analytics-domain`, `chore/gitignore-artifacts`, `data/refresh-markets`.

Types: `feat`, `fix`, `docs`, `chore`, `data`, `refactor`.

```bash
git switch main && git pull
git switch -c docs/analytics-domain
# ...make changes...
git add docs/ANALYTICS.md          # explicit paths only
git commit -m "docs: update analytics for custom domain"
git push -u origin docs/analytics-domain
gh pr create --fill
```

## Commits

- **Conventional-commit style subject:** `<type>: <imperative summary>` (≤ ~72 chars).
  e.g. `fix: relink map iframe to new My Maps id`.
- Body explains **why** when it isn't obvious. Wrap ~72 cols.
- Every commit ends with the trailer:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```
- Keep commits focused — one logical change each. Don't bundle an unrelated cleanup
  into a feature commit.

## Pull requests

- Open with `gh pr create`. Title mirrors the main commit subject.
- PR body: what changed, why, and how it was verified (e.g. "previewed locally, map
  loads"). End the body with:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  ```
- After pushing, **tell the maintainer the PR is ready and link it.** Wait for them to
  merge. Do not self-merge.
- Prefer **squash merge** to keep `main` history clean (branches are small).
- After merge: delete the branch, `git switch main && git pull`.

## Deploy & verification

- No CI/Actions — GitHub Pages deploys `main` directly. There's no build step; the site
  is static (`index.html` + assets at repo root).
- For changes visible on the site, verify locally before opening the PR (open
  `index.html`, or serve it) — note that `navigator.share`/clipboard only work over
  https or localhost, not `file://`.
- After a PR merges, the change is live at coloradofarmtrail.com in ~1–2 min.

## Windows / line endings

Local checkout is Windows; git warns `LF will be replaced by CRLF`. This is harmless —
files are committed with LF. No action needed unless we add a `.gitattributes`.

## Known repo debt (do not silently "fix" in unrelated PRs)

- A batch of `data-compiled/**` files are tracked in history but **absent from disk**,
  so they perpetually show as deleted in `git status`. Whether these enrichment
  artifacts should be tracked or `.gitignore`d is a **maintainer decision** — handle it
  in its own dedicated `chore/` PR, never as a side effect.
- Untracked in the working tree: `Farm Fresh Map/`, `PHASE2.md`, `data-compiled/phase2/`,
  `source-data/phase2/`, `og-image.png`. Leave these alone until asked.
