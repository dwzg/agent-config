#!/bin/sh
# Run Claude Code against a local llama-server instead of the Anthropic API, so that the local
# model can use Claude Code's file tools: `claude-local -p "Read src/x.c and ..."`.
# An example to adapt: set MODEL and the context size to what your server runs.
#
# The server here is started as a systemd user service; replace that line with whatever
# starts yours, or drop the block if it is always running.

URL=http://127.0.0.1:8080
MODEL=local

if ! curl -sf -o /dev/null "$URL/health"; then
    echo "claude-local: starting llama-server..." >&2
    systemctl --user start llama-server || exit 1
    until curl -sf -o /dev/null "$URL/health"; do sleep 1; done
fi

export ANTHROPIC_BASE_URL="$URL"
export ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$MODEL"
export CLAUDE_CODE_SUBAGENT_MODEL="$MODEL"
# must not exceed the server's context size (--ctx-size)
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=16000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

# Default permission mode: in headless use (-p) the model can read files and nothing else.
exec claude --permission-mode default "$@"
