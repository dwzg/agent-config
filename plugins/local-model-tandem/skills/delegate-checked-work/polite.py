#!/usr/bin/env python3
"""Run a CPU-heavy command so that it does not slow a local model on the same machine.

    polite.py [--free-cores N] COMMAND [ARGUMENT...]

The command (and everything it starts) gets the lowest scheduling priority and is kept off N
physical cores (default 2). Linux only; elsewhere the priority is lowered and the cores are
left alone.

Why both: a model that computes on the GPU is still driven by a CPU thread or two. With every
hardware thread busy, that thread shares its core with a busy sibling and the whole processor
runs at its all-core clock, whatever the priorities say. Measured on a 16-core machine with a
27B model on the GPU and a test run using all 32 threads: 82 tokens a second with the test run
paused, 55 with it at the lowest priority on all cores, 76 with two cores left free.

Importable too: `from polite import polite; polite()` at the start of a worker pool's parent.
"""
import os
import sys


def polite(free_cores=2):
    """Lowest priority, and off `free_cores` physical cores (the highest-numbered ones)."""
    try:
        os.nice(19)
    except OSError:
        pass
    try:
        cores = {}
        for cpu in sorted(os.sched_getaffinity(0)):
            path = "/sys/devices/system/cpu/cpu%d/topology/core_id" % cpu
            cores.setdefault(open(path).read().strip() if os.path.exists(path) else str(cpu), []).append(cpu)
        ids = sorted(cores, key=lambda c: min(cores[c]))
        free = max(0, min(free_cores, len(ids) // 2))
        if free:
            os.sched_setaffinity(0, {cpu for c in ids[:len(ids) - free] for cpu in cores[c]})
    except (OSError, ValueError, AttributeError):
        pass


def main():
    argv = sys.argv[1:]
    free = 2
    if argv[:1] == ["--free-cores"]:
        free = int(argv[1])
        argv = argv[2:]
    if not argv:
        sys.exit(__doc__)
    polite(free)
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
