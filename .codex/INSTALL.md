# Installing dudu for Codex

Enable the dudu VC diligence skills in Codex via native skill discovery. Clone the repo, symlink the skills directory, restart Codex.

## Prerequisites

- OpenAI Codex CLI
- Git
- The Playwright MCP server installed and enabled (skills that touch LinkedIn, Crunchbase, etc. drive your authenticated browser session through it)

## Installation

1. **Clone the dudu repository:**

   Public clone (when the repo is public):
   ```bash
   git clone https://github.com/Ying-Kai-Liao/dudu.git ~/.codex/dudu
   ```

   The repo is currently private. Clone with `gh` (if you have access) or set up an SSH key:
   ```bash
   gh repo clone Ying-Kai-Liao/dudu ~/.codex/dudu
   # or
   git clone git@github.com:Ying-Kai-Liao/dudu.git ~/.codex/dudu
   ```

2. **Create the skills symlink:**
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/dudu/skills ~/.agents/skills/dudu
   ```

   **Windows (PowerShell):**
   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
   cmd /c mklink /J "$env:USERPROFILE\.agents\skills\dudu" "$env:USERPROFILE\.codex\dudu\skills"
   ```

3. **Restart Codex** (quit and relaunch the CLI) to discover the skills.

## Verify

```bash
ls -la ~/.agents/skills/dudu
```

You should see a symlink (or junction on Windows) pointing to your dudu skills directory.

In a fresh Codex session, asking "what dudu skills are available?" should surface the six skills (`diligence`, `founder-check`, `market-problem`, `customer-discovery`, `competitive-landscape`, `market-sizing`).

## Updating

```bash
cd ~/.codex/dudu && git pull
```

Skills update instantly through the symlink.

## Uninstalling

```bash
rm ~/.agents/skills/dudu
```

Optionally delete the clone: `rm -rf ~/.codex/dudu`.

## Troubleshooting

### Skills not showing up

1. Verify the symlink: `ls -la ~/.agents/skills/dudu`
2. Check skills exist at the target: `ls ~/.codex/dudu/skills`
3. Restart Codex — skills are discovered at startup

### Tool name differences

Skill bodies reference Claude Code conventions for some tool names (`mcp__playwright__browser_*`). On Codex, the equivalent Playwright MCP tools are exposed under your Codex naming convention. Codex agents resolve the prose intent automatically; skills do not need to be edited.
