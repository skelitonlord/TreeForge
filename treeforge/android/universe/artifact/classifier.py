from __future__ import annotations

import posixpath
import re

from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactKind,
)


class AndroidUniverseArtifactClassifier:
    """
    Classify canonical Android filesystem artifacts inside Universe.

    Classification is deterministic and based only on canonical filesystem
    identity already supplied by Filesystem Metadata.

    Parsing evidence has higher authority in the requirement builder.
    This classifier is therefore fallback semantic evidence for artifacts
    that Parsing does not intrinsically decode.

    Rules deliberately classify known semantic families rather than using
    generic /etc placement or generic extension catch-alls.
    """

    _SELINUX_CONTEXT_FILENAMES = (
        "file_contexts",
        "property_contexts",
        "service_contexts",
        "hwservice_contexts",
        "vndservice_contexts",
        "seapp_contexts",
        "keystore2_key_contexts",
    )

    _MEDIA_FILENAME_PREFIXES = (
        "media_",
        "media.",
        "audio_",
        "audio.",
    )

    _MEDIA_FILENAME_MARKERS = (
        "media_codecs",
        "media_profiles",
        "media_performance",
        "codec",
        "codecs",
        "audio_policy",
        "audio_effects",
    )

    _ART_RUNTIME_SUFFIXES = (
        ".odex",
        ".vdex",
        ".oat",
        ".art",
        ".prof",
        ".bprof",
    )

    _FONT_SUFFIXES = (
        ".ttf",
        ".otf",
        ".ttc",
    )

    _MEDIA_ASSET_SUFFIXES = (
        ".ogg",
        ".wav",
        ".mp3",
        ".flac",
        ".aac",
        ".m4a",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    )

    _MACHINE_LEARNING_SUFFIXES = (
        ".tflite",
        ".mfar",
        ".fst",
        ".syms",
        ".zvoice",
        ".pb",
        ".pbtxt",
        ".leveldb",
    )

    _KERNEL_MODULE_METADATA_FILENAMES = (
        "modules.dep",
        "modules.dep.bin",
        "modules.alias",
        "modules.alias.bin",
        "modules.softdep",
        "modules.blocklist",
        "modules.load",
        "modules.order",
        "modules.builtin",
        "modules.builtin.bin",
        "modules.builtin.modinfo",
        "modules.devname",
        "modules.symbols",
        "modules.symbols.bin",
    )

    _ACCOUNT_DATABASE_FILENAMES = (
        "passwd",
        "group",
    )

    _FILESYSTEM_CONFIGURATION_FILENAMES = (
        "fs_config_dirs",
        "fs_config_files",
    )

    _NATIVE_LIBRARY_FILENAMES = (
        "llndk.libraries.txt",
        "public.libraries.txt",
        "public.libraries-google.txt",
        "sanitizer.libraries.txt",
    )

    _POWER_FILENAMES = (
        "cgroups.json",
        "task_profiles.json",
        "powerhint.json",
    )

    _THERMAL_FILENAME_PREFIXES = (
        "thermal_info_config",
    )

    _SYSTEM_RUNTIME_METADATA_FILENAMES = (
        "dirty-image-objects",
        "preloaded-classes",
        "system-other-odex-marker",
        "xtables.lock",
    )

    def classify(
        self,
        android_path: str,
    ) -> tuple[
        AndroidUniverseArtifactKind,
        AndroidUniverseArtifactDisposition,
    ]:
        if not isinstance(
            android_path,
            str,
        ):
            raise TypeError(
                "android_path must be a string"
            )

        if not android_path:
            raise ValueError(
                "android_path cannot be empty"
            )

        path = android_path.lower()
        filename = posixpath.basename(path)

        parts = tuple(
            part
            for part in path.split("/")
            if part
        )

        kind = self._classify_kind(
            path=path,
            filename=filename,
            parts=parts,
        )

        return (
            kind,
            self._disposition_for(
                kind
            ),
        )

    def _classify_kind(
        self,
        *,
        path: str,
        filename: str,
        parts: tuple[str, ...],
    ) -> AndroidUniverseArtifactKind:
        # ----------------------------------------------------
        # Intrinsic Android semantic configuration sources.
        # ----------------------------------------------------

        if (
            filename.startswith("ueventd")
            and filename.endswith(".rc")
        ):
            return AndroidUniverseArtifactKind.UEVENTD_RC

        if (
            "etc" in parts
            and re.fullmatch(
                r".+\.[0-9]+rc",
                filename,
            )
        ):
            return AndroidUniverseArtifactKind.INIT_RC

        if (
            path.endswith(".rc")
            and (
                (
                    "etc" in parts
                    and "init" in parts
                )
                or filename.startswith("init.")
                or filename == "init.rc"
            )
        ):
            return AndroidUniverseArtifactKind.INIT_RC

        if (
            filename.startswith("fstab")
            or "/fstab." in path
            or filename == "recovery.fstab"
        ):
            return AndroidUniverseArtifactKind.FSTAB

        if (
            filename in (
                "build.prop",
                "default.prop",
            )
            or filename.endswith(".prop")
        ):
            return AndroidUniverseArtifactKind.PROPERTY_FILE

        if (
            "vintf" in parts
            and filename.endswith(".xml")
        ):
            if (
                filename == "compatibility_matrix.xml"
                or filename.startswith(
                    "compatibility_matrix."
                )
                or filename.startswith(
                    "compatibility_matrix_"
                )
            ):
                return AndroidUniverseArtifactKind.VINTF_MATRIX

            if (
                filename == "manifest.xml"
                or filename.startswith(
                    "manifest."
                )
                or filename.startswith(
                    "manifest_"
                )
            ):
                return AndroidUniverseArtifactKind.VINTF_MANIFEST

            return AndroidUniverseArtifactKind.VINTF_XML

        if (
            filename.endswith(".cil")
            or "sepolicy" in filename
        ):
            return AndroidUniverseArtifactKind.SELINUX_POLICY

        if (
            filename in self._SELINUX_CONTEXT_FILENAMES
            or any(
                filename.endswith(
                    "_" + context_name
                )
                for context_name
                in self._SELINUX_CONTEXT_FILENAMES
            )
        ):
            return AndroidUniverseArtifactKind.SELINUX_CONTEXTS

        if (
            filename.endswith("_mac_permissions.xml")
            or filename == "mac_permissions.xml"
        ):
            return AndroidUniverseArtifactKind.SELINUX_POLICY

        if (
            path.endswith(".xml")
            and "etc" in parts
            and (
                "permissions" in parts
                or "sysconfig" in parts
            )
        ):
            return AndroidUniverseArtifactKind.PERMISSION_XML

        if "/etc/default-permissions/" in path:
            return (
                AndroidUniverseArtifactKind
                .DEFAULT_PERMISSION_CONFIGURATION
            )

        if (
            "/etc/compatconfig/" in path
            or "/etc/appcompat/" in path
        ):
            return (
                AndroidUniverseArtifactKind
                .COMPATIBILITY_CONFIGURATION
            )

        # ----------------------------------------------------
        # Platform/runtime metadata and configuration.
        # ----------------------------------------------------

        if "/etc/classpaths/" in path:
            return (
                AndroidUniverseArtifactKind
                .RUNTIME_CLASSPATH_CONFIGURATION
            )

        if filename in {
            "linker.config.pb",
            "ld.config.txt",
        }:
            return (
                AndroidUniverseArtifactKind
                .LINKER_CONFIGURATION
            )

        if filename in self._NATIVE_LIBRARY_FILENAMES:
            return (
                AndroidUniverseArtifactKind
                .NATIVE_LIBRARY_CONFIGURATION
            )

        if filename in self._FILESYSTEM_CONFIGURATION_FILENAMES:
            return (
                AndroidUniverseArtifactKind
                .FILESYSTEM_CONFIGURATION
            )

        if filename in self._ACCOUNT_DATABASE_FILENAMES:
            return AndroidUniverseArtifactKind.ACCOUNT_DATABASE

        if (
            filename == "aconfig_flags.pb"
            or filename == "build_flags.json"
        ):
            return (
                AndroidUniverseArtifactKind
                .BUILD_FEATURE_METADATA
            )

        if filename == "notice.xml.gz":
            return AndroidUniverseArtifactKind.NOTICE_METADATA

        if (
            (
                "/usr/share/zoneinfo/" in path
                and filename in {
                    "tzdata",
                    "tz_version",
                }
            )
            or path.startswith("/etc/tz/")
        ):
            return AndroidUniverseArtifactKind.TIMEZONE_DATA

        if (
            path.startswith("/etc/icu/")
            and filename.startswith("icudt")
            and filename.endswith(".dat")
        ):
            return AndroidUniverseArtifactKind.ICU_RUNTIME_DATA

        if filename == "android.bp":
            return (
                AndroidUniverseArtifactKind
                .ANDROID_BUILD_DEFINITION
            )

        if "/etc/preferred-apps/" in path:
            return (
                AndroidUniverseArtifactKind
                .PREFERRED_APP_CONFIGURATION
            )

        if filename in self._SYSTEM_RUNTIME_METADATA_FILENAMES:
            return (
                AndroidUniverseArtifactKind
                .SYSTEM_RUNTIME_METADATA
            )

        if filename == "hosts":
            return (
                AndroidUniverseArtifactKind
                .SYSTEM_RUNTIME_METADATA
            )

        # ----------------------------------------------------
        # Security / integrity.
        # ----------------------------------------------------

        if "/etc/security/cacerts/" in path:
            return AndroidUniverseArtifactKind.TRUST_CERTIFICATE

        if (
            path == "/etc/security/otacerts.zip"
            or path.endswith(
                "/etc/security/otacerts.zip"
            )
        ):
            return (
                AndroidUniverseArtifactKind
                .OTA_CERTIFICATE_ARCHIVE
            )

        if (
            (
                "cacerts" in parts
                or "cacerts_wfa" in parts
            )
            and re.fullmatch(
                r"[0-9a-f]{8}\.[0-9]+",
                filename,
            )
        ):
            return AndroidUniverseArtifactKind.TRUST_CERTIFICATE

        if (
            "/etc/security/fsverity/" in path
            and filename.endswith(".idsig")
        ):
            return AndroidUniverseArtifactKind.FSVERITY_SIGNATURE

        if (
            "/etc/security/fsverity/" in path
            and filename.endswith(".der")
        ):
            return AndroidUniverseArtifactKind.FSVERITY_METADATA

        if (
            path.endswith(".fsv_meta")
        ):
            return AndroidUniverseArtifactKind.FSVERITY_METADATA

        if "/etc/seccomp_policy/" in path:
            return AndroidUniverseArtifactKind.SECCOMP_POLICY

        # ----------------------------------------------------
        # Kernel artifacts.
        # ----------------------------------------------------

        if (
            path.endswith(".ko")
            and "lib" in parts
            and "modules" in parts
        ):
            return AndroidUniverseArtifactKind.KERNEL_MODULE

        if (
            "modules" in parts
            and (
                filename in self._KERNEL_MODULE_METADATA_FILENAMES
                or filename.startswith("modules.")
            )
        ):
            return AndroidUniverseArtifactKind.KERNEL_MODULE_METADATA

        if "/etc/kernel/" in path:
            return AndroidUniverseArtifactKind.KERNEL_CONFIGURATION

        # ----------------------------------------------------
        # Native/runtime binary artifacts.
        # ----------------------------------------------------

        if (
            path.endswith(".so")
            and (
                self._contains_pair(
                    parts,
                    "lib",
                    "hw",
                )
                or self._contains_pair(
                    parts,
                    "lib64",
                    "hw",
                )
            )
        ):
            return AndroidUniverseArtifactKind.HAL_SHARED_LIBRARY

        if path.endswith(".so"):
            return AndroidUniverseArtifactKind.SHARED_LIBRARY

        if (
            "firmware" in parts
            or "firmware_mnt" in parts
        ):
            return AndroidUniverseArtifactKind.FIRMWARE

        if path == "/init":
            return AndroidUniverseArtifactKind.EXECUTABLE

        if filename == "microdroid.json":
            return (
                AndroidUniverseArtifactKind
                .VIRTUALIZATION_CONFIGURATION
            )

        if (
            filename.startswith("microdroid_")
            or filename == "rialto.bin"
        ):
            return (
                AndroidUniverseArtifactKind
                .VIRTUALIZATION_RUNTIME_ARTIFACT
            )

        if filename == "u-boot.bin":
            return (
                AndroidUniverseArtifactKind
                .BOOTLOADER_PAYLOAD
            )

        if filename == "apex_manifest.pb":
            return (
                AndroidUniverseArtifactKind
                .APEX_MANIFEST_METADATA
            )

        if filename in {
            "extensions_db.pb",
            "sdkinfo.pb",
            "flag.info",
            "flag.map",
            "flag.val",
            "package.map",
        }:
            return (
                AndroidUniverseArtifactKind
                .APEX_SUPPORT_METADATA
            )

        if (
            path.endswith(".apex")
            or path.endswith(".capex")
        ):
            return AndroidUniverseArtifactKind.APEX

        if (
            (
                path.endswith(".apk")
                or path.endswith(".apk.gz")
            )
            and "overlay" in parts
        ):
            return (
                AndroidUniverseArtifactKind
                .RUNTIME_RESOURCE_OVERLAY
            )

        if (
            path.endswith(".apk")
            or path.endswith(".apk.gz")
        ):
            return AndroidUniverseArtifactKind.APK

        if (
            path.endswith(".jar")
            and "framework" in parts
        ):
            return AndroidUniverseArtifactKind.FRAMEWORK_JAR

        if (
            path.endswith(".jar")
            and "javalib" in parts
        ):
            return AndroidUniverseArtifactKind.JAVA_LIBRARY

        if path.endswith(
            self._ART_RUNTIME_SUFFIXES
        ):
            return (
                AndroidUniverseArtifactKind
                .ART_RUNTIME_ARTIFACT
            )

        # ----------------------------------------------------
        # Android input / specialized runtime artifacts.
        # ----------------------------------------------------

        if (
            path.endswith(".kl")
            and "usr" in parts
            and "keylayout" in parts
        ):
            return AndroidUniverseArtifactKind.ANDROID_KEY_LAYOUT

        if (
            path.endswith(".kcm")
            and "usr" in parts
            and "keychars" in parts
        ):
            return (
                AndroidUniverseArtifactKind
                .ANDROID_KEY_CHARACTER_MAP
            )

        if (
            path.endswith(".idc")
            and "usr" in parts
            and "idc" in parts
        ):
            return (
                AndroidUniverseArtifactKind
                .ANDROID_INPUT_DEVICE_CONFIGURATION
            )

        if (
            path.endswith(".napp_header")
            and "etc" in parts
            and "chre" in parts
        ):
            return (
                AndroidUniverseArtifactKind
                .CHRE_NANOAPP_METADATA
            )

        if "/etc/chre/" in path:
            return AndroidUniverseArtifactKind.CHRE_RUNTIME_DATA

        if (
            path.endswith(".o")
            and "etc" in parts
            and "bpf" in parts
        ):
            return AndroidUniverseArtifactKind.EBPF_OBJECT

        if (
            path.endswith(".nprf")
            and "etc" in parts
            and "modem" in parts
        ):
            return AndroidUniverseArtifactKind.MODEM_PROFILE

        if (
            path.endswith(".icd")
            and "etc" in parts
            and "khronos" in parts
            and "opencl" in parts
            and "vendors" in parts
        ):
            return (
                AndroidUniverseArtifactKind
                .OPENCL_ICD_CONFIGURATION
            )

        # A shell source under bin/hw remains an executable utility.
        # Path placement alone is not sufficient evidence that a script is
        # a hardware-service process.
        if (
            path.endswith(".sh")
            and (
                "bin" in parts
                or "xbin" in parts
            )
        ):
            return AndroidUniverseArtifactKind.EXECUTABLE

        if (
            "bin" in parts
            and "hw" in parts
            and self._contains_pair(
                parts,
                "bin",
                "hw",
            )
        ):
            return AndroidUniverseArtifactKind.HARDWARE_SERVICE

        if (
            "bin" in parts
            or "xbin" in parts
        ):
            return AndroidUniverseArtifactKind.EXECUTABLE

        # ----------------------------------------------------
        # Final audited platform/runtime families.
        # ----------------------------------------------------

        if filename == "gps_debug.conf":
            return (
                AndroidUniverseArtifactKind
                .GNSS_CONFIGURATION
            )

        if filename == "libnfc-nci.conf":
            return (
                AndroidUniverseArtifactKind
                .NFC_CONFIGURATION
            )

        if filename.startswith("mke2fs.conf"):
            return (
                AndroidUniverseArtifactKind
                .FILESYSTEM_TOOL_CONFIGURATION
            )

        if (
            filename.endswith(".avbpubkey")
            and "avb" in parts
        ):
            return (
                AndroidUniverseArtifactKind
                .AVB_PUBLIC_KEY
            )

        if filename == "recovery.wipe":
            return (
                AndroidUniverseArtifactKind
                .RECOVERY_CONFIGURATION
            )

        if filename == "mkshrc":
            return (
                AndroidUniverseArtifactKind
                .SHELL_CONFIGURATION
            )

        if filename == "media_profiles_v1_0.dtd":
            return (
                AndroidUniverseArtifactKind
                .MEDIA_CONFIGURATION
            )

        if (
            "/usr/share/bmd/" in path
            and filename in {
                "rffspeed_501.bmd",
                "rffstd_501.bmd",
            }
        ):
            return (
                AndroidUniverseArtifactKind
                .FACE_DETECTION_MODEL_DATA
            )

        if (
            "/usr/share/ime/" in path
            and (
                filename == "mozc.data"
                or filename.endswith(".zip")
            )
        ):
            return (
                AndroidUniverseArtifactKind
                .INPUT_METHOD_DATA
            )

        if filename == "cert-chain.crt":
            return (
                AndroidUniverseArtifactKind
                .CERTIFICATE_CHAIN
            )

        if (
            filename == "init.common.cfg"
            or filename.startswith(
                "init.insmod."
            )
            and filename.endswith(".cfg")
        ):
            return (
                AndroidUniverseArtifactKind
                .KERNEL_MODULE_CONFIGURATION
            )

        if (
            "/etc/res/values/charger/" in path
            and filename == "animation.txt"
        ):
            return (
                AndroidUniverseArtifactKind
                .CHARGER_CONFIGURATION
            )

        if filename in {
            "touchflow.pb",
            "twoshay_config.json",
        }:
            return (
                AndroidUniverseArtifactKind
                .TOUCH_CONFIGURATION
            )

        if filename == "atc_profile.json":
            return (
                AndroidUniverseArtifactKind
                .DISPLAY_CONFIGURATION
            )

        # ----------------------------------------------------
        # Device/platform subsystem configuration.
        # ----------------------------------------------------

        if path.endswith(".tflite"):
            return (
                AndroidUniverseArtifactKind
                .MACHINE_LEARNING_MODEL
            )

        if (
            (
                path.endswith(".binarypb")
                or filename == "tuning_ocl.txt"
            )
            and "camera" in parts
        ):
            return (
                AndroidUniverseArtifactKind
                .CAMERA_CONFIGURATION
            )

        if (
            path.endswith(".binarypb")
            and filename.startswith(
                "autocal_"
            )
        ):
            return (
                AndroidUniverseArtifactKind
                .CAMERA_CONFIGURATION
            )

        if (
            "/etc/bluetooth/le_audio/" in path
            and filename.endswith(".bfbs")
        ):
            return (
                AndroidUniverseArtifactKind
                .AUDIO_CONFIGURATION
            )

        if (
            path.startswith("/etc/bluetooth/")
            and filename.endswith(".conf")
        ):
            return (
                AndroidUniverseArtifactKind
                .BLUETOOTH_CONFIGURATION
            )

        if "/etc/uwb/" in path:
            if (
                filename.startswith("uwb-calibration")
                or filename == "calib_paths"
            ):
                return (
                    AndroidUniverseArtifactKind
                    .UWB_CALIBRATION
                )

            return AndroidUniverseArtifactKind.UWB_CONFIGURATION

        if "/etc/aoc/" in path:
            return AndroidUniverseArtifactKind.AUDIO_DSP_DATA

        if (
            "/etc/aidl/le_audio/" in path
            or filename in {
                "default_volume_tables.xml",
                "mixer_paths.xml",
                "sound_trigger_configuration.xml",
                "waves_config.ini",
                "waves_preset.mps",
            }
        ):
            return AndroidUniverseArtifactKind.AUDIO_CONFIGURATION

        if "/etc/modem/" in path or filename == "modem_stat.conf":
            return AndroidUniverseArtifactKind.MODEM_CONFIGURATION

        if "/etc/wifi/" in path:
            return AndroidUniverseArtifactKind.WIFI_CONFIGURATION

        if "/etc/sensors/" in path:
            if (
                "/registry/" in path
                or "cal" in filename
            ):
                return (
                    AndroidUniverseArtifactKind
                    .SENSOR_CALIBRATION
                )

            return AndroidUniverseArtifactKind.SENSOR_CONFIGURATION

        if (
            "/etc/displayconfig/" in path
            or filename == "display_settings.xml"
        ):
            return AndroidUniverseArtifactKind.DISPLAY_CONFIGURATION

        if (
            filename.startswith("display_colordata_")
            or filename.startswith("display_golden_")
        ):
            return AndroidUniverseArtifactKind.DISPLAY_CALIBRATION

        if filename in self._POWER_FILENAMES:
            return AndroidUniverseArtifactKind.POWER_CONFIGURATION

        if filename.startswith(
            self._THERMAL_FILENAME_PREFIXES
        ):
            return AndroidUniverseArtifactKind.THERMAL_CONFIGURATION

        if "/etc/parameter-framework/" in path:
            return (
                AndroidUniverseArtifactKind
                .PARAMETER_FRAMEWORK_CONFIGURATION
            )

        if (
            filename.startswith("bluetooth_power_limits")
            and filename.endswith(".csv")
        ):
            return (
                AndroidUniverseArtifactKind
                .DEVICE_CALIBRATION_DATA
            )

        if (
            filename.startswith("led_golden_calibration_")
        ):
            return (
                AndroidUniverseArtifactKind
                .DEVICE_CALIBRATION_DATA
            )

        # ----------------------------------------------------
        # Diagnostic/tracing metadata.
        # ----------------------------------------------------

        if (
            "/etc/perfetto/" in path
            or "/etc/atrace/" in path
            or filename == "event-log-tags"
            or filename.startswith("ftrace_")
        ):
            return (
                AndroidUniverseArtifactKind
                .TRACING_CONFIGURATION
            )

        if (
            "protolog" in filename
        ):
            return (
                AndroidUniverseArtifactKind
                .PROTOLOG_CONFIGURATION
            )

        # ----------------------------------------------------
        # Fonts, language resources, model data, media.
        # ----------------------------------------------------

        if path.endswith(
            self._FONT_SUFFIXES
        ):
            return AndroidUniverseArtifactKind.FONT

        if filename in {
            "fonts.xml",
            "font_fallback.xml",
            "fonts_customization.xml",
        }:
            return AndroidUniverseArtifactKind.FONT_CONFIGURATION

        if path.endswith(".hyb"):
            return (
                AndroidUniverseArtifactKind
                .HYPHENATION_DICTIONARY
            )

        if (
            "/usr/hyphen-data/" in path
            and filename.endswith(".lic.txt")
        ):
            return (
                AndroidUniverseArtifactKind
                .HYPHENATION_LICENSE
            )

        if (
            "/usr/srec/" in path
        ):
            return (
                AndroidUniverseArtifactKind
                .SPEECH_MODEL_DATA
            )

        if (
            filename in {
                "motion_predictor_model.tflite",
                "input_classifier_model.pb",
            }
            or (
                "/etc/ambient/" in path
                and filename.endswith(".leveldb")
            )
        ):
            return (
                AndroidUniverseArtifactKind
                .MACHINE_LEARNING_MODEL
            )

        if filename == "motion_predictor_config.xml":
            return (
                AndroidUniverseArtifactKind
                .MACHINE_LEARNING_MODEL
            )

        if (
            (
                "usr" in parts
                and "srec" in parts
            )
            or "tts" in parts
        ) and path.endswith(
            self._MACHINE_LEARNING_SUFFIXES
        ):
            return (
                AndroidUniverseArtifactKind
                .MACHINE_LEARNING_MODEL
            )

        if (
            "/priv-app/euiccsupportpixel/" in path
        ):
            return AndroidUniverseArtifactKind.ESIM_SUPPORT_DATA

        if (
            "/wallpaper/image/" in path
            or "wallpaper" in filename
        ):
            return AndroidUniverseArtifactKind.WALLPAPER_ASSET

        if path.endswith(".bc"):
            return AndroidUniverseArtifactKind.RUNTIME_BITCODE

        if (
            "media" in parts
            and filename.startswith("bootanimation")
            and filename.endswith(".zip")
        ):
            return AndroidUniverseArtifactKind.MEDIA_ASSET

        if path.endswith(
            self._MEDIA_ASSET_SUFFIXES
        ):
            return AndroidUniverseArtifactKind.MEDIA_ASSET

        if path.endswith(".zip"):
            return AndroidUniverseArtifactKind.ARCHIVE

        # ----------------------------------------------------
        # Existing media configuration behavior.
        # ----------------------------------------------------

        if (
            "etc" in parts
            and filename.endswith(
                (
                    ".xml",
                    ".conf",
                    ".json",
                )
            )
            and (
                filename.startswith(
                    self._MEDIA_FILENAME_PREFIXES
                )
                or any(
                    marker in filename
                    for marker
                    in self._MEDIA_FILENAME_MARKERS
                )
            )
        ):
            return AndroidUniverseArtifactKind.MEDIA_CONFIGURATION

        # ----------------------------------------------------
        # Deliberately unresolved.
        # ----------------------------------------------------

        return AndroidUniverseArtifactKind.UNKNOWN

    @staticmethod
    def _contains_pair(
        parts: tuple[str, ...],
        first: str,
        second: str,
    ) -> bool:
        return any(
            parts[index] == first
            and parts[index + 1] == second
            for index in range(
                max(
                    0,
                    len(parts) - 1,
                )
            )
        )

    @staticmethod
    def _disposition_for(
        kind: AndroidUniverseArtifactKind,
    ) -> AndroidUniverseArtifactDisposition:
        if kind is AndroidUniverseArtifactKind.UNKNOWN:
            return (
                AndroidUniverseArtifactDisposition
                .UNCLASSIFIED
            )

        if kind in {
            AndroidUniverseArtifactKind.APEX_MANIFEST_METADATA,
            AndroidUniverseArtifactKind.APEX_SUPPORT_METADATA,
            AndroidUniverseArtifactKind.CTS_SHIM_ALLOWED_HASHES,
        }:
            return (
                AndroidUniverseArtifactDisposition
                .INVENTORY_ONLY
            )

        if kind in {
            AndroidUniverseArtifactKind.JAVA_LIBRARY,
            AndroidUniverseArtifactKind.KERNEL_MODULE,
            AndroidUniverseArtifactKind.AVB_PUBLIC_KEY,
            AndroidUniverseArtifactKind.CAMERA_CONFIGURATION,
            AndroidUniverseArtifactKind.RECOVERY_CONFIGURATION,
            AndroidUniverseArtifactKind.VIRTUALIZATION_RUNTIME_ARTIFACT,
            AndroidUniverseArtifactKind.BOOTLOADER_PAYLOAD,
        }:
            return (
                AndroidUniverseArtifactDisposition
                .PRESERVE
            )

        if kind in {
            AndroidUniverseArtifactKind.INIT_RC,
            AndroidUniverseArtifactKind.FSTAB,
            AndroidUniverseArtifactKind.UEVENTD_RC,
            AndroidUniverseArtifactKind.PROPERTY_FILE,
            AndroidUniverseArtifactKind.VINTF_MANIFEST,
            AndroidUniverseArtifactKind.VINTF_MATRIX,
            AndroidUniverseArtifactKind.VINTF_XML,
            AndroidUniverseArtifactKind.SELINUX_POLICY,
            AndroidUniverseArtifactKind.SELINUX_CONTEXTS,
            AndroidUniverseArtifactKind.PERMISSION_XML,
            AndroidUniverseArtifactKind.MEDIA_CONFIGURATION,
            AndroidUniverseArtifactKind.COMPATIBILITY_CONFIGURATION,
            AndroidUniverseArtifactKind.DEFAULT_PERMISSION_CONFIGURATION,
            AndroidUniverseArtifactKind.RUNTIME_CLASSPATH_CONFIGURATION,
            AndroidUniverseArtifactKind.LINKER_CONFIGURATION,
            AndroidUniverseArtifactKind.NATIVE_LIBRARY_CONFIGURATION,
            AndroidUniverseArtifactKind.FILESYSTEM_CONFIGURATION,
            AndroidUniverseArtifactKind.ACCOUNT_DATABASE,
            AndroidUniverseArtifactKind.FONT_CONFIGURATION,
            AndroidUniverseArtifactKind.PREFERRED_APP_CONFIGURATION,
            AndroidUniverseArtifactKind.UWB_CONFIGURATION,
            AndroidUniverseArtifactKind.UWB_CALIBRATION,
            AndroidUniverseArtifactKind.AUDIO_CONFIGURATION,
            AndroidUniverseArtifactKind.MODEM_CONFIGURATION,
            AndroidUniverseArtifactKind.WIFI_CONFIGURATION,
            AndroidUniverseArtifactKind.SENSOR_CONFIGURATION,
            AndroidUniverseArtifactKind.SENSOR_CALIBRATION,
            AndroidUniverseArtifactKind.DISPLAY_CONFIGURATION,
            AndroidUniverseArtifactKind.DISPLAY_CALIBRATION,
            AndroidUniverseArtifactKind.POWER_CONFIGURATION,
            AndroidUniverseArtifactKind.THERMAL_CONFIGURATION,
            AndroidUniverseArtifactKind.PARAMETER_FRAMEWORK_CONFIGURATION,
            AndroidUniverseArtifactKind.KERNEL_CONFIGURATION,
            AndroidUniverseArtifactKind.TRACING_CONFIGURATION,
            AndroidUniverseArtifactKind.GNSS_CONFIGURATION,
            AndroidUniverseArtifactKind.NFC_CONFIGURATION,
            AndroidUniverseArtifactKind.FILESYSTEM_TOOL_CONFIGURATION,
            AndroidUniverseArtifactKind.SHELL_CONFIGURATION,
            AndroidUniverseArtifactKind.KERNEL_MODULE_CONFIGURATION,
            AndroidUniverseArtifactKind.CHARGER_CONFIGURATION,
            AndroidUniverseArtifactKind.TOUCH_CONFIGURATION,
            AndroidUniverseArtifactKind.BLUETOOTH_CONFIGURATION,
            AndroidUniverseArtifactKind.VIRTUALIZATION_CONFIGURATION,
        }:
            return (
                AndroidUniverseArtifactDisposition
                .SEMANTIC_SOURCE
            )

        if kind in {
            AndroidUniverseArtifactKind.ART_RUNTIME_ARTIFACT,
            AndroidUniverseArtifactKind.FSVERITY_METADATA,
            AndroidUniverseArtifactKind.FSVERITY_SIGNATURE,
            AndroidUniverseArtifactKind.BUILD_FEATURE_METADATA,
            AndroidUniverseArtifactKind.NOTICE_METADATA,
            AndroidUniverseArtifactKind.TIMEZONE_DATA,
            AndroidUniverseArtifactKind.ICU_RUNTIME_DATA,
            AndroidUniverseArtifactKind.ANDROID_BUILD_DEFINITION,
            AndroidUniverseArtifactKind.PROTOLOG_CONFIGURATION,
            AndroidUniverseArtifactKind.SYSTEM_RUNTIME_METADATA,
        }:
            return (
                AndroidUniverseArtifactDisposition
                .INVENTORY_ONLY
            )

        #
        # A known semantic kind does not by itself prove that the exact
        # installed artifact must be preserved.
        #
        # Binary/runtime/resource families may be source-reconstructible,
        # exact-preservation payloads, or otherwise require additional
        # canonical context.  Until such evidence exists, keep the
        # reconstruction disposition explicitly unresolved rather than
        # silently treating recognition as proof of preservation.
        #
        return (
            AndroidUniverseArtifactDisposition
            .UNCLASSIFIED
        )
