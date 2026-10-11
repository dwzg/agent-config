# CLAUDE.md

A public Claude Code plugin marketplace: skills, agents, commands and hooks from Dennis Witzig's own projects, shared for anyone to install. Its private counterpart is `dwzg/agent-config-private`, which has the same layout. Moving something from private to public is copying one plugin folder and adding one entry.

## Layout

```
.claude-plugin/marketplace.json   the catalog: one entry per plugin
plugins/<plugin>/
  .claude-plugin/plugin.json      the plugin's manifest
  skills/<skill>/SKILL.md         skills, invoked as /<plugin>:<skill>
  agents/<agent>.md               subagents
  hooks/hooks.json                hooks
```

## Adding something

- **Group by what it is for, not by type.** A plugin is something a person would install as a unit, such as `homelab-deploy`. Don't make plugins called `skills` or `agents`.
- **New plugin:** create the folder and its `plugin.json`, and add an entry to `marketplace.json`. The entry `name` and the manifest `name` must be identical. That name is the install id, and renaming it later breaks installs, unless you add a `renames` entry to `marketplace.json`.
- **Prefer skills over commands.** Commands are the older format.
- **A skill's `description` decides when Claude uses it.** Say what it does and when to use it, including the error messages or situations that should trigger it.
- **Rules must come from something that actually happened.** Say what breaks without each rule. A rule with no reason gets deleted by the next person who doesn't understand it.
- **No `version` field**, in either `plugin.json` or `marketplace.json`. Installs then track commits, so a push is a release. `claude plugin validate` warns about this; the warning is expected.
- Add the plugin to the table in `README.md`.

## Committing

Commit straight to `main` and push. No branch or pull request is needed; CI validates every push to `main`. This holds only for this repository and `dwzg/agent-config-private`. Changes to `dwzg/homepage` always go through a pull request.

## Never commit

This repository is public. Keep out of it: secrets, tokens, webhook URLs, hostnames or IPs from the home network, and anything that locates the weather station. That kind of content belongs in `agent-config-private`, or nowhere.

## Check

```bash
claude plugin validate .
claude plugin validate ./plugins/<plugin>
```

CI (`.github/workflows/validate.yml`) runs both on every pull request. To try a plugin locally without installing it: `claude --plugin-dir ./plugins/<plugin>`.
