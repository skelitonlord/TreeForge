# TreeForge — Pixel Tablet (tangorpro) EUB / Pixel ROM Recovery Recovery Record

**Date:** 2026-09-10  
**Device:** Google Pixel Tablet (`tangorpro`)  
**SoC:** Google Tensor G2 / GS201 / S5P9855  
**Factory build used for native firmware:** `BP1A.250505.005`  
**Native bootloader version after recovery:** `tangorpro-15.2-13237001`  
**Outcome:** **RECOVERED TO NATIVE TANGORPRO BOOTLOADER FASTBOOT**

---

## 1. Incident state

The tablet became stuck in Google Pixel ROM Recovery / EUB after a custom diagnostic-kernel boot-loop incident.

Observed USB state:

```text
18d1:4f00 Google Inc. Pixel ROM Recovery
```

Normal fastboot was unavailable:

```text
fastboot devices
# no device
```

A cable unplug/replug by itself did **not** reliably bring the device back. When the USB device disappeared, a **Power-only reset while the USB cable remained connected** restored:

```text
18d1:4f00 Google Inc. Pixel ROM Recovery
```

This behavior should be treated as specific operational knowledge for tangorpro EUB recovery.

---

## 2. Important signed-image constraint

A broad scan of public tangorpro factory images found that normal factory bootloader stages are Google-signed but are **not USB/EUB boot variants**.

Typical flags:

```text
normal tangorpro factory stage: 0x00000400  -> USB bit NO
tangorpro LDFW:                0x00000402  -> USB bit NO
Tensor-USBDL GS201 recovery:   0x00000401  -> USB bit YES
```

The USB flag is covered by Google's signature. Therefore:

- Do **not** flip the USB bit on a normal tangorpro factory stage.
- Do **not** use Tensor-USBDL `--usb` to mutate the signed tangorpro images.
- Do **not** transplant signed headers between different bodies.
- The working solution must use already signed USB-recovery variants where required.

---

## 3. Host-side Tensor-USBDL preparation

TreeForge used a guarded Tensor-USBDL v0.2.0 build.

Upstream release identification:

```text
tag:    020
commit: aebdc392ef990a6972ac3bfa004dade57f5d1d8c
```

Release ZIP SHA-256:

```text
15dbd6406c1c74c2cd7104388ab745f3605d026ede6fc6c61c754ddb30b194b2
```

TreeForge guarded binary:

```text
/home/skelitonlord/development/treeforge/.smoke/tangorpro-ram-fastboot/tensor-usbdl-treeforge-guarded
```

The guarded build was patched so DNW serial writes/drains retry on `EINTR` instead of aborting the boot-stage transfer.

Patched binary SHA-256:

```text
3390b3716953a28a3638f4391b45f447a2535ccac4e7651e8f28b2ce2e7702e5
```

The patch was required because the first live run failed partway through `ABLB` with:

```text
interrupted system call
```

After the retry patch, the complete USB chain could be transferred reliably.

---

## 4. Known GS201 USB-recovery payload hashes

```text
BL1   375c45717e9a07aaae46648016b8059255185b5f3ac83d205249b3c26f53ebb7
PBL   db418b2cee07201866c80a96ee4886f39610804b6d00b90fe3f19703af65dbf2
BL2   c017c5d33f9aa50e8736fa0da2a3a2369996ea32575714f904c66f6d97929cb2
GSA   f49ba328f389696dbfab8e981c7f1905217bc5743c2c217270712585d7806633
ABL   7a47a5138cf95a35afa558b1a8227edac6f841ed02d3e06391cb4933131b6d53
TZSW  fe53b053b33406b60bae36f0575f28166608fa4454932b7a7ab84d0880f29011
LDFW  302adf409eb0fecf4d9fa9346d2e0423e408639c40aea6d12b8c31c84f06b37e
BL31  c2442fbbef74a46cd1ac7ee12da7954f975c9205d4e110c9ae6505caae51ece8
```

These are signed USB-boot variants for the GS201 family, not tangorpro-native late firmware.

---

## 5. Exact tangorpro factory stage hashes

Factory package:

```text
BP1A.250505.005
bootloader-tangorpro-tangorpro-15.2-13237001.img
```

Extracted stage directory:

```text
/home/skelitonlord/development/treeforge/.smoke/tangorpro-ram-fastboot/tangorpro-bp1a.250505.005
```

Known SHA-256 values:

```text
BL1   59bb4e9009ba7a6d8654ce39737991634cec70d776c1fb1fee757f4911c705c4
PBL   b381e23a3e92b03cc2b438c1716099f558c1261eff061d1b670d1cde1097d02d
BL2   14ba3e781d52a2c8411f75326bb8689e337e46491665f1e6990f7ccba5cd5d18
ABL   d643d0e83005973c600e423389a07813c9d0ea43f70a6de2df98c270fec62705
BL31  f274bcc15581b2c3d92f5c00b82e4898718da42006a5d3a8e365d8c0eb69968f
GSA   d2d2d4dc490201ca379709ae2d8c57ce64cd9722a5b65e8f50674ad33dc84590
TZSW  b1c91ca3b67d412e7627076505089e49463476a4e8bdf164eb9597e2141a5c37
LDFW  d087333903791e9da475dae037dd88fa03eb8804fe474abf3501b3cd254baafd
```

