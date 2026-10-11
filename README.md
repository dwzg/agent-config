# agent-config

Skills, agents and other things for AI coding by Dennis Witzig, taken from my own projects. Each one exists because something went wrong without it.

The repository is a [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces): every folder under `plugins/` is a plugin you can install on its own.

## Install

In Claude Code:

```
/plugin marketplace add dwzg/agent-config
/plugin install homelab-deploy@agent-config
```

Or from your shell:

```bash
claude plugin marketplace add dwzg/agent-config
claude plugin install homelab-deploy@agent-config
```

To receive updates automatically, open `/plugin`, go to **Marketplaces**, select `agent-config` and choose **Enable auto-update**. Otherwise run `/plugin marketplace update agent-config` now and then.

## Plugins

| Plugin | What it does |
| --- | --- |
| [`homelab-deploy`](plugins/homelab-deploy) | Builds a Docker image in GitHub Actions, pushes it to GHCR and redeploys it through a Portainer webhook. The skill `/homelab-deploy:ghcr-portainer` carries a ready workflow and the eight rules that keep it from breaking. |
| [`local-model-tandem`](plugins/local-model-tandem) | Runs a queue of checkable tasks through a local model (llama-server, Ollama, LM Studio) while the session does other work. The skill `/local-model-tandem:delegate-checked-work` carries the loop, a wrapper that keeps CPU jobs from slowing the model, and the thirteen rules that came out of one long run. |

## Not using Claude Code?

A skill is a folder with a `SKILL.md` in it, and the format is shared by other agents. Copy the folder from `plugins/<plugin>/skills/` into wherever your tool reads skills from.

## License

MIT
