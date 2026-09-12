# TreeForge

**TreeForge** is an open-source Android device bring-up framework for analyzing Android factory images and reconstructing deterministic, reviewable Android device-tree inputs.

TreeForge is designed around immutable models, deterministic output, provenance preservation, and provider-independent Android device evidence.

The current validation target is the **Google Pixel Tablet (`tangorpro`) running Android 15**.

---

## What TreeForge Does

TreeForge turns Android device evidence into structured device-tree and bring-up output.

The primary workflow accepts an Android factory-image ZIP and drives the extraction, discovery, reconstruction, generation, reporting, and export pipeline.

```text
factory-image ZIP
        ↓
factory extraction and image discovery
        ↓
partition discovery
        ↓
filesystem detection and materialization
        ↓
Android model extraction
        ↓
reconstruction and analysis
        ↓
Android build/device-tree generation
        ↓
inventory, summary, manifest, reports, and export
```

TreeForge currently provides:

- Android partition and filesystem discovery;
- standalone partition-image handling;
- Android sparse-image conversion;
- ext4 and EROFS filesystem inspection;
- boot and init_boot metadata parsing;
- Android property extraction;
- `init`, `fstab`, `ueventd`, and VINTF reconstruction;
- service, property, boot, filesystem, and dependency analysis;
- deterministic Android build and device-tree generation;
- inventories, statistics, summaries, manifests, reports, and exports;
- provenance and canonical identity preservation throughout the pipeline.

### Current validation target

| | |
|---|---|
| Device | Google Pixel Tablet |
| Codename | `tangorpro` |
| Android | 15 |
| Platform | `gs201` |
| Primary input | Google factory-image ZIP |

---

## Installation

Download `setup.sh` from the appropriate TreeForge release and run it:

```bash
./setup.sh
```

The setup utility handles TreeForge installation, updates, verification, repair, required dependencies, and environment configuration. It can also configure Android source and host tooling when those features are needed.

After installation, verify the environment with:

```bash
treeforge doctor
```

For available commands:

```bash
treeforge --help
```

---

## Generating a Device Tree

The primary TreeForge command is:

```bash
treeforge generate
```

Use the installed CLI for the authoritative option reference:

```bash
treeforge generate --help
```

### Factory-image workflow

Factory-image generation is the recommended workflow. The factory-image ZIP can be located anywhere accessible on the host filesystem and does not need to be copied into the TreeForge repository.

Example using the current Pixel Tablet validation target:

```bash
treeforge generate \
    --factory-image "/path/to/tangorpro-factory-image.zip" \
    --device-vendor google \
    --device-name tangorpro \
    --product-name aosp_tangorpro \
    --manufacturer Google \
    --architecture arm64 \
    --board-platform gs201 \
    --android-version 15
```

TreeForge automatically performs the downstream factory-image extraction, partition discovery, filesystem processing, model extraction, reconstruction, device-tree generation, reporting, and export operations.

The original factory-image archive is not moved or copied into the TreeForge repository. Input, workspace, and output paths may be located independently, including paths containing spaces.

### Generation options

#### Factory-image input

| Option | Description |
|---|---|
| `--factory-image` | Android factory-image ZIP. TreeForge extracts and processes the archive through its persistent workspace. |

#### Extracted filesystem inputs

These options provide already-extracted Android filesystem roots and are primarily useful for advanced or lower-level workflows.

| Option | Description |
|---|---|
| `--system-root` | Extracted Android `system` filesystem root. |
| `--vendor-root` | Extracted Android `vendor` filesystem root. |
| `--product-root` | Optional extracted Android `product` filesystem root. |
| `--system-ext-root` | Optional extracted Android `system_ext` filesystem root. |
| `--odm-root` | Optional extracted Android `odm` filesystem root. |

#### Partition-image inputs

| Option | Description |
|---|---|
| `--super-image` | Authoritative Android `super.img`. Do not combine with standalone logical partition images. |
| `--system-image` | Standalone Android `system` partition image. |
| `--vendor-image` | Standalone Android `vendor` partition image. |
| `--product-image` | Optional standalone Android `product` partition image. |
| `--system-ext-image` | Optional standalone Android `system_ext` partition image. |
| `--odm-image` | Optional standalone Android `odm` partition image. |
| `--boot-image` | Optional standalone Android `boot` partition image. |
| `--init-boot-image` | Optional standalone Android `init_boot` partition image. |

When `--super-image` is omitted from the manual workflow, `--system-image` and `--vendor-image` are used as the primary standalone partition images.

Factory-image input cannot be combined with manual filesystem or partition-image inputs.

#### Output and workspace

