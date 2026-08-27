"""
Artemis benchmark harness for python-sortedcontainers.

Writes numeric metrics to ./artemis_results.json (repository root)
so that Artemis Discover can score code versions against real measurements.

Design notes:
  - fixed random seed        -> comparable across versions
  - warmup + median of N     -> resistant to noise and outliers
  - tracemalloc peak         -> memory objective
  - no prints required by Artemis, but kept for human debugging
"""

import json
import random
import statistics
import time
import tracemalloc
from pathlib import Path

from sortedcontainers import SortedDict, SortedList

SEED = 1234
N = 100_000          # اندازهٔ داده — اگر اجرا کند بود کمش کن
REPEATS = 5
WARMUP = 1


def make_data(n=N):
    rnd = random.Random(SEED)
    return [rnd.random() for _ in range(n)]


# ---------- workloads: هر کدام مدت اجرا را برمی‌گرداند ----------

def bench_add(data):
    sl = SortedList()
    t0 = time.perf_counter()
    for x in data:
        sl.add(x)
    return time.perf_counter() - t0


def bench_contains(data):
    sl = SortedList(data)
    probes = data[::10]
    t0 = time.perf_counter()
    for x in probes:
        x in sl
    return time.perf_counter() - t0


def bench_index(data):
    sl = SortedList(data)
    probes = data[::10]
    t0 = time.perf_counter()
    for x in probes:
        sl.index(x)
    return time.perf_counter() - t0


def bench_remove(data):
    sl = SortedList(data)
    t0 = time.perf_counter()
    for x in data:
        sl.remove(x)
    return time.perf_counter() - t0


def bench_dict_setitem(data):
    sd = SortedDict()
    t0 = time.perf_counter()
    for i, x in enumerate(data):
        sd[x] = i
    return time.perf_counter() - t0


def median_time(fn, data):
    for _ in range(WARMUP):
        fn(data)
    samples = [fn(data) for _ in range(REPEATS)]
    return statistics.median(samples)


def peak_memory_mb(data):
    tracemalloc.start()
    sl = SortedList(data)
    _peak_holder = len(sl)          # جلوگیری از حذف زودهنگام توسط GC
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / (1024 * 1024)


def main():
    root = Path.cwd()
    for stale in ("artemis_results.json", "artemis_results.csv"):
        (root / stale).unlink(missing_ok=True)

    data = make_data()
    probes = len(data[::10])

    t_add = median_time(bench_add, data)
    t_contains = median_time(bench_contains, data)
    t_index = median_time(bench_index, data)
    t_remove = median_time(bench_remove, data)
    t_dict = median_time(bench_dict_setitem, data)

    results = {
        "sl_add_ops_per_sec": len(data) / t_add,
        "sl_contains_ops_per_sec": probes / t_contains,
        "sl_index_ops_per_sec": probes / t_index,
        "sl_remove_ops_per_sec": len(data) / t_remove,
        "sd_setitem_ops_per_sec": len(data) / t_dict,
        "total_workload_seconds": t_add + t_contains + t_index + t_remove + t_dict,
        "peak_memory_mb": peak_memory_mb(data),
    }

    # همهٔ مقادیر باید عدد متناهی باشند — الزام آرتمیس
    for key, value in results.items():
        assert isinstance(value, (int, float)), f"{key} is not numeric"
        results[key] = round(float(value), 4)

    out = root / "artemis_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
