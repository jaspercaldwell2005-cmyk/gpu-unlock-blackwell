# Feasibility

What is established, how it was established, and what remains inference.

Evidence labels follow the rule that each claim in this document carries one:
**measured** here, **read** from a source cited in the same sentence, or
**inferred**.

## The question

Does the pre-driver speed-selector unlock, which doubles FP16/BF16
FMA-into-FP32 issue rate on Ampere and Ada Geforce cards, apply to Blackwell,
and can it be ported?

## Answer

The restriction applies. **Measured** on an RTX 5090.

The port is not started and there is no public payload. **Read** from an
exhaustive check of the ecosystem, recorded below.

The port is mechanically well-defined and the reusable surface is large. The
blocker is one missing input: a decrypted GB20x debug booter to mine.

## Evidence

### The restriction is present on GB202

**Measured** with `probe/mma_rate.py` on an RTX 5090, driver 610.88, 575 W
power cap. FP16 accumulate is 334.68 TFLOP/s; FP32 accumulate is 226.14. Ratio
0.676. BF16 accumulate lands within a percent of the same number, 222.29.

Two independent modes agreeing at 0.67 is the expected signature. It is not an
exact 0.5 because the restricted path is partially hidden by overhead at these
shapes. **Inferred**, from the Ampere precedent where the same measurement
direction yields 2.00x after the unlock, that the ceiling here is whatever
removes the difference, not necessarily a clean doubling.

Basis count: one card, one boot, one driver. **Not verified** on a second
Blackwell card, and **not verified** across a driver update.

### No Blackwell payload exists

Checked 2026-10-24 by listing repositories, issue bodies, forks and Hugging
Face, across the whole unlock family.

| Target | Project | Payload |
| --- | --- | --- |
| TU102 | `nlzy/turing-unlock` | yes |
| GA100/102/103/104/106 | `Zagitta/gpu-unlock` | yes |
| AD102/AD103 | `JustAResearcher/gpu-unlock-ada` | yes |
| GB2xx | none | none |

The Ada repository's own fork network, dozens of forks all pushed the day of
this check, contains no Blackwell work.

`bird/vgpu-unlock-blackwell` covers GB202 but is a different mechanism, enabling
vGPU rather than the speed selectors, and is blocked in hardware by fused-off VF
PRIV registers. Its finding that consumer and enterprise firmware are byte
identical is **read** from its README and is relevant context, not a payload.

### No public GB20x debug booter

This is the real blocker. **Read** from
`docs/evidence/nvidia-booter-dispatch.txt`.

The booter dispatch picks an asset by chip. Explicit variants exist for TU102,
TU116, GA100, GA102, AD102 only. Every other chip resolves to a shared fallback
named `_80f438`.

**Read** from the open module's own generated header: in that module `_80f438`
is a stub body that only asserts, because the object is generated separately.
So for GB20x the booter image is only inside NVIDIA's closed `nv-kernel.o`.

Contrast Ada. `docs/evidence/nvidia-bindata-inventory.txt` lists GB20x assets
that do exist, the FMC, GSP-RM and debug signature blobs, but the booter is
absent from that list.

`nvlddmkm.sys` for 610.88, 120 MB, taken from this machine's driver store, has
`CNvDisplay_Blackwell_GB202` and only one `GB202` string, with no readable
booter symbol table. Extracting the booter from it is possible and is Phase 2
of the plan; it is not a solved extraction.

### The mechanism is understood

**Read** from the Ampere repository's `docs/How Ampere was unlocked.md`, which
is unusually candid and matches the Ada and CMP work.

The signed SEC2 booter has a stack overflow in its signature loader. The signed
debug build is encrypted with a known public test key, so it can be decrypted
and disassembled. A ROP chain of gadgets mined from it becomes a single
arbitrary write. That write sets `FEAT_OVR_PLM` at BAR0 `0x00823804` from
`0xffffff8f` to `0xffffffff`, which unlocks host writes to `SS0` `0x0082381c`
and `SS1` `0x00823820`. The host then writes `0x88888888` and `0x8`, which set
every class-zero speed field to full rate.

Each selector field is four bits, bit 3 an enable, bits 2:0 the divider, where
`0` is full rate. So `0x88888888` is eight fields all enabled at full rate.

None of this is Blackwell-specific. The Ada port reused all of it.

### The runtime side is written and portable

**Read** from the Ada repository layout. Its `unlock_610.c` is 64 KB of booter
state machine, with separate `prep`, `layout`, `vbios` and `aperture` modules,
an arch seam that is currently a two-value enum, and a full packaging story for
Arch, Debian and RPM with initramfs integration and suspend resume.

A Blackwell port is a third enum value, a third device table, and a third
payload. The rest is a re-target.

## What is reusable, concretely

The payload is a container, not code. **Read** from `firmware/generate_v67.py`.
It is 64,000 bytes of one repeated fill dword plus about 20 patched dwords.
Most of those 20 are fixed gadget addresses. Two are the write's operands, and
the chain picks up the address operand from a fixed offset, on Ada `0xf9cc`,
holding `FEAT_OVR_PLM`.

So the payload shell, its checksum pinning, the extraction of firmware and
license from a pinned driver package, and the packaging are all reusable
unchanged. The 20 dwords are not.

## The five prerequisites, and which exist

| Prerequisite | For Blackwell |
| --- | --- |
| Debug booter to mine | **missing** |
| Gadget chain | missing, derives from the above |
| MMIO target (`FEAT_OVR_PLM`) | **inferred** to be the same offset; Ada and Ampere share it and Blackwell did not move the FEAT block that we know of. Verify by readback. |
| Instruction addresses | missing, per-image |
| Pre-driver kmod | reusable |

## Confidence

High confidence, **measured** or **read**: the restriction exists, no public
payload exists, the mechanism, the missing booter, the size of the reusable
surface.

Medium confidence, **inferred**: that the MMIO offset is unchanged on GB20x,
that the booter retains the same overflow and a similarly deep clean-path
region, and that a port is roughly Ada-shaped in effort.

Low confidence, **guess**: the effort. Ada took one person one evening after the
payload existed. Everything before the payload is the long part.

## Risks

**Bricking.** Low. The unlock runs before the driver and does not modify
firmware on the card. Removing the kernel command-line option restores stock
behaviour on the next boot. The card's VBIOS is untouched.

**Power and heat.** Real, and understated by the projects. Tensor cores at full
issue draw more. Existing reports hold the power cap and measure the gain at that
cap, which is the honest protocol.

**Data integrity.** Reports in the Ampere tracker found bit-identical outputs
before and after. **Read**, not verified on Blackwell.
