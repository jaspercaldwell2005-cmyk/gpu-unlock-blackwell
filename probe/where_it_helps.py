#!/usr/bin/env python3
"""Where the unlock would actually pay: sweep the compute-bound / bandwidth-bound
axis and show which regimes carry the fuse.

The unlock doubles the FP16/BF16 tensor FMA-into-FP32 issue rate. That only
matters where the tensor cores are the bottleneck. Where the workload is waiting
on memory, doubling issue rate changes nothing.

Batch size M on a fixed K=N GEMM is exactly that axis. Small M is a decode-like
GEMV (weights streamed from VRAM, one token at a time). Large M is a prefill or
training-like GEMM (compute saturated).

For each M this reports the fp16->fp32-accumulate rate against the
fp16->fp16-accumulate rate, plus how close the lower one sits to peak. A ratio
near the fuse together with high utilisation means the unlock helps there. A
ratio near 1.0 together with utilisation far below peak means it does not.
"""

from __future__ import annotations

import time

import torch

K = N = 8192
BATCHES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
TARGET_FLOPS = 3e10


def bench(dtype, m, fp16acc, target_flops=TARGET_FLOPS, reps=3):
    a = torch.randn(m, K, device="cuda", dtype=dtype)
    b = torch.randn(K, N, device="cuda", dtype=dtype)
    prev = torch.backends.cuda.matmul.allow_fp16_accumulation
    torch.backends.cuda.matmul.allow_fp16_accumulation = fp16acc
    for _ in range(5):
        a @ b
    torch.cuda.synchronize()
    iters = max(20, int(target_flops / (2 * m * N * K)))
    best = 0.0
    for _ in range(reps):
        t = time.perf_counter()
        for _ in range(iters):
            a @ b
        torch.cuda.synchronize()
        best = max(best, 2 * m * N * K / ((time.perf_counter() - t) / iters) / 1e12)
    torch.backends.cuda.matmul.allow_fp16_accumulation = prev
    del a, b
    torch.cuda.empty_cache()
    return best


def memory_bandwidth_gbs():
    n = 256 * 1024 * 1024
    a = torch.empty(n, device="cuda", dtype=torch.uint8)
    b = torch.empty(n, device="cuda", dtype=torch.uint8)
    for _ in range(3):
        b.copy_(a)
    torch.cuda.synchronize()
    best = 0.0
    for _ in range(5):
        t = time.perf_counter()
        b.copy_(a)
        torch.cuda.synchronize()
        best = max(best, 2 * n / (time.perf_counter() - t) / 1e9)
    del a, b
    return best


p = torch.cuda.get_device_properties(0)
print(f"gpu {torch.cuda.get_device_name(0)} | SMs {p.multi_processor_count}")
print(f"GEMM K=N={K}, fp16 inputs, best-of-3\n")

bw = memory_bandwidth_gbs()
print(f"measured copy bandwidth {bw:,.0f} GB/s\n")

print(f"{'M':>6s} {'fp16acc':>9s} {'fp32acc':>9s} {'ratio':>7s}  {'verdict'}")
print("-" * 62)

rows = []
ref = max(bench(torch.float16, m, True) for m in (2048, 4096))

for m in BATCHES:
    hi = bench(torch.float16, m, True)
    lo = bench(torch.float16, m, False)
    ratio = lo / hi if hi else 0.0
    row = {"m": m, "fp16acc": hi, "fp32acc": lo, "ratio": ratio}
    rows.append(row)

    if ratio < 0.85 and lo > 0.4 * ref:
        verdict = "compute-bound, fuse bites -> unlock helps"
    elif ratio > 0.9:
        verdict = "bandwidth-bound, fuse absorbed -> unlock does nothing"
    else:
        verdict = "partial"

    print(f"{m:6d} {hi:8.1f}T {lo:8.1f}T {ratio:7.3f}  {verdict}")

print()
print(f"reference fp16->fp16 at large M: {ref:.1f} TFLOP/s")
print()
print("decode-like (M small): absolute TFLOP/s is far under peak and the")
print("fp32-accumulate penalty vanishes, so the unlock buys ~nothing.")
print("prefill/train-like (M large): the penalty is the full fuse and the")
print("kernel is near peak, so the unlock buys that fuse back.")