| Option | Description |
|---|---|
| `--workspace-root` | Persistent TreeForge runtime workspace. When omitted, TreeForge uses its configured workspace root, normally `./workspace`. |
| `--output-root` | Destination for the generated Android device tree. |

Workspace and output directories may be located independently from the TreeForge repository.

#### Device identity

| Option | Description |
|---|---|
| `--device-vendor` | Android source-tree vendor namespace, such as `google`. |
| `--device-name` | Android device codename, such as `tangorpro`. |
| `--product-name` | Android product name generated for the device. |
| `--manufacturer` | Human-readable device manufacturer. |
| `--architecture` | Primary Android target architecture, such as `arm64`. |
| `--board-platform` | Target board platform or SoC identifier, such as `gs201`. |
| `--android-version` | Android source version represented by the supplied device evidence. |

#### Host tools

| Option | Description |
|---|---|
| `--lpdump` | Explicit path to an `lpdump` executable. When omitted, TreeForge uses its verified Android host-provider bundle. |

TreeForge also uses Android and filesystem host tools internally where required. Run `treeforge doctor` to inspect the configured environment and host-tool availability.

`lpdump`, `lpunpack`, and `simg2img` are TreeForge-owned Android host providers and are verified by `treeforge doctor`.

### Advanced manual workflow

TreeForge retains the lower-level filesystem and partition-image workflow for advanced use and debugging.

```bash
treeforge generate \
    --system-root "/path/to/system" \
    --vendor-root "/path/to/vendor" \
    --product-root "/path/to/product" \
    --system-ext-root "/path/to/system_ext" \
    --odm-root "/path/to/odm" \
    --system-image "/path/to/system.img" \
    --vendor-image "/path/to/vendor.img" \
    --product-image "/path/to/product.img" \
    --system-ext-image "/path/to/system_ext.img" \
    --boot-image "/path/to/boot.img" \
    --init-boot-image "/path/to/init_boot.img" \
    --device-vendor google \
    --device-name tangorpro \
    --product-name aosp_tangorpro \
    --manufacturer Google \
    --architecture arm64 \
    --board-platform gs201 \
    --android-version 15
```

The factory-image workflow should normally be preferred because TreeForge can perform the extraction and discovery stages automatically.

---

## Other Commands

Check the installed TreeForge version:

```bash
treeforge version
```

Inspect the TreeForge environment:

```bash
treeforge doctor
```

Show all available commands:

```bash
treeforge --help
```

---

## Project Policy

TreeForge source code is open source.

Factory images, extracted proprietary binaries, vendor blobs, firmware, private signing keys, and other copyrighted or device-specific artifacts are **not** part of TreeForge and must not be redistributed through the TreeForge repository unless their licenses explicitly permit it.

TreeForge does not make proprietary Android files open source. It analyzes files supplied by the user and generates TreeForge-authored configuration, metadata, reports, manifests, and other bring-up artifacts.

Do not commit proprietary factory-image or device artifacts to the TreeForge repository. Users are responsible for obtaining required proprietary material from authorized sources and complying with the licenses and terms governing that material.

---

## Credits

TreeForge is built on the work of the Android open-source, Linux, filesystem, and Python communities.

Projects and ecosystems used by or relevant to TreeForge include:

- **Android Open Source Project (AOSP)** — Android platform formats, build conventions, host tools, and source references;
- **Linux kernel and filesystem projects** — underlying Android and filesystem technology;
- **e2fsprogs** — ext filesystem inspection tools;
- **EROFS utilities** — EROFS filesystem tooling;
- **Android libsparse tools** — Android sparse-image handling;
- **Python** — implementation language;
- **Typer** — command-line framework;
- **Rich** — terminal formatting;
- **Pydantic** — validated models;
- **lxml** — XML processing;
- **NetworkX** — graph modeling and analysis;
- **pyelftools** — ELF parsing;
- **LZ4** and **Zstandard** — boot and ramdisk compression support;
- **pytest** — testing framework;
- **Hatchling** — Python build backend.

Android, AOSP, Pixel, Google, and other names may be trademarks of their respective owners.

TreeForge is an independent project and is not affiliated with or endorsed by Google.

---

## License

TreeForge is licensed under the **Apache License, Version 2.0**.

Copyright © 2026 Dan Saporita and TreeForge Contributors.

You may use, modify, distribute, and use TreeForge commercially in accordance with the terms of the Apache License 2.0. The complete license is included in the `LICENSE` file.

The TreeForge license applies to TreeForge-authored source code and documentation. It does not grant rights to redistribute third-party proprietary Android factory images, vendor binaries, firmware, signing keys, or other copyrighted material.

Generated output may incorporate information derived from user-supplied material. Ownership, licensing, and redistribution requirements for that output depend on the underlying content and applicable licenses.
