---
name: delegate-checked-work
description: Hand bulk work to a local model (llama-server, Ollama, LM Studio) running beside the session, and keep only the answers a program accepts. Use when the user has a local model and there is a queue of similar tasks whose result can be tested, such as rewriting functions against existing tests, finding an input that reaches some code, or converting records against a schema. Also use when a local model's answers come back empty, when a bulk CPU job slows the model down, or when deciding what a weaker model can be trusted with.
---

# Work in tandem with a local model

A local model is slow and makes mistakes, and it costs nothing per call. That makes it useful for exactly one kind of work: **work whose answers a program can check**. Then nobody has to believe the model. It works through a queue in the background while the session does something else, and a checker decides which answers are kept.

Everything below comes from one long run: a 27B model on a 24 GB GPU, used beside a session that was rewriting machine code as C and comparing every rewrite with the original in an emulator.

## 1. Sort the work by who can check it

| The model's answer is | Who decides | Use it for |
| --- | --- | --- |
| an artifact a program can test (code against existing tests, an input that must reach a line, data against a schema) | the program's exit status | bulk queues, unattended |
| a claim ("this branch can never run", "this function sets the clock") | a reader, afterwards | leads worth reading, never facts |
| a description | nobody | a first look, to be compared with the source |

Only the first row runs unattended. In the run this comes from, the model wrote 37 functions that passed their tests, and two of two "this can never execute" claims were right when read. A description of ten functions, the same day, called a signed comparison unsigned in two of them. Nothing but reading would have caught that.

If there is no checker yet, build the checker first. The model's work is worth what the checker is worth.

## 2. Run the queue

[ask_and_check.py](ask_and_check.py) is the loop: one request per item, the answer to a file, the checker's verdict, and on a failure the checker's output back to the model for another try.

```bash
python3 ask_and_check.py --prompt question.txt --ext c \
    --check './build_and_test.sh {answer} {name}' items/*.txt
```

- Start it in the background and **do other work meanwhile**. Waiting for a model that takes a minute per item wastes the session.
- One queue at a time. A local server with one slot only queues the second request, and both get slower.
- Results are in `delegated/accepted/`, `delegated/rejected/` (with the checker's last output) and `results.tsv`. Read `rejected/` before blaming the model: in the first queue asked this way, the five rejections I looked at were all the tool's fault (rule 4).

The other way to ask is through Claude Code wrapped around the server, as in [claude-local.example.sh](claude-local.example.sh): `claude-local -p "Read item.txt and ..."`. The model can then read files itself, and in the run this comes from it also reasoned far less per answer (rule 4). `ask_and_check.py` asks the server directly, which works with any server and gives a speed figure per answer.

## 3. Rules, and what went wrong without each

1. **Give the model facts instead of letting it infer them.** Put what a tool already knows into the input. Told only to "read the listing", the model called two signed comparisons unsigned. With `; signed >` written after each branch by the listing tool, the same functions came back right. The annotation also protects the human reader, who makes the same mistake.

2. **Say what is normal.** Asked for "anything odd", the model listed the compiler's standard prologue and unused arguments for every function. A paragraph on what is ordinary here left the section empty except for real findings.

3. **Keep the question in a file of its own**, one item per request. Prompts get tuned many times; a prompt inside a script gets tuned by editing the script while a queue is running it.

4. **Give a reasoning model room, and treat an empty answer as no answer.** With a limit of 12,000 tokens, five of ten requests came back with no text at all: the model had spent the limit thinking. The tool then handed the placeholder to the compiler and fed the compiler's complaint back, which helped nobody. `ask_and_check.py` asks for 32,000 and retries an empty answer without showing it to the model. That cures the empty answers and not the cost: asked directly, the model reasoned for 14,000 to 32,000 tokens per function, up to seven minutes each. Through the Claude Code wrapper the same kind of function took half a minute to three minutes, and 29 of 32 passed their tests. How to cap the reasoning of a direct request on this server is not something I found out; if your queue is slow, try the wrapper before a bigger limit.

5. **For open-ended reasoning, ask for a short written analysis before the answer.** Asked for an input that reaches a given instruction, the model with free reasoning ran into the limit and answered nothing; with reasoning switched off (`--no-think`) it answered in 13 seconds and wrongly. "First write your analysis in numbered steps, at most 400 words, then the answer" got an answer for four of eight items, and three of those held up: one input that reached its target and two correct claims that the target cannot be reached.

6. **Check the checker with a right, a wrong and a malformed answer by hand** before the queue starts. A checker that accepts everything, or crashes on an address the model invented, costs an afternoon of the model's work.

7. **Passing the checker is its own category.** Model-written code that passes its tests has been read by nobody. Keep it apart from reviewed work in every count and report, and decide in advance what it needs before it replaces anything: in that run, no surviving mutation, which 11 of the 37 met.

8. **Have a reader go over a sample of what the checker accepted, and turn each finding into a check.** A review agent read 32 accepted functions against the original. 26 were the same. Four loaded or stored a memory location a different number of times, which the tests did not compare; they do now. One could not reproduce a fault of the original that nobody had noticed, a copy one byte past a buffer, and a scan for that shape found three more functions with it. The checker defines what "right" means, and a reader is how you find out what it left out.

9. **Keep what was accepted but not used.** Accepted answers that failed the stricter bar were hours of GPU time and good reading material. They lived in an untracked build directory until someone noticed.

10. **Never let a model's unchecked claim into a record.** Print it, read the evidence it names, and write the conclusion down as your own.

11. **Bulk CPU work has to leave the model room.** A test run on all hardware threads cut the model from 82 to 55 tokens a second, although the model computes on the GPU and the run had the lowest priority. Keeping the run off two physical cores brought it back to 76. [polite.py](polite.py) does both: `python3 polite.py make test`.

12. **Measure speed over whole answers.** Samples of a token counter every few seconds fell between requests and showed anything from 35 to 74. `ask_and_check.py` writes the server's own figure for each answer to `rate.tsv`; tune the sharing from that.

13. **Stop a queue in a command of its own.** `pkill -f pattern` also matches the shell that runs it when the pattern appears anywhere in that command line. Three times it killed the edits that followed it.

## 4. What to tell the user

Say what the checker checks and what it does not. Say how many answers were accepted, how many rejected, and how many of the accepted ones are in use. Do not report accepted work as understood.
