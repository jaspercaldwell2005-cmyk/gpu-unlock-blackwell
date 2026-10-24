# probe

`mma_rate.py` measures the thing the unlock changes, the issue-rate gap between
FP16 tensor FMA into FP32 and into FP16. Everything in this repository's
feasibility claim rests on this number, so it is a script rather than a
paragraph.

Torch only. Run it before and after any unlock attempt and diff the receipts.

```
python mma_rate.py                    # table and verdict
python mma_rate.py --json mine.json   # also write a receipt to diff
```

`5090-stock.json` is the baseline taken on an RTX 5090, driver 610.88, 575 W,
under WSL2 on 2026-10-24.