---

## 6. Failed / diagnostic experiments

These experiments were useful and should be preserved so they are not repeated unnecessarily.

### 6.1 Entire GS201 USB chain

A complete public GS201 USB-recovery chain transferred and acknowledged through:

```text
DPM
EPBL
BL2 / BL2B
GSA1
ABL / ABLB
TZSW / TZSB
LDFW / LDFB
BL31 / BL3B
```

Final result:

```text
Acknowledged BL3B
```

However, tangorpro remained:

```text
18d1:4f00 Google Inc. Pixel ROM Recovery
```

No fastboot appeared.

**Conclusion:** a complete Pixel-7-family USB chain alone is insufficient for tangorpro.

### 6.2 Genuine tangorpro ABL substituted directly

Bootstrap:

```text
GS201 USB DPM/PBL/BL2/GSA
        ->
genuine tangorpro ABL
```

Observed:

```text
Requested ABL
Sent ABL
Acknowledged ABL
```

but the device never requested `ABLB` and remained `18d1:4f00`.

**Conclusion:** the normal tangorpro factory ABL header can be transferred at the protocol level but is not accepted as a USB/EUB ABL payload.

### 6.3 GS201 USB ABL + tangorpro TZSW/LDFW/BL31

Observed:

```text
GS201 ABL / ABLB  -> accepted completely
tangorpro TZSW    -> header acknowledged, no TZSB request
tangorpro LDFW    -> header acknowledged, no LDFB request
tangorpro BL31    -> header acknowledged, no BL3B request
```

No fastboot transition occurred.

**Conclusion:** mixing normal tangorpro late-stage headers into the USB upload flow does not by itself complete the recovery.

---

## 7. WORKING RECOVERY CHAIN

The successful configuration used the tangorpro factory directory as the base source and overrode only PBL, BL2, ABL, and BL31 with signed GS201 USB-recovery variants.

Conceptually:

```text
Pixel ROM Recovery / EUB
        |
        v
GS201 USB PBL
        |
        v
GS201 USB BL2
        |
        v
tangorpro GSA
        |
        v
GS201 USB ABL
        |
        v
tangorpro TZSW
        |
        v
tangorpro LDFW
        |
        v
GS201 USB BL31
        |
        v
RAM fastboot
```

### Exact successful command

```bash
GBIN="/home/skelitonlord/development/treeforge/.smoke/tangorpro-ram-fastboot/tensor-usbdl-treeforge-guarded"
GS201="/home/skelitonlord/development/treeforge/.smoke/tangorpro-ram-fastboot/release/sources/gs201"
TANGOR="/home/skelitonlord/development/treeforge/.smoke/tangorpro-ram-fastboot/tangorpro-bp1a.250505.005"
LIVE="/home/skelitonlord/development/treeforge/.smoke/tangorpro_documented_hybrid_live.txt"

sudo "$GBIN" \
  --src "$TANGOR" \
  -p "$GS201/pbl.img" \
  -2 "$GS201/bl2.img" \
  -a "$GS201/abl.img" \
  -3 "$GS201/bl31.img" \
  2>&1 | tee "$LIVE"
```

### Successful transition

USB changed from:

```text
18d1:4f00 Google Inc. Pixel ROM Recovery
```

to:

```text
18d1:4ee0 Google Inc. Nexus/Pixel Device (fastboot)
```

and `fastboot devices` returned the device serial.

This was the first successful escape from EUB.

---

## 8. RAM-fastboot identity and storage visibility

The temporary RAM fastboot environment reported:

```text
enter-reason: usb boot
product: unknown
version-bootloader: cloudripper-1.0-8910487
current-slot: b
unlocked: yes
secure: yes
slot-count: 2
```

It also saw the real device storage:

```text
storage-capacity: 128 GB
storage-vendor: SKhynix
storage-model: HN8T05DEHKX073
storage-protocol: 3.1
```

Important initial slot state:

```text
current-slot: b
slot-retry-count:a: 3
slot-retry-count:b: 0
slot-successful:a: no
slot-successful:b: no
slot-unbootable:a: no
slot-unbootable:b: no
```

This strongly suggested slot B had exhausted its boot attempts while slot A still had three retries available.

---

## 9. Escape from RAM fastboot to native tangorpro bootloader

From RAM fastboot:

```bash
fastboot --set-active=a
```

Observed:

```text
Setting current slot to 'a' OKAY
current-slot: a
slot-retry-count:a: 3
slot-retry-count:b: 0
slot-unbootable:a: no
slot-unbootable:b: no
```

No partitions were flashed.

Then:

```bash
fastboot reboot bootloader
```

successfully left the temporary USB-booted `cloudripper` loader and entered the device's persistent/native bootloader.

Native fastboot identification:

