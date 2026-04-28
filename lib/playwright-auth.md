# Playwright authentication pattern

Some sources (LinkedIn, Crunchbase, certain forums) require authentication. Dudu skills drive these sites with the VC's own browser session via the Playwright MCP server, never with bots or stored credentials.

## Tools

The Playwright MCP server exposes (among others):
- `mcp__playwright__browser_navigate` — open a URL
- `mcp__playwright__browser_snapshot` — read the current page
- `mcp__playwright__browser_click`, `browser_type`, `browser_fill_form` — interact
- `mcp__playwright__browser_wait_for` — wait for content
- `mcp__playwright__browser_close` — close the browser

If these tools are not available in the current Claude Code session, abort the run and tell the VC to install/enable the Playwright MCP server before retrying.

## Login-once pattern

Before scraping a gated site, the skill MUST:

1. Navigate to a known-public page on the site (e.g. `https://www.linkedin.com/feed/`).
2. Take a snapshot.
3. If the snapshot shows the login wall, instruct the VC:

   > I need you to log into LinkedIn in the Playwright browser window. I'll wait. Tell me "logged in" when you're ready.

4. Wait for the VC's confirmation message before proceeding.
5. Re-snapshot to verify the session is now authenticated.

Once authenticated, the session persists for the rest of the run. If a session expires mid-run, the skill detects the redirect to the login page, pauses, and re-prompts the VC.

## Pacing and rate limits

- Pace navigations at human speed: at minimum a 2-second wait between page loads on the same domain.
- Never open more than one tab on the same site at a time.
- Hard cap per skill per founder/competitor: ~30 page fetches. If you hit the cap, stop and report what you have.

## Terms of service

Skills must not initiate scraping campaigns. Driving the VC's own authenticated browser at human pace for personal due-diligence research is the only permitted pattern. If a skill author is tempted to "fan out" or "speed up", that's a sign the design is wrong.

## Artifact citations

Every fact pulled from a Playwright-driven page MUST be cited with the URL the data came from. If a URL would expose VC-private data (e.g. logged-in profile views), cite the source as `"<domain> (authenticated session)"` and include the public-equivalent URL when one exists.
