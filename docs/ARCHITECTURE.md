# TreeForge Architecture

**Version:** 0.1.0

---

# Vision

TreeForge is a modular framework for Android device bring-up.

Rather than maintaining static device trees, TreeForge reconstructs and migrates device configurations using previous Android releases, factory images, kernels, and vendor artifacts.

The goal is to reduce Android bring-up from a manual reverse-engineering process into a repeatable, automated pipeline.

TreeForge is **not** a ROM.

TreeForge is **not** a build system.

TreeForge is a framework that understands Android devices and produces the information required to build and maintain them.

---

# Design Goals

TreeForge is designed around the following principles.

## Modular

Every subsystem should be independently replaceable.

Examples:

- Image extraction
- Device analysis
- Tree generation
- Validation
- Migration

should all exist as separate modules.

---

## Pipeline Driven

TreeForge executes work as a sequence of pipeline stages.

Each stage declares:

- required inputs
- generated outputs

The framework determines execution order.

No stage should directly invoke another stage.

---

## Data Driven

TreeForge operates on structured models instead of manipulating text files directly.

The central representation is the Device Model.

Everything consumes or produces structured data.

---

## Device Agnostic

TreeForge should never contain device-specific logic.

TangorPro is data.

Shiba is data.

Pixel Tablet is data.

Support for new devices should come from analysis, not hardcoded behavior.

---

## Android Version Agnostic

TreeForge should support multiple Android releases through plugins.

Migration logic belongs in version-specific modules rather than the framework itself.

---

# High-Level Architecture

CLI

↓

Pipeline

↓

Android Modules

↓

Device Model

↓

Generators / Validators / Reports

---

# Repository Layout

TreeForge/

docs/

tests/

scripts/

assets/

treeforge/

cli/

core/

android/

workspace/

---

# Core Layer

The Core layer contains reusable framework components.

Core must never depend on Android-specific code.

Responsibilities include:

- pipeline execution
- configuration
- plugin loading
- logging
- reports
- caching
- exceptions
- shared models

---

# Android Layer

The Android layer understands Android internals.

Examples include:

- boot images
- vendor images
- VINTF
- SELinux
- Android.bp
- init.rc
- fstab
- properties
- HAL discovery

Android modules may depend on Core.

Core may never depend on Android.

---

# Workspace

A Workspace represents a bring-up session.

The repository contains source code.

The workspace contains generated data.

Example:

workspace/

cache/

images/

reports/

generated/

logs/

A workspace can be deleted and recreated without affecting TreeForge itself.

---

# Device Model

The Device Model is the canonical representation of an Android device.

Future components should operate on the Device Model whenever possible.

Example contents:

Hardware

Kernel

Partitions

Properties

HALs

VINTF

SELinux

Overlays

Build Configuration

Dependencies

---

# Pipeline

Pipeline stages perform a single responsibility.

Examples:

ExtractFactoryImage

ExtractPartitions

AnalyzeBoot

AnalyzeVendor

AnalyzeSystem

BuildDeviceModel

GenerateTree

ValidateTree

Each stage declares:

Inputs

Outputs

Dependencies

The pipeline resolves execution automatically.

---

# Plugins

Support for new Android releases should be implemented through plugins.

Examples:

Android 15

Android 16

Android 17

Plugins may provide:

migration rules

validators

generators

parsers

Templates

The framework itself should not require modification for new Android versions.

---

# Philosophy

TreeForge should understand Android.

It should not merely automate shell commands.

The long-term objective is to encode Android bring-up knowledge into software rather than relying on manual engineering effort.

Whenever possible:

Prefer models over text.

Prefer parsers over regex.

Prefer structured data over shell output.

Prefer reusable components over one-off scripts.

If a feature does not fit the architecture, improve the architecture before adding the feature.