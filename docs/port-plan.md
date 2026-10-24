# Port plan

Ordered riskiest-unknown-first. Phases 1 to 3 are the real work; 4 to 6 are a
re-target of code that already exists.

Each phase names its exit check, so a phase is done when the check runs, not
when the code compiles.

## Phase 0: instrument

Done. `probe/mma_rate.py` measures the target ratio, and `probe/5090-stock.json`
is the baseline. Any later claim is measured against this receipt on the same
card.

Exit check: rerunning the harness reproduces the baseline within a few percent.

## Phase 1: get a GB20x booter plaintext

The blocker. Three routes, in preference order.

**1a. Find someone who already extracted it.** Highest value, lowest effort.
TOTORONG published the Ada payload as a Hugging Face repo with analysis
documents. They are the most likely next mover and have not touched Blackwell.
An issue on their repo or on the Ada repository asking specifically for a GB20x
debug booter plaintext or a GB20x `IMAGE_DBG` extraction is the first action.

**1b. Extract it from the installed driver.** `nvlddmkm.sys` 610.88 on this
machine carries `CNvDisplay_Blackwell_GB202`. The booter object is in there. The
work is locating it and, if it is a debug build, decrypting it with the known
test key.

Note the debug/production split. The open module publishes `IMAGE_DBG` next to
`IMAGE_PROD` for Ada, and the key index is known to be 37. Whether the Windows
driver ships a debug booter at all for GB20x is unknown. If it ships only
production, decryption uses a different path.

**1c. Wait for an NVIDIA module release that adds the GB20x booter explicit.**
Cheap, unbounded. They added an explicit AD102 entry once, so they may add
GB20x. Each driver release is a re-check.

Exit check: a plaintext, disassemblable booter image with a verifiable layout,
or a clear statement that none of the three routes yields one yet.

## Phase 2: find the overflow and mine gadgets

With plaintext in hand, disassemble it and reproduce the Ampere analysis:
confirm the signature loader still has the unbounded copy into the stack, and
that the same chain shape applies.

Mine for gadgets. Reuse the Ampere chain structure, then re-target the five
address classes TOTORONG's `docs/ANALYSIS.en.md` enumerates as the ones a chain
depends on, the main entry, the BAR write helper, the argument and return tail,
and the cleanup path.

Exit check: a candidate gadget chain with every address resolved against this
image, disassembly excerpts committed, and the flow argued step by step.

## Phase 3: build the payload and prove the write

Build the 64,000-byte image with the patched dwords. The chain's shape is one
funnel that enables the chain, two operands, three re-invocations of the BAR
write helper with different target and value pairs, and one status word.

Targets are `FEAT_OVR_PLM` at `0x00823804` set to `0xffffffff`, then `SS0` at
`0x0082381c` set to `0x88888888`, then `SS1` at `0x00823820` set to `0x8`.

The one confirmed barrier, **read** from the Ada report: several registers
refuse host writes while the booter still holds the card. The host write is
accepted only after the payload has completed and the booter has exited. So the
ordering is payload, then readback, then host selectors, and the readback is
what gates everything else.

Exit check: on hardware, the FEAT readback shows `0xffffffff` after the payload,
the marker lands, and the host writes to `SS0`/`SS1` stick where they previously
did nothing.

## Phase 4: the kernel module

Add a third arch value and a Blackwell device table to the arch seam. Reuse the
Ada booter state machine and the packaging. Re-target the addresses and sizes.

Exit check: cold boot with the option set, the module runs before the driver,
the driver binds normally afterwards, and readback after driver load still shows
the selectors held.

## Phase 5: measure the win and the cost

Run `probe/mma_rate.py` on an unlocked boot and diff against the baseline
receipt. Then sweep the power cap, because the honest number is the gain held at
a fixed cap, not a gain bought with watts.

Also check the negative side: INT8 and decode should be roughly unchanged, and
numerical output should be identical.

Exit check: a committed before/after pair of receipts and a stated power cap.

## Phase 6: publish and upstream

Package for the three distro families the Ada tree already supports. Decide
whether to carry a fork or send it upstream to `JustAResearcher/gpu-unlock-ada`,
which is the natural home since it already carries two architectures and an
arch seam.

Exit check: installable package, boot-order docs, and a compatibility report
matching the format the other projects use.

## Known prerequisites to gather before Phase 3

- the debug booter test key, index 37, and the AES-zero control value
  `717d1494eaca317ff106195258b38377` used to validate it. **Read** from the Ada
  decoder.
- the AD102 payload manifest with per-dword offsets, as the template. Public.
- BAR0 offsets for the FEAT block to confirm the inference that they did not
  move on GB20x.