```text
product: tangorpro
current-slot: a
version-bootloader: tangorpro-15.2-13237001
enter-reason: reboot bootloader
unlocked: yes
secure: yes
```

USB remained normal fastboot:

```text
18d1:4ee0 Google Inc. Nexus/Pixel Device (fastboot)
```

Native slot state:

```text
slot-retry-count:a: 3
slot-retry-count:b: 0
slot-successful:a: no
slot-successful:b: no
slot-unbootable:a: no
slot-unbootable:b: no
```

This proved the persistent/native tangorpro bootloader chain was still functional.

---

## 10. Native TreeForge diagnostics

Once native tangorpro fastboot was restored:

```bash
cd /home/skelitonlord/development/kernel/treeforge_kernel
./kernel diagnostics --transport fastboot
```

successfully identified:

```text
Device:     Pixel Tablet (tangorpro)
Profile:    android-15-r36
Transport:  fastboot
```

Diagnostic output:

```text
/home/skelitonlord/development/kernel/treeforge_kernel/out/tangorpro/android-15-r36/diagnostics/20260910-213324-0400
```

The run completed with `Marker hits: 32`.

The same command had failed in RAM fastboot because the USB ABL reported `product:unknown`.

---

## 11. Recovery procedure — concise version

For a tangorpro in confirmed Pixel ROM Recovery / EUB (`18d1:4f00`) with the same conditions:

1. Keep the USB cable connected.
2. If the device disappears, use a **Power-only reset** while still connected until `18d1:4f00` returns.
3. Use the guarded Tensor-USBDL build.
4. Use the genuine tangorpro factory stage directory as `--src`.
5. Override only PBL, BL2, ABL, and BL31 with the known signed GS201 USB-recovery variants.
6. Do **not** use `--usb`.
7. Run the hybrid chain.
8. Confirm transition to `18d1:4ee0` and `fastboot devices`.
9. Before flashing anything, capture `fastboot getvar all`.
10. If the RAM loader reports a viable alternate slot, set that slot active.
11. Run `fastboot reboot bootloader`.
12. Confirm native identity: `product:tangorpro` and `version-bootloader:tangorpro-...`.
13. Only after native fastboot is restored should normal repair/flashing procedures begin.

---

## 12. Safety / lessons learned

- Do **not** assume `Acknowledged <HEADER>` means the boot-stage body was authenticated or accepted.
- A subsequent body request (`ABLB`, `TZSB`, `LDFB`, `BL3B`) is stronger evidence that the USB loader accepted that stage for full transfer.
- `Received duplicate bootloader request` and `Not allowed to upload right now` were normal EUB flow-control messages when followed by `Acknowledged <stage>`.
- Do not manufacture USB variants by changing signed header flags.
- Do not repeatedly flash the bootloader simply because the device is in EUB.
- Obtain RAM fastboot first and inspect real storage/slot state.
- A valid alternate slot may be enough to return to the native bootloader without rewriting persistent bootloader partitions.
- Once native fastboot is restored, stop using the foreign RAM loader for ordinary flashing.
- Preserve the working EUB payload set and its hashes; recovery depends on exact signed binaries.

---

## 13. Files / evidence worth preserving

```text
/home/skelitonlord/development/treeforge/.smoke/tangorpro_mixed_chain_prepare.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_mixed_chain_live.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_mixed_abl_stall_state.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_mixed_usb_abl_prepare.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_mixed_usb_abl_live.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_mixed_usb_abl_post.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_documented_hybrid_live.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_documented_hybrid_post.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_eub_ram_fastboot_state.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_eub_set_active_a.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_native_bootloader_recovered.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_eub_ram_fastboot_diagnostics.txt
/home/skelitonlord/development/treeforge/.smoke/tangorpro_native_recovery_diagnostics.txt
```

Native diagnostic directory:

```text
/home/skelitonlord/development/kernel/treeforge_kernel/out/tangorpro/android-15-r36/diagnostics/20260910-213324-0400
```

---

## 14. Final recovery status

```text
EUB / Pixel ROM Recovery      RECOVERED
RAM fastboot                  ACHIEVED
native tangorpro bootloader   RESTORED
persistent bootloader flash   NOT REQUIRED
active slot                   A
native bootloader             tangorpro-15.2-13237001
```

The Android/AOSP userspace was already known not to be in a trusted bootable state before this incident, so the next operation was intentionally a flash of a previously known-working AOSP build from **native tangorpro fastboot**.

---

## 15. Recommended TreeForge follow-up

This incident should become a dedicated TreeForge recovery feature rather than remain an ad-hoc procedure.

Suggested future command family:

```text
treeforge recovery eub detect
treeforge recovery eub prepare
treeforge recovery eub boot-fastboot
treeforge recovery eub inspect
treeforge recovery eub handoff-native
```

Any implementation should retain the safety model demonstrated here:

- exact device/profile gating
- exact payload hashes
- no automatic signed-header mutation
- RAM-only bootstrap first
- read-only inspection before persistent writes
- explicit confirmation before changing slot metadata
- native-bootloader handoff before ordinary flashing
