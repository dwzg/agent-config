#!/usr/bin/env python3
"""Ask a local model for an answer and let a program decide whether it is right.

For each ITEM (a file: a function's listing, a failing test, a record to convert) the model
gets the question from --prompt with the item's content behind it. Its answer is written to a
file and handed to the --check command. Exit status 0 accepts it. Anything else is fed back to
the model together with what the checker printed, and the model tries again, up to --tries
times. The model is never believed: what counts is the checker's exit status.

    ask_and_check.py --prompt question.txt --check './judge.sh {answer} {item}' items/*.txt

Results go to --out (default ./delegated):
    accepted/NAME.EXT     answers the checker accepted
    rejected/NAME.EXT     the last answer of an item that was never accepted, and why
    results.tsv           item, accepted or rejected, tries, seconds
    rate.tsv              time, tokens written, tokens per second, load average: one line per
                          answer, for tuning how the machine is shared with other work

The server is any OpenAI-compatible one (llama-server, Ollama, LM Studio, vLLM) at --url.
Requests go one at a time: a local server with one slot only queues a second request anyway.

Options:
    --prompt FILE      the question; the item's content is appended
    --check CMD        shell command; {answer} is the answer's file, {item} the item's file,
                       {name} the item's name without extension
    --extract KIND     code (default: the last fenced code block), json (the last fenced
                       block or the whole answer, must parse) or text (the whole answer)
    --ext EXT          extension of the answer files (default: txt)
    --tries N          answers per item (default 3)
    --temp T           sampling temperature (default: the server's)
    --max-tokens N     per answer, reasoning included (default 32000; see the skill for why)
    --no-think         ask the server's chat template to switch reasoning off
    --url URL          default http://127.0.0.1:8080
    --model NAME       default "local"; most local servers ignore it
    --out DIR          default ./delegated
    --timeout SECONDS  per request (default 900)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request


def ask(args, prompt):
    """(text, why there is none). The text is None when the server gave no usable answer."""
    body = {"model": args.model, "max_tokens": args.max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if args.temp is not None:
        body["temperature"] = args.temp
    if args.no_think:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    request = urllib.request.Request(args.url.rstrip("/") + "/v1/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as r:
            reply = json.load(r)
    except OSError as e:
        return None, "no answer from the server: %s" % e
    choice = reply["choices"][0]
    log_rate(args, reply, time.time() - started)
    text = choice["message"].get("content")
    if not text:
        # A reasoning model can spend the whole limit thinking and write nothing.
        return None, "no text; the answer ended with '%s'" % choice.get("finish_reason")
    return text, ""


def log_rate(args, reply, seconds):
    timings, usage = reply.get("timings") or {}, reply.get("usage") or {}
    tokens = timings.get("predicted_n") or usage.get("completion_tokens") or 0
    if not tokens:
        return
    rate = timings.get("predicted_per_second") or tokens / max(seconds, 0.001)
    try:
        load = open("/proc/loadavg").read().split()[0]
    except OSError:
        load = "?"
    with open(os.path.join(args.out, "rate.tsv"), "a") as f:
        f.write("%s\t%d\t%.1f\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), tokens, rate, load))


def extract(kind, text):
    """The part of the model's text that is the answer, or None."""
    blocks = re.findall(r"```[A-Za-z0-9_+-]*\n(.*?)```", text, re.S)
    if kind == "text":
        return text
    if kind == "json":
        candidate = blocks[-1] if blocks else text
        try:
            json.loads(candidate)
        except ValueError:
            return None
        return candidate
    return blocks[-1] if blocks else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], usage=__doc__)
    ap.add_argument("items", nargs="+")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--check", required=True)
    ap.add_argument("--extract", choices=("code", "json", "text"), default="code")
    ap.add_argument("--ext", default="txt")
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--temp", type=float)
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--model", default="local")
    ap.add_argument("--out", default="delegated")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    question = open(args.prompt).read()
    for d in ("accepted", "rejected", "work"):
        os.makedirs(os.path.join(args.out, d), exist_ok=True)
    accepted = 0
    for item in args.items:
        name = os.path.splitext(os.path.basename(item))[0]
        first = question + "\n\n" + open(item).read()
        prompt, problem, answer, started, used = first, "no answer", "", time.time(), 0
        for used in range(1, args.tries + 1):
            text, why = ask(args, prompt)
            if text is None:
                problem = why           # nothing to check, and nothing to show the model either
                prompt = first
                continue
            answer = extract(args.extract, text)
            if answer is None:
                problem = "the answer has no %s" % ("fenced code block" if args.extract == "code" else "valid JSON")
                prompt = first + "\n\nYour previous answer could not be used: " + problem + ". Answer again in the form asked for."
                continue
            path = os.path.join(args.out, "work", "%s.%s" % (name, args.ext))
            open(path, "w").write(answer)
            command = args.check.replace("{answer}", path).replace("{item}", item).replace("{name}", name)
            check = subprocess.run(command, shell=True, capture_output=True, text=True)
            if check.returncode == 0:
                problem = ""
                break
            problem = (check.stdout + check.stderr).strip()[-3000:] or "the checker failed without output"
            prompt = first + "\n\nYour previous answer was:\n```\n" + answer + "\n```\nIt was checked by a program, which reported:\n" \
                + problem + "\nFind the cause and answer again in the same form."
        target = os.path.join(args.out, "rejected" if problem else "accepted", "%s.%s" % (name, args.ext))
        open(target, "w").write(answer + ("\n\n--- not accepted ---\n" + problem + "\n" if problem else ""))
        accepted += not problem
        line = "%s\t%s\t%d\t%d" % (name, "rejected" if problem else "accepted", used, time.time() - started)
        open(os.path.join(args.out, "results.tsv"), "a").write(line + "\n")
        print(line, flush=True)
    print("%d of %d accepted" % (accepted, len(args.items)))
    return 0 if accepted == len(args.items) else 1


if __name__ == "__main__":
    sys.exit(main())
