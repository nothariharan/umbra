"""Concurrent request helpers (spec: up to 50 in flight)."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

T = TypeVar("T")


def burst(fn: Callable[[int], T], n: int, *, timeout: float = 60.0) -> list[T]:
    if n < 1:
        raise ValueError("burst size must be positive")
    if n > 50:
        results: list[T] = []
        for start in range(0, n, 50):
            chunk = min(50, n - start)
            results.extend(burst(lambda i, offset=start: fn(offset + i), chunk, timeout=timeout))
        return results
    barrier = threading.Barrier(n)

    def worker(index: int):
        try:
            barrier.wait(timeout=timeout)
        except threading.BrokenBarrierError:
            pass
        try:
            return fn(index)
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(worker, range(n)))


def statuses(responses) -> list[int]:
    return [getattr(r, "status_code", 0) for r in responses]


def tally(responses) -> dict[int, int]:
    counts: dict[int, int] = {}
    for status in statuses(responses):
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def no_5xx(responses) -> None:
    bad = [r for r in responses if getattr(r, "status_code", 0) >= 500]
    errors = [r for r in responses if isinstance(r, Exception)]
    assert not bad and not errors, (
        f"5xx or transport errors under load: {tally(responses)}; "
        f"first error: {errors[0] if errors else bad[0].text[:200]}"
    )
