from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import struct
import subprocess

from treeforge.android.bootstrap.recovery_manifest import (
    AndroidBootstrapRecoveryPartitionManifest,
    render_recovery_partition_manifest_c,
)
from treeforge.android.bootstrap.recovery_usb import (
    AndroidBootstrapRecoveryUsbIdentity,
    render_recovery_usb_identity_c,
)


class AndroidBootstrapRecoveryRuntimeError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapRecoveryRuntimeBuild:
    source_path: Path
    executable_path: Path
    compiler_path: Path
    elf_machine: int
    target_triple: str


class AndroidBootstrapRecoveryRuntimeBuilder:
    '''
    Build TreeForge's standalone recovery/install runtime.

    The initial runtime is intentionally read-only. It derives the
    active Android slot from kernel boot evidence and inventories
    physical block partitions through generic Linux sysfs surfaces.

    It does not open block devices for writing and does not perform
    flashing.
    '''

    ELF_MACHINE_AARCH64 = 183

    _SOURCE = r'''
typedef unsigned long usize;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;


/* TREEFORGE_RECOVERY_CANONICAL_MANIFEST */


/* TREEFORGE_RECOVERY_CANONICAL_USB_IDENTITY */


void *memcpy(
    void *destination,
    const void *source,
    usize count
) {
    volatile unsigned char *output = (
        (volatile unsigned char *) destination
    );

    const volatile unsigned char *input = (
        (const volatile unsigned char *) source
    );

    for (
        usize index = 0;
        index < count;
        index++
    ) {
        output[index] = input[index];
    }

    return destination;
}


void *memmove(
    void *destination,
    const void *source,
    usize count
) {
    volatile unsigned char *output = (
        (volatile unsigned char *) destination
    );

    const volatile unsigned char *input = (
        (const volatile unsigned char *) source
    );

    if (
        (usize) output
        <= (usize) input
    ) {
        for (
            usize index = 0;
            index < count;
            index++
        ) {
            output[index] = input[index];
        }
    } else {
        while (count > 0) {
            count--;

            output[count] = input[count];
        }
    }

    return destination;
}


void *memset(
    void *destination,
    int value,
    usize count
) {
    volatile unsigned char *output = (
        (volatile unsigned char *) destination
    );

    unsigned char byte = (
        (unsigned char) value
    );

    for (
        usize index = 0;
        index < count;
        index++
    ) {
        output[index] = byte;
    }

    return destination;
}


int memcmp(
    const void *left,
    const void *right,
    usize count
) {
    const volatile unsigned char *left_bytes = (
        (const volatile unsigned char *) left
    );

    const volatile unsigned char *right_bytes = (
        (const volatile unsigned char *) right
    );

    for (
        usize index = 0;
        index < count;
        index++
    ) {
        if (
            left_bytes[index]
            < right_bytes[index]
        ) {
            return -1;
        }

        if (
            left_bytes[index]
            > right_bytes[index]
        ) {
            return 1;
        }
    }

    return 0;
}


#define SYS_DUP3 24
#define SYS_MKNODAT 33
#define SYS_MKDIRAT 34
#define SYS_UNLINKAT 35
#define SYS_SYMLINKAT 36
#define SYS_MOUNT 40
#define SYS_OPENAT 56
#define SYS_CLOSE 57
#define SYS_GETDENTS64 61
#define SYS_LSEEK 62
#define SYS_READ 63
#define SYS_WRITE 64
#define SYS_SYNC 81
#define SYS_FSYNC 82
#define SYS_EXIT 93
#define SYS_KILL 129
#define SYS_REBOOT 142
#define SYS_CLONE 220
#define SYS_EXECVE 221
#define SYS_WAIT4 260

#define AT_FDCWD (-100)

#define TREEFORGE_SIGKILL 9
#define TREEFORGE_SIGCHLD 17
#define TREEFORGE_WAIT_WNOHANG 1

#define O_RDONLY 0
#define O_WRONLY 1
#define O_CREAT 0100
#define O_TRUNC 01000
#define O_NONBLOCK 04000
#define O_DIRECTORY 040000

#define SEEK_SET 0

#define S_IFIFO 0010000
#define S_IFBLK 0060000

#define TREEFORGE_RECOVERY_FLASH_PLAN_REQUEST_PATH \
    "/metadata/treeforge/recovery-flash-plan"

/*
 * Hardware-accepted regular-file staging fallback.
 *
 * This remains available for small images while the streaming path
 * becomes the preferred generic transport.
 */
#define TREEFORGE_RECOVERY_FLASH_SOURCE_PATH \
    "/metadata/treeforge/recovery-source.img"

#define TREEFORGE_RECOVERY_UNIFIED_IMAGE_PLAN_REQUEST_PATH \
    "/metadata/treeforge/recovery-image-plan"

#define TREEFORGE_RECOVERY_IMAGE_DESCRIPTOR_PATH \
    "/metadata/treeforge/recovery-image.descriptor"

#define TREEFORGE_RECOVERY_INSTALL_SET_RECEIVE_READY_PATH \
    "/dev/treeforge-recovery-install-set-receive"

#define TREEFORGE_RECOVERY_INSTALL_SET_MANIFEST_PATH \
    "/metadata/treeforge/recovery-install-set.manifest"

#define TREEFORGE_RECOVERY_INSTALL_SET_TRANSFER_STATE_PATH \
    "/dev/treeforge-recovery-install-set-transfer"

#define TREEFORGE_RECOVERY_MAX_INSTALL_SET_IMAGES 64

#define TREEFORGE_RECOVERY_INSTALL_ACTION_FITS 1
#define TREEFORGE_RECOVERY_INSTALL_ACTION_ALLOCATE 2
#define TREEFORGE_RECOVERY_INSTALL_ACTION_RESIZE 3
#define TREEFORGE_RECOVERY_INSTALL_ACTION_SNAPSHOT 4

/*
 * Streaming staging contract.
 *
 * Only the tiny identity manifest persists on metadata. Image bytes
 * themselves flow through the boot-local FIFO and are never stored on
 * the metadata filesystem.
 */
#define TREEFORGE_RECOVERY_STREAM_MANIFEST_PATH \
    "/metadata/treeforge/recovery-source.manifest"

#define TREEFORGE_RECOVERY_STREAM_FIFO_PATH \
    "/dev/treeforge-recovery-source"

#define TREEFORGE_RECOVERY_READ_PROBE_REQUEST_PATH \
    "/metadata/treeforge/recovery-read-probe"

#define TREEFORGE_RECOVERY_LP_READ_PROBE_REQUEST_PATH \
    "/metadata/treeforge/recovery-lp-read-probe"

#define TREEFORGE_RECOVERY_LP_READ_PROBE_REPORT_PATH \
    "/metadata/treeforge/recovery-lp-read-probe-report"

#define TREEFORGE_RECOVERY_PROBE_NODE_PATH \
    "/dev/treeforge-recovery-probe"

#define TREEFORGE_RECOVERY_FLASH_NODE_PATH \
    "/dev/treeforge-recovery-flash"

#define TREEFORGE_RECOVERY_MAX_PARTITIONS 128
#define TREEFORGE_RECOVERY_KERNEL_NAME_CAPACITY 64
#define TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY 96
#define TREEFORGE_RECOVERY_DEVICE_NAME_CAPACITY 64

/*
 * Android logical-partition metadata.
 *
 * These values mirror AOSP liblp's serialized format. Logical discovery is
 * read-only in this milestone; no logical target becomes writable here.
 */
#define TREEFORGE_RECOVERY_LP_GEOMETRY_MAGIC 0x616c4467U
#define TREEFORGE_RECOVERY_LP_HEADER_MAGIC 0x414c5030U

#define TREEFORGE_RECOVERY_LP_RESERVED_BYTES 4096ULL
#define TREEFORGE_RECOVERY_LP_GEOMETRY_SIZE 4096ULL
#define TREEFORGE_RECOVERY_LP_GEOMETRY_STRUCT_SIZE 52U
#define TREEFORGE_RECOVERY_LP_SECTOR_SIZE 512ULL

#define TREEFORGE_RECOVERY_LP_MAJOR_VERSION 10U
#define TREEFORGE_RECOVERY_LP_MINOR_VERSION_MAX 2U

#define TREEFORGE_RECOVERY_LP_HEADER_V1_0_SIZE 128U
#define TREEFORGE_RECOVERY_LP_HEADER_V1_2_SIZE 256U

#define TREEFORGE_RECOVERY_LP_PARTITION_ENTRY_SIZE 52U
#define TREEFORGE_RECOVERY_LP_EXTENT_ENTRY_SIZE 24U
#define TREEFORGE_RECOVERY_LP_GROUP_ENTRY_SIZE 48U
#define TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_ENTRY_SIZE 64U

#define TREEFORGE_RECOVERY_LP_TARGET_LINEAR 0U
#define TREEFORGE_RECOVERY_LP_TARGET_ZERO 1U

#define TREEFORGE_RECOVERY_LP_ATTR_READONLY (1U << 0)
#define TREEFORGE_RECOVERY_LP_ATTR_SLOT_SUFFIXED (1U << 1)
#define TREEFORGE_RECOVERY_LP_ATTR_UPDATED (1U << 2)
#define TREEFORGE_RECOVERY_LP_ATTR_DISABLED (1U << 3)

#define TREEFORGE_RECOVERY_LP_GROUP_SLOT_SUFFIXED (1U << 0)
#define TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_SLOT_SUFFIXED (1U << 0)

#define TREEFORGE_RECOVERY_LP_HEADER_VIRTUAL_AB_DEVICE 0x1U
#define TREEFORGE_RECOVERY_LP_HEADER_OVERLAYS_ACTIVE 0x2U

#define TREEFORGE_RECOVERY_LP_MAX_METADATA_SLOTS 4
#define TREEFORGE_RECOVERY_LP_MAX_PARTITIONS 256
#define TREEFORGE_RECOVERY_LP_MAX_EXTENTS 2048

/*
 * Read-only allocation-planning populations.
 *
 * A metadata graph cannot contain more useful allocation gaps than
 * LINEAR extents + 1 on one block device. Groups are bounded separately
 * so malformed metadata cannot grow the runtime inventory without limit.
 */
#define TREEFORGE_RECOVERY_LP_MAX_GROUPS 256
#define TREEFORGE_RECOVERY_LP_MAX_FREE_RANGES \
    (TREEFORGE_RECOVERY_LP_MAX_EXTENTS + 1)

/*
 * Unified Recovery partition-image target surface.
 *
 * Physical and logical partitions remain distinct internally, but Recovery
 * exposes both through one generic target model.
 */
#define TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL 1
#define TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL 2

#define TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL 0
#define TREEFORGE_RECOVERY_FLASH_POLICY_BLOCKED_BOOTLOADER 1

#define TREEFORGE_RECOVERY_MAX_FLASH_TARGETS 384

#define TREEFORGE_RECOVERY_IMAGE_FORMAT_UNKNOWN 0
#define TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW 1
#define TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE 2

#define TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V1 1
#define TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2 2

#define TREEFORGE_RECOVERY_INSTALL_METHOD_UNKNOWN 0
#define TREEFORGE_RECOVERY_INSTALL_METHOD_PHYSICAL_DIRECT 1
#define TREEFORGE_RECOVERY_INSTALL_METHOD_LOGICAL_DIRECT 2
#define TREEFORGE_RECOVERY_INSTALL_METHOD_SNAPSHOT_COW 3

#define TREEFORGE_RECOVERY_PAYLOAD_KIND_UNKNOWN 0
#define TREEFORGE_RECOVERY_PAYLOAD_KIND_IMAGE 1
#define TREEFORGE_RECOVERY_PAYLOAD_KIND_COW 2

#define TREEFORGE_RECOVERY_COW_COMPRESSION_NONE 0
#define TREEFORGE_RECOVERY_COW_COMPRESSION_LZ4 1

#define TREEFORGE_RECOVERY_SPARSE_MAGIC 0xed26ff3aU
#define TREEFORGE_RECOVERY_SPARSE_MAJOR_VERSION 1U
#define TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE 28U
#define TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE 12U

#define TREEFORGE_RECOVERY_SPARSE_CHUNK_RAW 0xCAC1U
#define TREEFORGE_RECOVERY_SPARSE_CHUNK_FILL 0xCAC2U
#define TREEFORGE_RECOVERY_SPARSE_CHUNK_DONT_CARE 0xCAC3U
#define TREEFORGE_RECOVERY_SPARSE_CHUNK_CRC32 0xCAC4U

#define TREEFORGE_RECOVERY_LP_NODE_PATH \
    "/dev/treeforge-recovery-super"

#define LINUX_REBOOT_MAGIC1 0xfee1deadUL
#define LINUX_REBOOT_MAGIC2 672274793UL
#define LINUX_REBOOT_CMD_RESTART 0x01234567UL

#define TREEFORGE_RECOVERY_REPORT_PATH \
    "/metadata/treeforge/recovery-runtime-report"

struct tf_linux_dirent64 {
    u64 d_ino;
    long long d_off;
    u16 d_reclen;
    unsigned char d_type;
    char d_name[];
};


struct tf_runtime_partition {
    char kernel_name[
        TREEFORGE_RECOVERY_KERNEL_NAME_CAPACITY
    ];

    char partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char canonical_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char device_name[
        TREEFORGE_RECOVERY_DEVICE_NAME_CAPACITY
    ];

    u32 major_number;
    u32 minor_number;

    u64 sectors;
    u64 capacity_bytes;

    char slot;
    int slot_pair;
    int active;
    int writable;

    int canonical_expected;
    int canonical_size_resolved;

    u64 canonical_image_size_bytes;

    int canonical_capacity_sufficient;
    int read_probe_eligible;
};


struct tf_runtime_partition_inventory {
    int active_slot_resolved;
    char active_slot;

    int partition_count;
    int partitions_omitted;
    int enumeration_error;

    /*
     * Read-only discovery diagnostics:
     *
     *   0 = no enumeration failure
     *   1 = /sys/class/block open
     *   2 = getdents64
     *   3 = malformed linux_dirent64
     *
     * enumeration_errno contains the positive Linux errno returned
     * by the raw syscall where applicable.
     */
    int enumeration_stage;
    u64 enumeration_errno;

    struct tf_runtime_partition partitions[
        TREEFORGE_RECOVERY_MAX_PARTITIONS
    ];
};


struct tf_recovery_lp_table_descriptor {
    u32 offset;
    u32 num_entries;
    u32 entry_size;
};


struct tf_recovery_lp_metadata_layout {
    u16 major_version;
    u16 minor_version;

    u32 header_size;
    u32 tables_size;

    struct tf_recovery_lp_table_descriptor partitions;
    struct tf_recovery_lp_table_descriptor extents;
    struct tf_recovery_lp_table_descriptor groups;
    struct tf_recovery_lp_table_descriptor block_devices;
};


struct tf_recovery_lp_slot_result {
    int attempted;
    int valid;

    u32 metadata_slot;
    char suffix;

    int primary_valid;
    int backup_used;

    u16 major_version;
    u16 minor_version;

    u32 header_size;
    u32 tables_size;
    u32 header_flags;

    /*
     * LP metadata slots and boot slots are different concepts.
     * Only metadata indexes 0 and 1 map to Android boot slots A/B.
     */
    int boot_slot_mapped;

    u32 partition_count;
    u32 extent_count;
    u32 group_count;
    u32 block_device_count;

    int error_stage;
    u64 error_errno;
};


struct tf_recovery_logical_partition {
    u32 metadata_slot;

    char partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char canonical_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char group_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char slot;
    int slot_pair;
    int active;

    u32 attributes;
    u32 first_extent_index;
    u32 num_extents;

    u64 sectors;
    u64 capacity_bytes;

    /*
     * Read-only milestone invariant.
     */
    int writable;
};


struct tf_recovery_logical_extent {
    u32 metadata_slot;

    char partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    u32 partition_extent_index;
    u32 table_extent_index;

    u64 num_sectors;
    u32 target_type;

    u64 target_data;
    u32 target_source;

    char block_device_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];
};


struct tf_recovery_lp_group {
    u32 metadata_slot;
    u32 table_group_index;

    char group_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    u32 flags;

    u64 maximum_size_bytes;
    u64 allocated_bytes;
    u64 remaining_bytes;

    int unlimited;
    int over_limit;
};


struct tf_recovery_lp_free_range {
    u64 start_sector;
    u64 end_sector;

    u64 num_sectors;
    u64 bytes;
};


struct tf_recovery_lp_inventory {
    int super_found;

    u32 super_major;
    u32 super_minor;
    u64 super_capacity_bytes;

    /*
     * Authoritative LP block-device boundary.
     *
     * first_logical_sector is the earliest sector in super that LP
     * metadata permits logical extents to occupy. Destructive logical
     * writers must never seek below this boundary.
     *
     * These values are published only from the metadata copy selected
     * by the active Android boot slot.
     */
    int super_data_region_resolved;
    u64 super_first_logical_sector;
    u64 super_device_size_bytes;

    int node_created;
    int open_succeeded;

    int geometry_resolved;
    int geometry_primary_valid;
    int geometry_backup_used;

    u32 metadata_max_size;
    u32 metadata_slot_count;
    u32 logical_block_size;

    int metadata_slots_read;
    int metadata_slots_valid;
    int metadata_slots_omitted;

    /*
     * TreeForge validates every metadata copy but publishes exactly
     * the copy selected by the real Android active boot slot.
     */
    int authoritative_slot_resolved;
    u32 authoritative_metadata_slot;
    int authoritative_metadata_valid;

    int virtual_ab;

    int partition_count;
    int partitions_omitted;

    int extent_count;
    int extents_omitted;

    /*
     * Serialized block-device allocation properties from authoritative
     * metadata. These remain descriptive only.
     */
    u32 super_alignment_bytes;
    u32 super_alignment_offset_bytes;

    /*
     * Authoritative partition-group population.
     */
    int group_count;
    int groups_omitted;

    /*
     * Read-only free-space derivation across source-0 LINEAR extents.
     */
    int free_space_resolved;
    int free_space_overlap;

    int free_range_count;
    int free_ranges_omitted;

    u64 free_sectors;
    u64 free_bytes;

    u64 largest_free_start_sector;
    u64 largest_free_sectors;
    u64 largest_free_bytes;

    int error_stage;
    u64 error_errno;

    struct tf_recovery_lp_slot_result slots[
        TREEFORGE_RECOVERY_LP_MAX_METADATA_SLOTS
    ];

    struct tf_recovery_logical_partition partitions[
        TREEFORGE_RECOVERY_LP_MAX_PARTITIONS
    ];

    struct tf_recovery_logical_extent extents[
        TREEFORGE_RECOVERY_LP_MAX_EXTENTS
    ];

    struct tf_recovery_lp_group groups[
        TREEFORGE_RECOVERY_LP_MAX_GROUPS
    ];

    struct tf_recovery_lp_free_range free_ranges[
        TREEFORGE_RECOVERY_LP_MAX_FREE_RANGES
    ];
};


struct tf_recovery_flash_target {
    int target_type;
    int flash_policy;

    char partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char canonical_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char slot;
    int slot_pair;
    int active;

    /*
     * selectable means the target belongs to the currently inactive slot.
     *
     * It does NOT authorize writes. writable remains hard-zero until a
     * separately validated destructive plan exists.
     */
    int selectable;
    int writable;

    u64 capacity_bytes;

    /*
     * Physical targets.
     */
    u32 physical_major;
    u32 physical_minor;

    /*
     * Logical targets.
     */
    u32 metadata_slot;
    u32 first_extent_index;
    u32 num_extents;
    u32 attributes;

    int allocation_present;
};


struct tf_recovery_flash_target_inventory {
    int active_slot_resolved;
    char active_slot;

    int default_install_slot_resolved;
    char default_install_slot;

    int target_count;
    int targets_omitted;

    int physical_count;
    int logical_count;

    int inactive_selectable_count;
    int active_blocked_count;
    int bootloader_blocked_count;

    struct tf_recovery_flash_target targets[
        TREEFORGE_RECOVERY_MAX_FLASH_TARGETS
    ];
};


struct tf_recovery_install_set_image {
    char canonical_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char target_partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    int image_format;

    u64 source_bytes;
    u64 expanded_bytes;

    char sha256[65];

    /*
     * Wire-v2 realization identity.
     *
     * source_bytes / expanded_bytes / sha256 describe the intended
     * final partition image.
     *
     * manifest_payload_bytes / manifest_payload_sha256 describe the
     * exact bytes transported through the Recovery FIFO.
     */
    int install_method;
    int manifest_payload_kind;

    u64 manifest_payload_bytes;
    char manifest_payload_sha256[65];

    u64 cow_version_major;
    u64 cow_version_minor;
    u64 cow_block_size;

    u64 cow_merge_ops;
    u64 cow_data_ops;
    u64 cow_replace_ops;
    u64 cow_zero_ops;
    u64 cow_copy_ops;
    u64 cow_xor_ops;

    int cow_compression;

    u32 sparse_block_size;
    u32 sparse_total_blocks;
    u32 sparse_total_chunks;

    u32 sparse_raw_chunks;
    u32 sparse_fill_chunks;
    u32 sparse_dont_care_chunks;
    u32 sparse_crc32_chunks;

    int target_resolved;
    int target_type;
    int target_flash_policy;
    int target_active;
    int target_selectable;

    u64 target_capacity_bytes;
    int target_allocation_present;

    int install_action;

    /*
     * Read-only streamed payload verification.
     *
     * These fields never imply write authorization.
     */
    int payload_verification_attempted;
    int payload_structure_valid;
    int payload_hash_succeeded;
    int payload_verified;

    u64 payload_bytes_received;

    char payload_sha256[65];

    /*
     * First staged-transaction destructive milestone.
     *
     * These fields describe only the explicit single physical RAW
     * test writer. They never imply whole-set completion or slot
     * activation eligibility.
     */
    int install_write_attempted;
    int install_written;
    int install_readback_verified;

    u64 install_bytes_written;

    /*
     * Source and destination identities diverge for Android sparse
     * images:
     *
     *   install_stream_sha256   = exact sparse source bytes
     *   install_expanded_sha256 = exact expanded logical image
     *   install_readback_sha256 = independent logical readback
     *
     * For RAW images the source and expanded identities are naturally
     * identical.
     */
    char install_stream_sha256[65];
    char install_expanded_sha256[65];
    char install_readback_sha256[65];

    int install_error_stage;
    u64 install_error_errno;
};


struct tf_recovery_install_set_result {
    int present;
    int parsed;
    int plan_resolved;

    int wire_version;
    int snapshot_cow_count;

    char target_slot;

    int image_count;

    int physical_count;
    int logical_count;

    int raw_count;
    int sparse_count;

    int allocation_count;
    int resize_count;

    int active_slot_resolved;
    char active_slot;
    int target_slot_safe;

    int payload_verification_started;
    int payload_verified_count;
    int payload_verification_complete;

    /*
     * Destructive staged-install transaction state.
     *
     * A started-but-incomplete transaction is intentionally not
     * restartable during this milestone. This prevents an implicit
     * retry from rewriting already completed members after a later
     * member fails.
     */
    int install_transaction_started;
    int install_transaction_complete;
    int install_transaction_failed;

    int install_written_count;
    int install_error_image_index;

    int payload_error_stage;
    int payload_error_image_index;
    u64 payload_error_errno;

    int error_stage;
    int error_image_index;
    u64 error_errno;

    struct tf_recovery_install_set_image images[
        TREEFORGE_RECOVERY_MAX_INSTALL_SET_IMAGES
    ];
};


struct tf_recovery_image_descriptor {
    int image_format;

    u64 source_bytes;
    u64 expanded_bytes;

    char sha256[65];

    u32 sparse_block_size;
    u32 sparse_total_blocks;
    u32 sparse_total_chunks;

    u32 sparse_raw_chunks;
    u32 sparse_fill_chunks;
    u32 sparse_dont_care_chunks;
    u32 sparse_crc32_chunks;

    int sparse_metadata_valid;
};


struct tf_recovery_image_inspection {
    int source_open_succeeded;
    int inspection_complete;

    int image_format;

    u64 source_bytes;
    u64 expanded_bytes;

    int sparse_structure_valid;
    u32 sparse_block_size;
    u32 sparse_total_blocks;
    u32 sparse_total_chunks;

    u32 sparse_raw_chunks;
    u32 sparse_fill_chunks;
    u32 sparse_dont_care_chunks;
    u32 sparse_crc32_chunks;

    int error_stage;
    u64 error_errno;
};


struct tf_recovery_unified_image_plan_result {
    int requested;

    char requested_partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    int target_resolved;
    int target_type;
    int target_flash_policy;

    char target_partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char target_canonical_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char target_slot;
    int target_active;
    int target_selectable;

    u64 target_capacity_bytes;
    int target_allocation_present;

    int source_open_succeeded;
    int source_inspected;
    int source_described;

    int source_descriptor_valid;
    int source_streaming;
    int source_manifest_valid;
    int source_identity_match;

    int source_format;

    char source_sha256[65];

    u64 source_bytes;
    u64 expanded_bytes;

    int sparse_structure_valid;
    u32 sparse_block_size;
    u32 sparse_total_blocks;
    u32 sparse_total_chunks;

    u32 sparse_raw_chunks;
    u32 sparse_fill_chunks;
    u32 sparse_dont_care_chunks;
    u32 sparse_crc32_chunks;

    /*
     * Capacity/allocation planning only.
     *
     * No field here authorizes a destructive operation.
     */
    int physical_capacity_sufficient;
    int fits_current_allocation;
    int allocation_required;
    int resize_required;
    int metadata_update_required;

    int plan_resolved;

    /*
     * Hard-zero until the physical/logical writers are explicitly
     * integrated behind this planner.
     */
    int write_ready;

    int error_stage;
    u64 error_errno;
};


struct tf_recovery_lp_read_probe_result {
    int requested;

    char requested_partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    int target_resolved;

    char target_partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char target_slot;
    int target_active;

    u32 metadata_slot;

    u32 expected_extents;
    u32 extents_read;
    u32 linear_extents;
    u32 zero_extents;

    u64 bytes_expected;
    u64 bytes_read;

    int extent_map_complete;

    int super_node_created;
    int super_open_succeeded;

    int hash_succeeded;
    char sha256[65];

    int error_stage;
    u64 error_errno;
};


struct tf_recovery_read_probe_result {
    int requested;

    char requested_canonical_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    int target_resolved;

    char target_partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char target_slot;
    int target_active;

    u32 target_major;
    u32 target_minor;

    u64 bytes_requested;
    u64 bytes_read;

    int node_created;
    int open_succeeded;
    int hash_succeeded;
    int hash_match;

    char expected_sha256[65];
    char actual_sha256[65];

    int error_stage;
    u64 error_errno;
};


struct tf_recovery_flash_plan_result {
    int requested;

    char requested_canonical_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    int target_resolved;

    char target_partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char target_slot;
    int target_active;

    u32 target_major;
    u32 target_minor;

    u64 target_capacity_bytes;
    u64 canonical_image_size_bytes;

    int source_open_succeeded;
    int source_hash_succeeded;
    int source_oversized;

    /*
     * Source transport identity.
     *
     * source_streaming == 0 preserves the existing regular-file path.
     * source_streaming == 1 means source_bytes/source_sha256 came from
     * a strictly validated TreeForge stream manifest.
     */
    int source_streaming;
    int source_manifest_valid;
    int source_stream_ready;

    u64 source_bytes;

    char canonical_sha256[65];
    char source_sha256[65];

    int source_matches_canonical;
    int source_size_matches_canonical;
    int source_fits_target;

    int target_ready;
    int plan_ready;

    int authorization_requested;
    int authorization_match;

    /*
     * A single-image plan is not proof that the complete AVB/boot
     * chain is coherent and therefore never makes a slot eligible
     * for activation.
     */
    int activation_eligible;

    int authorized;

    /*
     * Destructive writer lifecycle.
     *
     * written is final acceptance and becomes true only after the
     * reopened target hashes back to the exact authorized source
     * SHA-256.
     */
    int source_revalidated;
    int target_node_created;
    int target_open_succeeded;

    u64 bytes_written;

    int write_synced;

    /*
     * Streaming source digest measured from the exact bytes consumed
     * from the FIFO during the destructive transfer.
     */
    int streamed_hash_succeeded;
    char streamed_sha256[65];

    int verification_open_succeeded;
    int verification_hash_succeeded;
    int verification_match;

    char verified_sha256[65];

    int written;

    int error_stage;
    u64 error_errno;
};




static struct tf_runtime_partition_inventory
    tf_recovery_inventory;

static struct tf_recovery_lp_inventory
    tf_recovery_lp_inventory;

static struct tf_recovery_flash_target_inventory
    tf_recovery_flash_targets;

static struct tf_recovery_install_set_result
    tf_recovery_install_set;

static struct tf_recovery_unified_image_plan_result
    tf_recovery_unified_image_plan;

static struct tf_recovery_lp_read_probe_result
    tf_recovery_lp_read_probe;

static struct tf_recovery_read_probe_result
    tf_recovery_read_probe;

static struct tf_recovery_flash_plan_result
    tf_recovery_flash_plan;

static int tf_recovery_stream_fifo_ready = 0;


static long tf_syscall1(
    long number,
    long arg1
) {
    register long x8 asm("x8") = number;
    register long x0 asm("x0") = arg1;

    asm volatile(
        "svc 0"
        : "+r"(x0)
        : "r"(x8)
        : "memory"
    );

    return x0;
}


static long tf_syscall3(
    long number,
    long arg1,
    long arg2,
    long arg3
) {
    register long x8 asm("x8") = number;
    register long x0 asm("x0") = arg1;
    register long x1 asm("x1") = arg2;
    register long x2 asm("x2") = arg3;

    asm volatile(
        "svc 0"
        : "+r"(x0)
        : "r"(x8),
          "r"(x1),
          "r"(x2)
        : "memory"
    );

    return x0;
}


static long tf_syscall4(
    long number,
    long arg1,
    long arg2,
    long arg3,
    long arg4
) {
    register long x8 asm("x8") = number;
    register long x0 asm("x0") = arg1;
    register long x1 asm("x1") = arg2;
    register long x2 asm("x2") = arg3;
    register long x3 asm("x3") = arg4;

    asm volatile(
        "svc 0"
        : "+r"(x0)
        : "r"(x8),
          "r"(x1),
          "r"(x2),
          "r"(x3)
        : "memory"
    );

    return x0;
}


static long tf_syscall5(
    long number,
    long arg1,
    long arg2,
    long arg3,
    long arg4,
    long arg5
) {
    register long x8 asm("x8") = number;
    register long x0 asm("x0") = arg1;
    register long x1 asm("x1") = arg2;
    register long x2 asm("x2") = arg3;
    register long x3 asm("x3") = arg4;
    register long x4 asm("x4") = arg5;

    asm volatile(
        "svc 0"
        : "+r"(x0)
        : "r"(x8),
          "r"(x1),
          "r"(x2),
          "r"(x3),
          "r"(x4)
        : "memory"
    );

    return x0;
}


static usize tf_strlen(
    const char *value
) {
    usize length = 0;

    if (!value) {
        return 0;
    }

    while (
        value[length]
        != '\0'
    ) {
        length++;
    }

    return length;
}


static int tf_string_equal(
    const char *left,
    const char *right
) {
    if (
        !left
        || !right
    ) {
        return 0;
    }

    usize index = 0;

    while (
        left[index] != '\0'
        && right[index] != '\0'
    ) {
        if (
            left[index]
            != right[index]
        ) {
            return 0;
        }

        index++;
    }

    return (
        left[index] == '\0'
        && right[index] == '\0'
    );
}


static int tf_copy_string(
    char *destination,
    usize capacity,
    const char *source
) {
    if (
        !destination
        || !source
        || capacity == 0
    ) {
        return 0;
    }

    usize index = 0;

    while (
        source[index]
        != '\0'
    ) {
        if (
            index + 1
            >= capacity
        ) {
            destination[0] = '\0';
            return 0;
        }

        destination[index] = source[index];
        index++;
    }

    destination[index] = '\0';

    return 1;
}


static int tf_copy_range(
    char *destination,
    usize capacity,
    const char *source,
    usize length
) {
    if (
        !destination
        || !source
        || capacity == 0
        || length + 1 > capacity
    ) {
        return 0;
    }

    for (
        usize index = 0;
        index < length;
        index++
    ) {
        destination[index] = source[index];
    }

    destination[length] = '\0';

    return 1;
}


static int tf_join3(
    const char *left,
    const char *middle,
    const char *right,
    char *output,
    usize capacity
) {
    usize left_length = tf_strlen(
        left
    );

    usize middle_length = tf_strlen(
        middle
    );

    usize right_length = tf_strlen(
        right
    );

    usize required = (
        left_length
        + middle_length
        + right_length
        + 1
    );

    if (
        !output
        || required > capacity
    ) {
        return 0;
    }

    usize position = 0;

    for (
        usize index = 0;
        index < left_length;
        index++
    ) {
        output[position++] = left[index];
    }

    for (
        usize index = 0;
        index < middle_length;
        index++
    ) {
        output[position++] = middle[index];
    }

    for (
        usize index = 0;
        index < right_length;
        index++
    ) {
        output[position++] = right[index];
    }

    output[position] = '\0';

    return 1;
}


static long tf_open(
    const char *path,
    long flags
) {
    return tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) path,
        flags,
        0
    );
}


static void tf_close(
    long fd
) {
    if (fd >= 0) {
        tf_syscall1(
            SYS_CLOSE,
            fd
        );
    }
}


static long tf_read_path(
    const char *path,
    char *buffer,
    usize capacity
) {
    if (
        !path
        || !buffer
        || capacity < 2
    ) {
        return -1;
    }

    long fd = tf_open(
        path,
        O_RDONLY
        | O_NONBLOCK
    );

    if (fd < 0) {
        return -1;
    }

    long amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) buffer,
        (long) (
            capacity - 1
        )
    );

    tf_close(
        fd
    );

    if (amount < 0) {
        return -1;
    }

    buffer[amount] = '\0';

    return amount;
}


static int tf_parse_u64(
    const char *value,
    u64 *output
) {
    if (
        !value
        || !output
    ) {
        return 0;
    }

    u64 parsed = 0;
    int digits = 0;

    for (
        usize index = 0;
        value[index] != '\0';
        index++
    ) {
        char character = value[index];

        if (
            character == '\n'
            || character == '\r'
        ) {
            break;
        }

        if (
            character < '0'
            || character > '9'
        ) {
            return 0;
        }

        u64 digit = (
            (u64) (
                character - '0'
            )
        );

        if (
            parsed
            > (
                0xffffffffffffffffULL
                - digit
            ) / 10ULL
        ) {
            return 0;
        }

        parsed = (
            parsed * 10ULL
            + digit
        );

        digits++;
    }

    if (digits == 0) {
        return 0;
    }

    *output = parsed;

    return 1;
}



struct tf_sha256_context {
    u32 state[8];
    u64 total_bytes;

    unsigned char buffer[64];
    usize buffer_size;
};


static u32 tf_rotr32(
    u32 value,
    u32 count
) {
    return (
        value >> count
    ) | (
        value
        << (
            32U - count
        )
    );
}


static u32 tf_sha256_load_be32(
    const unsigned char *value
) {
    return (
        ((u32) value[0] << 24)
        | ((u32) value[1] << 16)
        | ((u32) value[2] << 8)
        | ((u32) value[3])
    );
}


static void tf_sha256_store_be32(
    unsigned char *output,
    u32 value
) {
    output[0] = (
        (unsigned char) (
            value >> 24
        )
    );

    output[1] = (
        (unsigned char) (
            value >> 16
        )
    );

    output[2] = (
        (unsigned char) (
            value >> 8
        )
    );

    output[3] = (
        (unsigned char) value
    );
}


static void tf_sha256_transform(
    struct tf_sha256_context *context,
    const unsigned char block[64]
) {
    static const u32 constants[64] = {
        0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
        0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
        0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
        0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
        0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
        0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
        0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
        0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
        0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
        0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
        0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
        0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
        0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
        0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
        0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
        0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U,
    };

    u32 words[64];

    for (
        int index = 0;
        index < 16;
        index++
    ) {
        words[index] = (
            tf_sha256_load_be32(
                block
                + (
                    index * 4
                )
            )
        );
    }

    for (
        int index = 16;
        index < 64;
        index++
    ) {
        u32 s0 = (
            tf_rotr32(
                words[index - 15],
                7
            )
            ^ tf_rotr32(
                words[index - 15],
                18
            )
            ^ (
                words[index - 15]
                >> 3
            )
        );

        u32 s1 = (
            tf_rotr32(
                words[index - 2],
                17
            )
            ^ tf_rotr32(
                words[index - 2],
                19
            )
            ^ (
                words[index - 2]
                >> 10
            )
        );

        words[index] = (
            words[index - 16]
            + s0
            + words[index - 7]
            + s1
        );
    }

    u32 a = context->state[0];
    u32 b = context->state[1];
    u32 c = context->state[2];
    u32 d = context->state[3];
    u32 e = context->state[4];
    u32 f = context->state[5];
    u32 g = context->state[6];
    u32 h = context->state[7];

    for (
        int index = 0;
        index < 64;
        index++
    ) {
        u32 sum1 = (
            tf_rotr32(
                e,
                6
            )
            ^ tf_rotr32(
                e,
                11
            )
            ^ tf_rotr32(
                e,
                25
            )
        );

        u32 choose = (
            (e & f)
            ^ (
                (~e) & g
            )
        );

        u32 temporary1 = (
            h
            + sum1
            + choose
            + constants[index]
            + words[index]
        );

        u32 sum0 = (
            tf_rotr32(
                a,
                2
            )
            ^ tf_rotr32(
                a,
                13
            )
            ^ tf_rotr32(
                a,
                22
            )
        );

        u32 majority = (
            (a & b)
            ^ (a & c)
            ^ (b & c)
        );

        u32 temporary2 = (
            sum0
            + majority
        );

        h = g;
        g = f;
        f = e;
        e = d + temporary1;
        d = c;
        c = b;
        b = a;
        a = temporary1 + temporary2;
    }

    context->state[0] += a;
    context->state[1] += b;
    context->state[2] += c;
    context->state[3] += d;
    context->state[4] += e;
    context->state[5] += f;
    context->state[6] += g;
    context->state[7] += h;
}


static void tf_sha256_init(
    struct tf_sha256_context *context
) {
    memset(
        context,
        0,
        sizeof(*context)
    );

    context->state[0] = 0x6a09e667U;
    context->state[1] = 0xbb67ae85U;
    context->state[2] = 0x3c6ef372U;
    context->state[3] = 0xa54ff53aU;
    context->state[4] = 0x510e527fU;
    context->state[5] = 0x9b05688cU;
    context->state[6] = 0x1f83d9abU;
    context->state[7] = 0x5be0cd19U;
}


static void tf_sha256_update(
    struct tf_sha256_context *context,
    const unsigned char *data,
    usize length
) {
    context->total_bytes += (
        (u64) length
    );

    while (length > 0) {
        usize available = (
            64
            - context->buffer_size
        );

        usize amount = (
            length < available
            ? length
            : available
        );

        memcpy(
            context->buffer
                + context->buffer_size,
            data,
            amount
        );

        context->buffer_size += amount;
        data += amount;
        length -= amount;

        if (
            context->buffer_size
            == 64
        ) {
            tf_sha256_transform(
                context,
                context->buffer
            );

            context->buffer_size = 0;
        }
    }
}


static void tf_sha256_final(
    struct tf_sha256_context *context,
    unsigned char digest[32]
) {
    u64 bit_count = (
        context->total_bytes
        * 8ULL
    );

    context->buffer[
        context->buffer_size++
    ] = 0x80;

    if (
        context->buffer_size
        > 56
    ) {
        while (
            context->buffer_size
            < 64
        ) {
            context->buffer[
                context->buffer_size++
            ] = 0;
        }

        tf_sha256_transform(
            context,
            context->buffer
        );

        context->buffer_size = 0;
    }

    while (
        context->buffer_size
        < 56
    ) {
        context->buffer[
            context->buffer_size++
        ] = 0;
    }

    for (
        int index = 0;
        index < 8;
        index++
    ) {
        context->buffer[
            63 - index
        ] = (
            (unsigned char) (
                bit_count
                >> (
                    index * 8
                )
            )
        );
    }

    tf_sha256_transform(
        context,
        context->buffer
    );

    for (
        int index = 0;
        index < 8;
        index++
    ) {
        tf_sha256_store_be32(
            digest
                + (
                    index * 4
                ),
            context->state[index]
        );
    }
}


static void tf_sha256_hex(
    const unsigned char digest[32],
    char output[65]
) {
    static const char hex[] =
        "0123456789abcdef";

    for (
        int index = 0;
        index < 32;
        index++
    ) {
        output[
            index * 2
        ] = hex[
            digest[index] >> 4
        ];

        output[
            index * 2 + 1
        ] = hex[
            digest[index] & 0x0f
        ];
    }

    output[64] = '\0';
}


static int tf_extract_uevent_value(
    const char *buffer,
    const char *key,
    char *output,
    usize capacity
) {
    if (
        !buffer
        || !key
        || !output
        || capacity == 0
    ) {
        return 0;
    }

    usize key_length = tf_strlen(
        key
    );

    usize position = 0;

    while (
        buffer[position]
        != '\0'
    ) {
        usize line_start = position;

        while (
            buffer[position] != '\0'
            && buffer[position] != '\n'
        ) {
            position++;
        }

        usize line_length = (
            position - line_start
        );

        if (
            line_length > key_length
            && memcmp(
                buffer + line_start,
                key,
                key_length
            ) == 0
            && buffer[
                line_start
                + key_length
            ] == '='
        ) {
            usize value_start = (
                line_start
                + key_length
                + 1
            );

            usize value_length = (
                line_length
                - key_length
                - 1
            );

            return tf_copy_range(
                output,
                capacity,
                buffer + value_start,
                value_length
            );
        }

        if (
            buffer[position]
            == '\n'
        ) {
            position++;
        }
    }

    return 0;
}


static char tf_parse_slot_value(
    const char *value,
    usize length
) {
    usize position = 0;

    while (
        position < length
        && (
            value[position] == ' '
            || value[position] == '\t'
            || value[position] == '"'
        )
    ) {
        position++;
    }

    if (
        position < length
        && value[position] == '_'
    ) {
        position++;
    }

    if (
        position < length
        && (
            value[position] == 'a'
            || value[position] == 'b'
        )
    ) {
        return value[position];
    }

    return 0;
}



static int tf_recovery_manifest_match(
    const char *buffer,
    usize length,
    usize *position,
    const char *literal
) {
    if (
        !buffer
        || !position
        || !literal
    ) {
        return 0;
    }

    usize cursor = *position;

    for (
        usize index = 0;
        literal[index] != '\0';
        index++
    ) {
        if (
            cursor >= length
            || buffer[cursor] != literal[index]
        ) {
            return 0;
        }

        cursor++;
    }

    *position = cursor;

    return 1;
}


static int tf_recovery_load_stream_manifest(
    u64 *bytes,
    char sha256[65]
) {
    if (
        !bytes
        || !sha256
    ) {
        return -1;
    }

    *bytes = 0;
    sha256[0] = '\0';

    char buffer[256];

    /*
     * Do not use tf_read_path() here.
     *
     * That generic helper intentionally collapses open/read failures
     * to -1, but source selection must distinguish a genuinely absent
     * manifest (ENOENT) from every other failure.
     */
    long manifest = tf_open(
        TREEFORGE_RECOVERY_STREAM_MANIFEST_PATH,
        O_RDONLY
        | O_NONBLOCK
    );

    if (manifest < 0) {
        if (manifest == -2) {
            /*
             * ENOENT: no streaming manifest exists, so the accepted
             * regular-file staging fallback remains eligible.
             */
            return 0;
        }

        /*
         * Any other open failure is fail-closed. Never silently select
         * a different staged source identity.
         */
        return -1;
    }

    long amount = tf_syscall3(
        SYS_READ,
        manifest,
        (long) buffer,
        (long) (
            sizeof(buffer) - 1
        )
    );

    tf_close(
        manifest
    );

    if (amount < 0) {
        /*
         * A manifest that opened successfully but could not be read is
         * also fail-closed.
         */
        return -1;
    }

    if (amount == 0) {
        return -1;
    }

    buffer[amount] = '\0';

    usize length = (usize) amount;
    usize position = 0;

    if (
        !tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "treeforge-recovery-stream-v1\n"
        )
        || !tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "bytes="
        )
    ) {
        return -1;
    }

    u64 parsed_bytes = 0;
    int digits = 0;

    while (
        position < length
        && buffer[position] != '\n'
    ) {
        char value = buffer[position];

        if (
            value < '0'
            || value > '9'
        ) {
            return -1;
        }

        u64 digit = (u64) (
            value - '0'
        );

        if (
            parsed_bytes
            > (
                (~0ULL - digit)
                / 10ULL
            )
        ) {
            return -1;
        }

        parsed_bytes = (
            parsed_bytes * 10ULL
            + digit
        );

        digits++;
        position++;
    }

    if (
        digits == 0
        || parsed_bytes == 0
        || position >= length
        || buffer[position] != '\n'
    ) {
        return -1;
    }

    position++;

    if (
        !tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "sha256="
        )
    ) {
        return -1;
    }

    for (
        int index = 0;
        index < 64;
        index++
    ) {
        if (position >= length) {
            return -1;
        }

        char value = buffer[position++];

        int valid = (
            (
                value >= '0'
                && value <= '9'
            )
            || (
                value >= 'a'
                && value <= 'f'
            )
            || (
                value >= 'A'
                && value <= 'F'
            )
        );

        if (!valid) {
            return -1;
        }

        if (
            value >= 'A'
            && value <= 'F'
        ) {
            value = (
                value
                - 'A'
                + 'a'
            );
        }

        sha256[index] = value;
    }

    sha256[64] = '\0';

    if (
        position >= length
        || buffer[position] != '\n'
    ) {
        return -1;
    }

    position++;

    /*
     * Strict framing: no extra keys, whitespace, or trailing bytes.
     */
    if (position != length) {
        return -1;
    }

    *bytes = parsed_bytes;

    return 1;
}


static int tf_recovery_descriptor_parse_u64_field(
    const char *buffer,
    usize length,
    usize *position,
    const char *key,
    u64 *output
) {
    if (
        !buffer
        || !position
        || !key
        || !output
    ) {
        return 0;
    }

    if (
        !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            key
        )
    ) {
        return 0;
    }

    u64 parsed = 0;
    int digits = 0;

    while (
        *position < length
        && buffer[*position] != '\n'
    ) {
        char value = buffer[*position];

        if (
            value < '0'
            || value > '9'
        ) {
            return 0;
        }

        u64 digit = (
            (u64) (
                value - '0'
            )
        );

        if (
            parsed
            > (
                0xffffffffffffffffULL
                - digit
            ) / 10ULL
        ) {
            return 0;
        }

        parsed = (
            parsed * 10ULL
            + digit
        );

        digits++;
        (*position)++;
    }

    if (
        digits == 0
        || *position >= length
        || buffer[*position] != '\n'
    ) {
        return 0;
    }

    (*position)++;

    *output = parsed;

    return 1;
}


static int tf_recovery_descriptor_parse_sha256(
    const char *buffer,
    usize length,
    usize *position,
    char sha256[65]
) {
    if (
        !buffer
        || !position
        || !sha256
    ) {
        return 0;
    }

    if (
        !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "sha256="
        )
    ) {
        return 0;
    }

    for (
        int index = 0;
        index < 64;
        index++
    ) {
        if (*position >= length) {
            return 0;
        }

        char value = buffer[(*position)++];

        int valid = (
            (
                value >= '0'
                && value <= '9'
            )
            || (
                value >= 'a'
                && value <= 'f'
            )
            || (
                value >= 'A'
                && value <= 'F'
            )
        );

        if (!valid) {
            return 0;
        }

        if (
            value >= 'A'
            && value <= 'F'
        ) {
            value = (
                value
                - 'A'
                + 'a'
            );
        }

        sha256[index] = value;
    }

    sha256[64] = '\0';

    if (
        *position >= length
        || buffer[*position] != '\n'
    ) {
        return 0;
    }

    (*position)++;

    return 1;
}


/*
 * Return contract:
 *
 *   0  descriptor absent
 *   1  descriptor present and strictly valid
 *  -1  descriptor present but malformed/unreadable
 *
 * The descriptor is planning metadata only. For streamed input its
 * bytes + sha256 must independently match the hardware-accepted stream
 * manifest before the planner may consume any of its format metadata.
 */
static int tf_recovery_load_image_descriptor(
    struct tf_recovery_image_descriptor *descriptor
) {
    if (!descriptor) {
        return -1;
    }

    memset(
        descriptor,
        0,
        sizeof(*descriptor)
    );

    long fd = tf_open(
        TREEFORGE_RECOVERY_IMAGE_DESCRIPTOR_PATH,
        O_RDONLY
        | O_NONBLOCK
    );

    if (fd < 0) {
        if (fd == -2) {
            return 0;
        }

        return -1;
    }

    char buffer[1024];

    long amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) buffer,
        sizeof(buffer) - 1
    );

    if (amount <= 0) {
        tf_close(fd);
        return -1;
    }

    /*
     * Reject an oversized/truncated descriptor rather than parsing a
     * valid-looking prefix.
     */
    char extra = 0;

    long extra_amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) &extra,
        1
    );

    tf_close(fd);

    if (
        extra_amount < 0
        || extra_amount != 0
    ) {
        return -1;
    }

    buffer[amount] = '\0';

    usize length = (
        (usize) amount
    );

    usize position = 0;

    if (
        !tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "treeforge-recovery-image-descriptor-v1\n"
        )
        || !tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "format="
        )
    ) {
        return -1;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "raw\n"
        )
    ) {
        descriptor->image_format = (
            TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        );
    } else if (
        tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "android-sparse\n"
        )
    ) {
        descriptor->image_format = (
            TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
        );
    } else {
        return -1;
    }

    u64 block_size = 0;
    u64 total_blocks = 0;
    u64 total_chunks = 0;
    u64 raw_chunks = 0;
    u64 fill_chunks = 0;
    u64 dont_care_chunks = 0;
    u64 crc32_chunks = 0;

    if (
        !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "bytes=",
            &descriptor->source_bytes
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "expanded_bytes=",
            &descriptor->expanded_bytes
        )
        || !tf_recovery_descriptor_parse_sha256(
            buffer,
            length,
            &position,
            descriptor->sha256
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "block_size=",
            &block_size
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "total_blocks=",
            &total_blocks
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "total_chunks=",
            &total_chunks
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "raw_chunks=",
            &raw_chunks
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "fill_chunks=",
            &fill_chunks
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "dont_care_chunks=",
            &dont_care_chunks
        )
        || !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "crc32_chunks=",
            &crc32_chunks
        )
        || position != length
    ) {
        return -1;
    }

    if (
        descriptor->source_bytes == 0
        || descriptor->expanded_bytes == 0
        || block_size > 0xffffffffULL
        || total_blocks > 0xffffffffULL
        || total_chunks > 0xffffffffULL
        || raw_chunks > 0xffffffffULL
        || fill_chunks > 0xffffffffULL
        || dont_care_chunks > 0xffffffffULL
        || crc32_chunks > 0xffffffffULL
    ) {
        return -1;
    }

    descriptor->sparse_block_size = (
        (u32) block_size
    );

    descriptor->sparse_total_blocks = (
        (u32) total_blocks
    );

    descriptor->sparse_total_chunks = (
        (u32) total_chunks
    );

    descriptor->sparse_raw_chunks = (
        (u32) raw_chunks
    );

    descriptor->sparse_fill_chunks = (
        (u32) fill_chunks
    );

    descriptor->sparse_dont_care_chunks = (
        (u32) dont_care_chunks
    );

    descriptor->sparse_crc32_chunks = (
        (u32) crc32_chunks
    );

    if (
        descriptor->image_format
        == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
    ) {
        if (
            descriptor->expanded_bytes
                != descriptor->source_bytes
            || block_size != 0
            || total_blocks != 0
            || total_chunks != 0
            || raw_chunks != 0
            || fill_chunks != 0
            || dont_care_chunks != 0
            || crc32_chunks != 0
        ) {
            return -1;
        }

        return 1;
    }

    if (
        descriptor->image_format
        != TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
    ) {
        return -1;
    }

    if (
        block_size == 0
        || (
            block_size % 4ULL
        ) != 0
        || total_blocks == 0
        || total_chunks == 0
    ) {
        return -1;
    }

    u64 expected_expanded = (
        total_blocks
        * block_size
    );

    if (
        expected_expanded
        != descriptor->expanded_bytes
    ) {
        return -1;
    }

    u64 described_chunks = (
        raw_chunks
        + fill_chunks
        + dont_care_chunks
        + crc32_chunks
    );

    if (
        described_chunks
        != total_chunks
    ) {
        return -1;
    }

    descriptor->sparse_metadata_valid = 1;

    return 1;
}


static int tf_recovery_prepare_stream_fifo(void) {
    tf_recovery_stream_fifo_ready = 0;

    /*
     * /dev is boot-local. TreeForge owns this exact endpoint.
     */
    long unlink_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_STREAM_FIFO_PATH,
        0
    );

    if (
        unlink_result < 0
        && unlink_result != -2
    ) {
        return 0;
    }

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_STREAM_FIFO_PATH,
        S_IFIFO | 0600,
        0
    );

    if (node_result < 0) {
        return 0;
    }

    tf_recovery_stream_fifo_ready = 1;

    return 1;
}



static char tf_slot_from_bootconfig(void) {
    char buffer[16384];

    long amount = tf_read_path(
        "/proc/bootconfig",
        buffer,
        sizeof(buffer)
    );

    if (amount <= 0) {
        return 0;
    }

    static const char key[] =
        "androidboot.slot_suffix";

    usize key_length = (
        sizeof(key) - 1
    );

    usize position = 0;

    while (
        position < (usize) amount
    ) {
        usize line_start = position;

        while (
            position < (usize) amount
            && buffer[position] != '\n'
        ) {
            position++;
        }

        usize line_end = position;

        usize cursor = line_start;

        while (
            cursor < line_end
            && (
                buffer[cursor] == ' '
                || buffer[cursor] == '\t'
            )
        ) {
            cursor++;
        }

        if (
            line_end - cursor >= key_length
            && memcmp(
                buffer + cursor,
                key,
                key_length
            ) == 0
        ) {
            cursor += key_length;

            while (
                cursor < line_end
                && (
                    buffer[cursor] == ' '
                    || buffer[cursor] == '\t'
                )
            ) {
                cursor++;
            }

            if (
                cursor < line_end
                && buffer[cursor] == '='
            ) {
                cursor++;

                char slot = tf_parse_slot_value(
                    buffer + cursor,
                    line_end - cursor
                );

                if (slot) {
                    return slot;
                }
            }
        }

        if (
            position < (usize) amount
            && buffer[position] == '\n'
        ) {
            position++;
        }
    }

    return 0;
}


static char tf_slot_from_cmdline(void) {
    char buffer[8192];

    long amount = tf_read_path(
        "/proc/cmdline",
        buffer,
        sizeof(buffer)
    );

    if (amount <= 0) {
        return 0;
    }

    static const char suffix_key[] =
        "androidboot.slot_suffix=";

    static const char slot_key[] =
        "androidboot.slot=";

    usize position = 0;

    while (
        position < (usize) amount
    ) {
        while (
            position < (usize) amount
            && (
                buffer[position] == ' '
                || buffer[position] == '\n'
                || buffer[position] == '\r'
                || buffer[position] == '\t'
            )
        ) {
            position++;
        }

        usize token_start = position;

        while (
            position < (usize) amount
            && buffer[position] != ' '
            && buffer[position] != '\n'
            && buffer[position] != '\r'
            && buffer[position] != '\t'
        ) {
            position++;
        }

        usize token_length = (
            position - token_start
        );

        usize suffix_length = (
            sizeof(suffix_key) - 1
        );

        if (
            token_length > suffix_length
            && memcmp(
                buffer + token_start,
                suffix_key,
                suffix_length
            ) == 0
        ) {
            char slot = tf_parse_slot_value(
                buffer
                + token_start
                + suffix_length,
                token_length
                - suffix_length
            );

            if (slot) {
                return slot;
            }
        }

        usize slot_length = (
            sizeof(slot_key) - 1
        );

        if (
            token_length > slot_length
            && memcmp(
                buffer + token_start,
                slot_key,
                slot_length
            ) == 0
        ) {
            char slot = tf_parse_slot_value(
                buffer
                + token_start
                + slot_length,
                token_length
                - slot_length
            );

            if (slot) {
                return slot;
            }
        }
    }

    return 0;
}


static char tf_resolve_active_slot(void) {
    char slot = tf_slot_from_bootconfig();

    if (slot) {
        return slot;
    }

    return tf_slot_from_cmdline();
}


static int tf_partition_slot_candidate(
    const char *partition_name,
    char *canonical_name,
    usize canonical_capacity,
    char *slot
) {
    usize length = tf_strlen(
        partition_name
    );

    if (
        length > 2
        && partition_name[
            length - 2
        ] == '_'
        && (
            partition_name[
                length - 1
            ] == 'a'
            || partition_name[
                length - 1
            ] == 'b'
        )
    ) {
        if (
            !tf_copy_range(
                canonical_name,
                canonical_capacity,
                partition_name,
                length - 2
            )
        ) {
            return 0;
        }

        *slot = partition_name[
            length - 1
        ];

        return 1;
    }

    if (
        !tf_copy_string(
            canonical_name,
            canonical_capacity,
            partition_name
        )
    ) {
        return 0;
    }

    *slot = 0;

    return 1;
}


static int tf_collect_partition(
    const char *kernel_name,
    struct tf_runtime_partition_inventory *inventory
) {
    if (
        !kernel_name
        || !inventory
    ) {
        return 0;
    }

    char path[256];
    char probe[32];

    if (
        !tf_join3(
            "/sys/class/block/",
            kernel_name,
            "/partition",
            path,
            sizeof(path)
        )
    ) {
        return 0;
    }

    if (
        tf_read_path(
            path,
            probe,
            sizeof(probe)
        ) <= 0
    ) {
        return 0;
    }

    if (
        inventory->partition_count
        >= TREEFORGE_RECOVERY_MAX_PARTITIONS
    ) {
        inventory->partitions_omitted = 1;
        return 0;
    }

    char uevent_path[256];

    if (
        !tf_join3(
            "/sys/class/block/",
            kernel_name,
            "/uevent",
            uevent_path,
            sizeof(uevent_path)
        )
    ) {
        inventory->partitions_omitted = 1;
        return 0;
    }

    char uevent[1024];

    if (
        tf_read_path(
            uevent_path,
            uevent,
            sizeof(uevent)
        ) <= 0
    ) {
        return 0;
    }

    char major_text[32];
    char minor_text[32];

    struct tf_runtime_partition *record = (
        &inventory->partitions[
            inventory->partition_count
        ]
    );

    memset(
        record,
        0,
        sizeof(*record)
    );

    if (
        !tf_copy_string(
            record->kernel_name,
            sizeof(record->kernel_name),
            kernel_name
        )
        || !tf_extract_uevent_value(
            uevent,
            "PARTNAME",
            record->partition_name,
            sizeof(record->partition_name)
        )
        || !tf_extract_uevent_value(
            uevent,
            "DEVNAME",
            record->device_name,
            sizeof(record->device_name)
        )
        || !tf_extract_uevent_value(
            uevent,
            "MAJOR",
            major_text,
            sizeof(major_text)
        )
        || !tf_extract_uevent_value(
            uevent,
            "MINOR",
            minor_text,
            sizeof(minor_text)
        )
    ) {
        return 0;
    }

    u64 major_number;
    u64 minor_number;

    if (
        !tf_parse_u64(
            major_text,
            &major_number
        )
        || !tf_parse_u64(
            minor_text,
            &minor_number
        )
        || major_number > 0xffffffffULL
        || minor_number > 0xffffffffULL
    ) {
        return 0;
    }

    record->major_number = (
        (u32) major_number
    );

    record->minor_number = (
        (u32) minor_number
    );

    char size_path[256];

    if (
        !tf_join3(
            "/sys/class/block/",
            kernel_name,
            "/size",
            size_path,
            sizeof(size_path)
        )
    ) {
        return 0;
    }

    char size_text[64];

    if (
        tf_read_path(
            size_path,
            size_text,
            sizeof(size_text)
        ) <= 0
    ) {
        return 0;
    }

    if (
        !tf_parse_u64(
            size_text,
            &record->sectors
        )
    ) {
        return 0;
    }

    if (
        record->sectors
        > (
            0xffffffffffffffffULL
            / 512ULL
        )
    ) {
        return 0;
    }

    record->capacity_bytes = (
        record->sectors * 512ULL
    );

    if (
        !tf_partition_slot_candidate(
            record->partition_name,
            record->canonical_name,
            sizeof(record->canonical_name),
            &record->slot
        )
    ) {
        return 0;
    }

    /*
     * The initial recovery implementation is strictly read-only.
     * Writable remains false for every discovered partition.
     */
    record->writable = 0;

    inventory->partition_count++;

    return 1;
}


static void tf_resolve_slot_pairs(
    struct tf_runtime_partition_inventory *inventory
) {
    for (
        int left_index = 0;
        left_index < inventory->partition_count;
        left_index++
    ) {
        struct tf_runtime_partition *left = (
            &inventory->partitions[
                left_index
            ]
        );

        if (
            left->slot != 'a'
            && left->slot != 'b'
        ) {
            continue;
        }

        char required_slot = (
            left->slot == 'a'
            ? 'b'
            : 'a'
        );

        for (
            int right_index = 0;
            right_index < inventory->partition_count;
            right_index++
        ) {
            if (
                right_index
                == left_index
            ) {
                continue;
            }

            struct tf_runtime_partition *right = (
                &inventory->partitions[
                    right_index
                ]
            );

            if (
                right->slot
                == required_slot
                && tf_string_equal(
                    left->canonical_name,
                    right->canonical_name
                )
            ) {
                left->slot_pair = 1;
                break;
            }
        }

        if (
            left->slot_pair
            && inventory->active_slot_resolved
            && left->slot
                == inventory->active_slot
        ) {
            left->active = 1;
        }
    }
}



static const struct tf_canonical_partition_expectation *
tf_find_canonical_expectation(
    const char *canonical_name
) {
    if (!canonical_name) {
        return 0;
    }

    for (
        usize index = 0;
        index
            < (
                usize
            ) TREEFORGE_RECOVERY_CANONICAL_EXPECTATION_COUNT;
        index++
    ) {
        const struct tf_canonical_partition_expectation
            *expectation = (
                &tf_canonical_partition_expectations[index]
            );

        if (
            tf_string_equal(
                expectation->canonical_name,
                canonical_name
            )
        ) {
            return expectation;
        }
    }

    return 0;
}


static void tf_apply_canonical_expectations(
    struct tf_runtime_partition_inventory *inventory
) {
    if (!inventory) {
        return;
    }

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        struct tf_runtime_partition *record = (
            &inventory->partitions[index]
        );

        record->canonical_expected = 0;
        record->canonical_size_resolved = 0;
        record->canonical_image_size_bytes = 0;
        record->canonical_capacity_sufficient = 0;
        record->read_probe_eligible = 0;

        const struct tf_canonical_partition_expectation
            *expectation = (
                tf_find_canonical_expectation(
                    record->canonical_name
                )
            );

        if (!expectation) {
            continue;
        }

        record->canonical_expected = 1;

        record->canonical_size_resolved = (
            expectation->image_size_resolved
        );

        record->canonical_image_size_bytes = (
            expectation->canonical_image_size_bytes
        );

        if (
            expectation->image_size_resolved
            && record->capacity_bytes
                >= expectation->canonical_image_size_bytes
        ) {
            record->canonical_capacity_sufficient = 1;
        }

        /*
         * Initial recovery authorization is intentionally read-only.
         *
         * Runtime identity must match a canonical factory-derived
         * expectation. The expectation itself must represent a
         * physical, size-resolved read-probe candidate, and the live
         * physical target must be large enough to contain the
         * canonical image.
         *
         * Slot activation state does not authorize or deny reading.
         * It remains independent live evidence used by later target
         * selection policy.
         */
        if (
            expectation->read_probe_candidate
            && !expectation->logical
            && expectation->image_size_resolved
            && record->canonical_capacity_sufficient
        ) {
            record->read_probe_eligible = 1;
        }

        /*
         * Canonical comparison must never make a target writable.
         */
        record->writable = 0;
    }
}


static u64 tf_read_probe_eligible_count(
    const struct tf_runtime_partition_inventory *inventory
) {
    if (!inventory) {
        return 0;
    }

    u64 count = 0;

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        if (
            inventory
            ->partitions[index]
            .read_probe_eligible
        ) {
            count++;
        }
    }

    return count;
}



static int tf_parse_read_probe_name(
    const char *buffer,
    usize length,
    char *output,
    usize capacity
) {
    if (
        !buffer
        || !output
        || capacity == 0
    ) {
        return 0;
    }

    usize start = 0;

    while (
        start < length
        && (
            buffer[start] == ' '
            || buffer[start] == '\t'
            || buffer[start] == '\r'
            || buffer[start] == '\n'
        )
    ) {
        start++;
    }

    usize end = length;

    while (
        end > start
        && (
            buffer[end - 1] == ' '
            || buffer[end - 1] == '\t'
            || buffer[end - 1] == '\r'
            || buffer[end - 1] == '\n'
        )
    ) {
        end--;
    }

    if (
        end <= start
        || end - start + 1 > capacity
    ) {
        return 0;
    }

    for (
        usize index = start;
        index < end;
        index++
    ) {
        char character = buffer[index];

        int allowed = (
            (
                character >= 'a'
                && character <= 'z'
            )
            || (
                character >= 'A'
                && character <= 'Z'
            )
            || (
                character >= '0'
                && character <= '9'
            )
            || character == '_'
            || character == '-'
            || character == '.'
        );

        if (!allowed) {
            return 0;
        }
    }

    return tf_copy_range(
        output,
        capacity,
        buffer + start,
        end - start
    );
}


static int tf_encode_device_number(
    u32 major_number,
    u32 minor_number,
    u64 *output
) {
    if (
        !output
        || major_number > 0xfffU
        || minor_number > 0xfffffU
    ) {
        return 0;
    }

    *output = (
        ((u64) minor_number & 0xffULL)
        | (
            ((u64) major_number)
            << 8
        )
        | (
            (
                (u64) minor_number
                & 0xfffff00ULL
            )
            << 12
        )
    );

    return 1;
}


static int tf_hash_fd_exact(
    long fd,
    u64 requested_bytes,
    char output[65],
    u64 *bytes_read,
    u64 *error_errno
) {
    if (
        fd < 0
        || !output
        || !bytes_read
        || !error_errno
    ) {
        return 0;
    }

    *bytes_read = 0;
    *error_errno = 0;

    struct tf_sha256_context context;

    tf_sha256_init(
        &context
    );

    unsigned char buffer[4096];

    u64 remaining = (
        requested_bytes
    );

    while (
        remaining > 0
    ) {
        usize requested = (
            remaining < sizeof(buffer)
            ? (usize) remaining
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) buffer,
            requested
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (
                    -amount
                )
            );

            return 0;
        }

        if (amount == 0) {
            return 0;
        }

        tf_sha256_update(
            &context,
            buffer,
            (usize) amount
        );

        *bytes_read += (
            (u64) amount
        );

        remaining -= (
            (u64) amount
        );
    }

    unsigned char digest[32];

    tf_sha256_final(
        &context,
        digest
    );

    tf_sha256_hex(
        digest,
        output
    );

    return 1;
}



static int tf_hash_fd_to_eof_bounded(
    long fd,
    u64 maximum_bytes,
    char output[65],
    u64 *bytes_read,
    int *oversized,
    u64 *error_errno
) {
    if (
        fd < 0
        || !output
        || !bytes_read
        || !oversized
        || !error_errno
    ) {
        return 0;
    }

    *bytes_read = 0;
    *oversized = 0;
    *error_errno = 0;

    output[0] = '\0';

    struct tf_sha256_context context;

    tf_sha256_init(
        &context
    );

    unsigned char buffer[4096];

    u64 total = 0;

    for (;;) {
        usize requested = sizeof(buffer);

        if (
            total >= maximum_bytes
        ) {
            /*
             * One additional byte is enough to distinguish an exact
             * capacity-sized file from an oversized source.
             */
            requested = 1;
        } else {
            u64 remaining = (
                maximum_bytes
                - total
            );

            if (
                remaining
                < (
                    (u64) sizeof(buffer)
                )
            ) {
                requested = (
                    (usize) remaining
                    + 1
                );
            }
        }

        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) buffer,
            requested
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (
                    -amount
                )
            );

            return 0;
        }

        if (amount == 0) {
            unsigned char digest[32];

            tf_sha256_final(
                &context,
                digest
            );

            tf_sha256_hex(
                digest,
                output
            );

            *bytes_read = total;

            return 1;
        }

        if (
            total > maximum_bytes
            || (
                (u64) amount
                > (
                    maximum_bytes
                    - total
                )
            )
        ) {
            *oversized = 1;

            /*
             * We intentionally do not claim a SHA-256 for a source
             * that exceeded the bounded validation window.
             */
            *bytes_read = (
                maximum_bytes
                + 1ULL
            );

            output[0] = '\0';

            return 2;
        }

        tf_sha256_update(
            &context,
            buffer,
            (usize) amount
        );

        total += (
            (u64) amount
        );
    }
}


static void tf_run_requested_read_probe(
    struct tf_runtime_partition_inventory *inventory,
    struct tf_recovery_read_probe_result *result
) {
    memset(
        result,
        0,
        sizeof(*result)
    );

    char request[256];

    long amount = tf_read_path(
        TREEFORGE_RECOVERY_READ_PROBE_REQUEST_PATH,
        request,
        sizeof(request)
    );

    if (amount <= 0) {
        return;
    }

    result->requested = 1;

    /*
     * Consume the control file before touching the block device so a
     * later recovery invocation cannot accidentally repeat the probe.
     */
    long unlink_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_READ_PROBE_REQUEST_PATH,
        0
    );

    if (unlink_result < 0) {
        result->error_stage = 1;
        result->error_errno = (
            (u64) (
                -unlink_result
            )
        );
        return;
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        !tf_parse_read_probe_name(
            request,
            (usize) amount,
            result->requested_canonical_name,
            sizeof(
                result->requested_canonical_name
            )
        )
    ) {
        result->error_stage = 1;
        return;
    }

    if (
        !inventory
        || !inventory->active_slot_resolved
    ) {
        result->error_stage = 2;
        return;
    }

    struct tf_runtime_partition *target = 0;
    int target_count = 0;

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        struct tf_runtime_partition *record = (
            &inventory->partitions[index]
        );

        if (
            !record->read_probe_eligible
            || !record->slot_pair
            || record->active
            || !tf_string_equal(
                record->canonical_name,
                result->requested_canonical_name
            )
        ) {
            continue;
        }

        target = record;
        target_count++;
    }

    if (
        target_count != 1
        || !target
    ) {
        result->error_stage = 2;
        return;
    }

    const struct tf_canonical_partition_expectation
        *expectation = (
            tf_find_canonical_expectation(
                target->canonical_name
            )
        );

    if (
        !expectation
        || !expectation->content_sha256_resolved
        || !expectation->canonical_content_sha256
        || !expectation->canonical_content_sha256[0]
    ) {
        result->error_stage = 2;
        return;
    }

    result->target_resolved = 1;

    tf_copy_string(
        result->target_partition_name,
        sizeof(
            result->target_partition_name
        ),
        target->partition_name
    );

    result->target_slot = (
        target->slot
    );

    result->target_active = (
        target->active
    );

    result->target_major = (
        target->major_number
    );

    result->target_minor = (
        target->minor_number
    );

    result->bytes_requested = (
        target->canonical_image_size_bytes
    );

    tf_copy_string(
        result->expected_sha256,
        sizeof(
            result->expected_sha256
        ),
        expectation->canonical_content_sha256
    );

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            target->major_number,
            target->minor_number,
            &encoded_device
        )
    ) {
        result->error_stage = 3;
        return;
    }

    /*
     * /dev is Android's already-established first-stage tmpfs.
     * TreeForge owns exactly this temporary node name.
     */
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_PROBE_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_PROBE_NODE_PATH,
        S_IFBLK | 0600,
        (long) encoded_device
    );

    if (node_result < 0) {
        result->error_stage = 4;
        result->error_errno = (
            (u64) (
                -node_result
            )
        );
        return;
    }

    result->node_created = 1;

    long fd = tf_open(
        TREEFORGE_RECOVERY_PROBE_NODE_PATH,
        O_RDONLY
    );

    if (fd < 0) {
        result->error_stage = 5;
        result->error_errno = (
            (u64) (
                -fd
            )
        );

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_PROBE_NODE_PATH,
            0
        );

        return;
    }

    result->open_succeeded = 1;

    u64 read_errno = 0;

    if (
        tf_hash_fd_exact(
            fd,
            result->bytes_requested,
            result->actual_sha256,
            &result->bytes_read,
            &read_errno
        )
    ) {
        result->hash_succeeded = 1;

        result->hash_match = (
            tf_string_equal(
                result->actual_sha256,
                result->expected_sha256
            )
        );
    } else {
        result->error_stage = 6;
        result->error_errno = (
            read_errno
        );
    }

    tf_close(
        fd
    );

    long cleanup_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_PROBE_NODE_PATH,
        0
    );

    if (
        cleanup_result < 0
        && result->error_stage == 0
    ) {
        result->error_stage = 7;
        result->error_errno = (
            (u64) (
                -cleanup_result
            )
        );
    }
}



static void tf_run_requested_flash_plan(
    struct tf_runtime_partition_inventory *inventory,
    struct tf_recovery_flash_plan_result *result
) {
    memset(
        result,
        0,
        sizeof(*result)
    );

    /*
     * These remain hard-zero regardless of every other result.
     */
    result->activation_eligible = 0;
    result->authorized = 0;
    result->written = 0;

    char request[256];

    long amount = tf_read_path(
        TREEFORGE_RECOVERY_FLASH_PLAN_REQUEST_PATH,
        request,
        sizeof(request)
    );

    if (amount <= 0) {
        return;
    }

    result->requested = 1;

    /*
     * Planning is one-shot. Consume the request before inspecting the
     * staged source so a failed source validation cannot silently
     * repeat on a later recovery invocation.
     */
    long unlink_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_FLASH_PLAN_REQUEST_PATH,
        0
    );

    if (unlink_result < 0) {
        result->error_stage = 1;
        result->error_errno = (
            (u64) (
                -unlink_result
            )
        );
        return;
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        !tf_parse_read_probe_name(
            request,
            (usize) amount,
            result->requested_canonical_name,
            sizeof(
                result->requested_canonical_name
            )
        )
    ) {
        result->error_stage = 1;
        return;
    }

    if (
        !inventory
        || !inventory->active_slot_resolved
    ) {
        result->error_stage = 2;
        return;
    }

    struct tf_runtime_partition *target = 0;
    int target_count = 0;

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        struct tf_runtime_partition *record = (
            &inventory->partitions[index]
        );

        if (
            !record->read_probe_eligible
            || !record->slot_pair
            || record->active
            || !tf_string_equal(
                record->canonical_name,
                result->requested_canonical_name
            )
        ) {
            continue;
        }

        target = record;
        target_count++;
    }

    if (
        target_count != 1
        || !target
    ) {
        result->error_stage = 2;
        return;
    }

    const struct tf_canonical_partition_expectation
        *expectation = (
            tf_find_canonical_expectation(
                target->canonical_name
            )
        );

    if (
        !expectation
        || !expectation->image_size_resolved
        || target->canonical_image_size_bytes == 0
    ) {
        result->error_stage = 2;
        return;
    }

    result->target_resolved = 1;

    tf_copy_string(
        result->target_partition_name,
        sizeof(
            result->target_partition_name
        ),
        target->partition_name
    );

    result->target_slot = (
        target->slot
    );

    result->target_active = (
        target->active
    );

    result->target_major = (
        target->major_number
    );

    result->target_minor = (
        target->minor_number
    );

    result->target_capacity_bytes = (
        target->capacity_bytes
    );

    result->canonical_image_size_bytes = (
        target->canonical_image_size_bytes
    );

    if (
        expectation->content_sha256_resolved
        && expectation->canonical_content_sha256
        && expectation->canonical_content_sha256[0]
    ) {
        tf_copy_string(
            result->canonical_sha256,
            sizeof(
                result->canonical_sha256
            ),
            expectation->canonical_content_sha256
        );
    }

    /*
     * The runtime target is acceptable for planning only. This does
     * not change record->writable and does not authorize a future
     * destructive operation.
     */
    result->target_ready = (
        target->read_probe_eligible
        && target->slot_pair
        && !target->active
        && target->canonical_capacity_sufficient
        && target->writable == 0
    );

    u64 manifest_bytes = 0;
    char manifest_sha256[65];

    int manifest_status = (
        tf_recovery_load_stream_manifest(
            &manifest_bytes,
            manifest_sha256
        )
    );

    if (manifest_status < 0) {
        /*
         * A present but malformed streaming manifest is never allowed
         * to silently fall through to another source identity.
         */
        result->error_stage = 3;
        result->error_errno = 0;
        return;
    }

    if (manifest_status == 1) {
        result->source_streaming = 1;
        result->source_manifest_valid = 1;
        result->source_stream_ready = (
            tf_recovery_stream_fifo_ready
        );

        result->source_bytes = manifest_bytes;

        tf_copy_string(
            result->source_sha256,
            sizeof(result->source_sha256),
            manifest_sha256
        );

        result->source_fits_target = (
            result->source_bytes
            <= target->capacity_bytes
        );

        result->source_size_matches_canonical = (
            result->source_bytes
            == target->canonical_image_size_bytes
        );

        if (
            result->canonical_sha256[0]
            && result->source_sha256[0]
        ) {
            result->source_matches_canonical = (
                tf_string_equal(
                    result->source_sha256,
                    result->canonical_sha256
                )
            );
        }

        result->plan_ready = (
            result->target_ready
            && result->source_manifest_valid
            && result->source_stream_ready
            && result->source_fits_target
            && result->source_size_matches_canonical
        );

        if (
            !result->source_stream_ready
            && result->error_stage == 0
        ) {
            result->error_stage = 5;
            result->error_errno = 0;
        }

        /*
         * The manifest supplies the expected source identity.
         * source_hash_succeeded remains false until the actual streamed
         * bytes have been consumed and hashed by the writer.
         */
        return;
    }

    /*
     * No stream manifest exists: preserve the already hardware-accepted
     * regular-file staging path exactly.
     */
    long source = tf_open(
        TREEFORGE_RECOVERY_FLASH_SOURCE_PATH,
        O_RDONLY
    );

    if (source < 0) {
        result->error_stage = 3;
        result->error_errno = (
            (u64) (
                -source
            )
        );
        return;
    }

    result->source_open_succeeded = 1;

    u64 source_errno = 0;

    int hash_status = (
        tf_hash_fd_to_eof_bounded(
            source,
            target->capacity_bytes,
            result->source_sha256,
            &result->source_bytes,
            &result->source_oversized,
            &source_errno
        )
    );

    tf_close(
        source
    );

    if (hash_status == 0) {
        result->error_stage = 4;
        result->error_errno = (
            source_errno
        );
        return;
    }

    if (hash_status == 2) {
        result->source_fits_target = 0;
        result->source_hash_succeeded = 0;
        result->plan_ready = 0;
        return;
    }

    result->source_hash_succeeded = 1;

    result->source_fits_target = (
        result->source_bytes
        <= target->capacity_bytes
    );

    result->source_size_matches_canonical = (
        result->source_bytes
        == target->canonical_image_size_bytes
    );

    if (
        result->canonical_sha256[0]
        && result->source_sha256[0]
    ) {
        result->source_matches_canonical = (
            tf_string_equal(
                result->source_sha256,
                result->canonical_sha256
            )
        );
    }

    result->plan_ready = (
        result->target_ready
        && result->source_hash_succeeded
        && !result->source_oversized
        && result->source_fits_target
        && result->source_size_matches_canonical
    );

    /*
     * Even a perfect plan is not authorization.
     *
     * A later explicit authorization contract must bind at least the
     * canonical target identity and this exact source SHA-256 before a
     * write-capable block descriptor can ever exist.
     */
    result->activation_eligible = 0;
    result->authorized = 0;
    result->written = 0;
}


/*
 * Write exactly one already-authorized staged image.
 *
 * Safety invariants:
 *
 *   - authorization must have revalidated the complete plan;
 *   - target must still be the inactive member of an A/B pair;
 *   - source length must equal the canonical image length;
 *   - source SHA-256 is revalidated immediately before opening a
 *     writable block descriptor;
 *   - only the exact planned major/minor device is materialized;
 *   - no slot activation is performed;
 *   - written=1 is claimed only after read-back SHA-256 verification.
 */
static int tf_recovery_write_authorized_file_plan(
    struct tf_recovery_flash_plan_result *result
) {
    if (!result) {
        return 0;
    }

    result->source_revalidated = 0;
    result->streamed_hash_succeeded = 0;
    result->streamed_sha256[0] = '\0';
    result->target_node_created = 0;
    result->target_open_succeeded = 0;
    result->bytes_written = 0;
    result->write_synced = 0;
    result->verification_open_succeeded = 0;
    result->verification_hash_succeeded = 0;
    result->verification_match = 0;
    result->verified_sha256[0] = '\0';
    result->written = 0;

    /*
     * activation_eligible remains hard-zero. A single partition write
     * does not prove that the complete inactive boot chain is coherent.
     */
    result->activation_eligible = 0;

    if (
        !result->authorization_requested
        || !result->authorization_match
        || !result->authorized
        || !result->plan_ready
        || !result->target_resolved
        || result->target_active
        || (
            result->target_slot != 'a'
            && result->target_slot != 'b'
        )
        || !result->source_hash_succeeded
        || !result->source_sha256[0]
        || result->source_bytes == 0
        || result->source_bytes
            != result->canonical_image_size_bytes
        || !result->source_fits_target
        || result->source_bytes
            > result->target_capacity_bytes
    ) {
        result->error_stage = 10;
        result->error_errno = 0;
        return 0;
    }

    /*
     * The active slot itself must still disagree with the authorized
     * target immediately before destructive access.
     */
    char active_slot = tf_resolve_active_slot();

    if (
        active_slot != 'a'
        && active_slot != 'b'
    ) {
        result->error_stage = 11;
        result->error_errno = 0;
        return 0;
    }

    if (active_slot == result->target_slot) {
        result->error_stage = 12;
        result->error_errno = 0;
        return 0;
    }

    long source = tf_open(
        TREEFORGE_RECOVERY_FLASH_SOURCE_PATH,
        O_RDONLY
    );

    if (source < 0) {
        result->error_stage = 13;
        result->error_errno = (u64) (-source);
        return 0;
    }

    /*
     * Revalidate the staged file itself after authorization.
     * This is the last operation before a writable target descriptor
     * can exist.
     */
    char revalidated_sha256[65];
    u64 revalidated_bytes = 0;
    int revalidated_oversized = 0;
    u64 source_errno = 0;

    int revalidated = tf_hash_fd_to_eof_bounded(
        source,
        result->source_bytes,
        revalidated_sha256,
        &revalidated_bytes,
        &revalidated_oversized,
        &source_errno
    );

    if (
        revalidated != 1
        || revalidated_oversized
        || revalidated_bytes != result->source_bytes
        || !tf_string_equal(
            revalidated_sha256,
            result->source_sha256
        )
    ) {
        tf_close(source);

        result->error_stage = 14;
        result->error_errno = source_errno;
        return 0;
    }

    result->source_revalidated = 1;

    long seek_result = tf_syscall3(
        SYS_LSEEK,
        source,
        0,
        SEEK_SET
    );

    if (seek_result != 0) {
        tf_close(source);

        result->error_stage = 15;
        result->error_errno = (
            seek_result < 0
            ? (u64) (-seek_result)
            : 0
        );

        return 0;
    }

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            result->target_major,
            result->target_minor,
            &encoded_device
        )
    ) {
        tf_close(source);

        result->error_stage = 16;
        result->error_errno = 0;
        return 0;
    }

    /*
     * TreeForge owns exactly this transient block node.
     */
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        S_IFBLK | 0600,
        (long) encoded_device
    );

    if (node_result < 0) {
        tf_close(source);

        result->error_stage = 17;
        result->error_errno = (u64) (-node_result);
        return 0;
    }

    result->target_node_created = 1;

    long target = tf_open(
        TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        O_WRONLY
    );

    if (target < 0) {
        tf_close(source);

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_FLASH_NODE_PATH,
            0
        );

        result->target_node_created = 0;
        result->error_stage = 18;
        result->error_errno = (u64) (-target);
        return 0;
    }

    result->target_open_succeeded = 1;

    unsigned char buffer[4096];

    struct tf_sha256_context streamed_context;

    tf_sha256_init(
        &streamed_context
    );

    u64 remaining = result->source_bytes;
    int write_failed = 0;

    while (remaining > 0) {
        usize requested = (
            remaining < (u64) sizeof(buffer)
            ? (usize) remaining
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            source,
            (long) buffer,
            requested
        );

        if (amount <= 0) {
            result->error_stage = 19;
            result->error_errno = (
                amount < 0
                ? (u64) (-amount)
                : 0
            );

            write_failed = 1;
            break;
        }

        usize offset = 0;

        while (offset < (usize) amount) {
            long write_result = tf_syscall3(
                SYS_WRITE,
                target,
                (long) (buffer + offset),
                (long) (
                    (usize) amount - offset
                )
            );

            if (write_result <= 0) {
                result->error_stage = 20;
                result->error_errno = (
                    write_result < 0
                    ? (u64) (-write_result)
                    : 0
                );

                write_failed = 1;
                break;
            }

            offset += (usize) write_result;
            result->bytes_written += (
                (u64) write_result
            );
        }

        if (write_failed) {
            break;
        }

        tf_sha256_update(
            &streamed_context,
            buffer,
            (usize) amount
        );

        remaining -= (u64) amount;
    }

    /*
     * Flush even a failed partial write so the resulting hardware state
     * is determinate and the report does not describe dirty page-cache
     * state as though nothing reached the device.
     */
    long fsync_result = tf_syscall1(
        SYS_FSYNC,
        target
    );

    if (fsync_result == 0) {
        result->write_synced = 1;
    } else if (!write_failed) {
        result->error_stage = 21;
        result->error_errno = (u64) (-fsync_result);
        write_failed = 1;
    }

    tf_close(target);
    tf_close(source);

    target = -1;
    source = -1;

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        write_failed
        || result->bytes_written
            != result->source_bytes
    ) {
        if (
            !write_failed
            && result->error_stage == 0
        ) {
            result->error_stage = 22;
            result->error_errno = 0;
        }

        goto cleanup;
    }

    /*
     * Verify that the exact bytes consumed for the write still hash to
     * the source identity that authorization approved.
     */
    unsigned char streamed_digest[32];
    char streamed_sha256[65];

    tf_sha256_final(
        &streamed_context,
        streamed_digest
    );

    tf_sha256_hex(
        streamed_digest,
        streamed_sha256
    );

    if (
        !tf_string_equal(
            streamed_sha256,
            result->source_sha256
        )
    ) {
        result->error_stage = 23;
        result->error_errno = 0;
        goto cleanup;
    }

    /*
     * Reopen the block device read-only rather than verifying through
     * the writable descriptor.
     */
    long verify = tf_open(
        TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        O_RDONLY
    );

    if (verify < 0) {
        result->error_stage = 24;
        result->error_errno = (u64) (-verify);
        goto cleanup;
    }

    result->verification_open_succeeded = 1;

    u64 verified_bytes = 0;
    u64 verify_errno = 0;

    if (
        !tf_hash_fd_exact(
            verify,
            result->source_bytes,
            result->verified_sha256,
            &verified_bytes,
            &verify_errno
        )
    ) {
        tf_close(verify);

        result->error_stage = 25;
        result->error_errno = verify_errno;
        goto cleanup;
    }

    tf_close(verify);

    result->verification_hash_succeeded = 1;

    result->verification_match = (
        verified_bytes == result->source_bytes
        && tf_string_equal(
            result->verified_sha256,
            result->source_sha256
        )
    );

    if (!result->verification_match) {
        result->error_stage = 26;
        result->error_errno = 0;
        goto cleanup;
    }

    /*
     * This is the only point at which TreeForge calls the operation
     * written/accepted.
     */
    result->written = 1;
    result->error_stage = 0;
    result->error_errno = 0;

cleanup:
    {
        long cleanup_result = tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_FLASH_NODE_PATH,
            0
        );

        if (
            cleanup_result == 0
            || cleanup_result == -2
        ) {
            result->target_node_created = 0;
        } else if (result->error_stage == 0) {
            result->error_stage = 27;
            result->error_errno = (
                (u64) (-cleanup_result)
            );
        }
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    return result->written;
}


/*
 * Write one manifest-authorized source stream.
 *
 * Unlike regular-file staging there is deliberately no full-size
 * persistent copy of the image. The validated manifest is the expected
 * source identity. The exact FIFO bytes are hashed while they are
 * written to the already-authorized inactive target.
 *
 * written=1 still requires all three identities to agree:
 *
 *   authorized manifest SHA-256
 *          ==
 *   exact streamed-byte SHA-256
 *          ==
 *   reopened target read-back SHA-256
 *
 * Slot activation remains impossible here.
 */
static int tf_recovery_write_authorized_stream_plan(
    struct tf_recovery_flash_plan_result *result
) {
    if (!result) {
        return 0;
    }

    result->source_open_succeeded = 0;
    result->source_hash_succeeded = 0;
    result->source_oversized = 0;
    result->source_revalidated = 0;
    result->streamed_hash_succeeded = 0;
    result->streamed_sha256[0] = '\0';
    result->target_node_created = 0;
    result->target_open_succeeded = 0;
    result->bytes_written = 0;
    result->write_synced = 0;
    result->verification_open_succeeded = 0;
    result->verification_hash_succeeded = 0;
    result->verification_match = 0;
    result->verified_sha256[0] = '\0';
    result->written = 0;
    result->error_stage = 0;
    result->error_errno = 0;

    result->activation_eligible = 0;

    if (
        !result->source_streaming
        || !result->source_manifest_valid
        || !result->source_stream_ready
        || !result->authorization_requested
        || !result->authorization_match
        || !result->authorized
        || !result->plan_ready
        || !result->target_resolved
        || result->target_active
        || (
            result->target_slot != 'a'
            && result->target_slot != 'b'
        )
        || !result->source_sha256[0]
        || result->source_bytes == 0
        || result->source_bytes
            != result->canonical_image_size_bytes
        || !result->source_fits_target
        || result->source_bytes
            > result->target_capacity_bytes
    ) {
        result->error_stage = 30;
        return 0;
    }

    /*
     * Re-check the active slot before waiting for a host stream.
     */
    char active_slot = tf_resolve_active_slot();

    if (
        active_slot != 'a'
        && active_slot != 'b'
    ) {
        result->error_stage = 31;
        return 0;
    }

    if (active_slot == result->target_slot) {
        result->error_stage = 32;
        return 0;
    }

    /*
     * Blocking FIFO open is intentional.
     *
     * The Recovery UI has already displayed the waiting-for-ADB screen.
     * adbd's sync service opens the same existing FIFO O_WRONLY and the
     * two endpoints rendezvous here.
     */
    long source = tf_open(
        TREEFORGE_RECOVERY_STREAM_FIFO_PATH,
        O_RDONLY
    );

    if (source < 0) {
        result->error_stage = 33;
        result->error_errno = (u64) (-source);
        return 0;
    }

    result->source_open_succeeded = 1;

    /*
     * The FIFO rendezvous may wait an arbitrary amount of time.
     * Re-check slot identity immediately before creating a writable
     * target descriptor.
     */
    active_slot = tf_resolve_active_slot();

    if (
        active_slot != 'a'
        && active_slot != 'b'
    ) {
        tf_close(source);

        result->error_stage = 34;
        return 0;
    }

    if (active_slot == result->target_slot) {
        tf_close(source);

        result->error_stage = 35;
        return 0;
    }

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            result->target_major,
            result->target_minor,
            &encoded_device
        )
    ) {
        tf_close(source);

        result->error_stage = 36;
        return 0;
    }

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        S_IFBLK | 0600,
        (long) encoded_device
    );

    if (node_result < 0) {
        tf_close(source);

        result->error_stage = 37;
        result->error_errno = (u64) (-node_result);
        return 0;
    }

    result->target_node_created = 1;

    long target = tf_open(
        TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        O_WRONLY
    );

    if (target < 0) {
        tf_close(source);

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_FLASH_NODE_PATH,
            0
        );

        result->target_node_created = 0;
        result->error_stage = 38;
        result->error_errno = (u64) (-target);
        return 0;
    }

    result->target_open_succeeded = 1;

    unsigned char buffer[4096];

    struct tf_sha256_context streamed_context;

    tf_sha256_init(
        &streamed_context
    );

    u64 remaining = result->source_bytes;
    int write_failed = 0;

    while (remaining > 0) {
        usize requested = (
            remaining < (u64) sizeof(buffer)
            ? (usize) remaining
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            source,
            (long) buffer,
            requested
        );

        if (amount <= 0) {
            result->error_stage = 39;
            result->error_errno = (
                amount < 0
                ? (u64) (-amount)
                : 0
            );

            write_failed = 1;
            break;
        }

        usize offset = 0;

        while (offset < (usize) amount) {
            long write_result = tf_syscall3(
                SYS_WRITE,
                target,
                (long) (
                    buffer + offset
                ),
                (long) (
                    (usize) amount - offset
                )
            );

            if (write_result <= 0) {
                result->error_stage = 40;
                result->error_errno = (
                    write_result < 0
                    ? (u64) (-write_result)
                    : 0
                );

                write_failed = 1;
                break;
            }

            offset += (
                (usize) write_result
            );

            result->bytes_written += (
                (u64) write_result
            );
        }

        if (write_failed) {
            break;
        }

        tf_sha256_update(
            &streamed_context,
            buffer,
            (usize) amount
        );

        remaining -= (
            (u64) amount
        );
    }

    /*
     * Exact-size framing matters for a FIFO. Once the declared byte
     * count has been consumed, require EOF. One additional byte means
     * the host sent an oversized source.
     */
    if (!write_failed) {
        unsigned char extra_byte = 0;

        long extra = tf_syscall3(
            SYS_READ,
            source,
            (long) &extra_byte,
            1
        );

        if (extra < 0) {
            result->error_stage = 41;
            result->error_errno = (
                (u64) (-extra)
            );
            write_failed = 1;
        } else if (extra > 0) {
            result->source_oversized = 1;
            result->error_stage = 42;
            result->error_errno = 0;
            write_failed = 1;
        }
    }

    if (!write_failed) {
        unsigned char streamed_digest[32];

        tf_sha256_final(
            &streamed_context,
            streamed_digest
        );

        tf_sha256_hex(
            streamed_digest,
            result->streamed_sha256
        );

        result->streamed_hash_succeeded = 1;
        result->source_hash_succeeded = 1;

        result->source_revalidated = (
            tf_string_equal(
                result->streamed_sha256,
                result->source_sha256
            )
        );

        if (!result->source_revalidated) {
            result->error_stage = 43;
            result->error_errno = 0;
            write_failed = 1;
        }
    }

    /*
     * As with the accepted file writer, flush even failed/partial
     * writes so the resulting inactive-slot state is determinate.
     */
    long fsync_result = tf_syscall1(
        SYS_FSYNC,
        target
    );

    if (fsync_result == 0) {
        result->write_synced = 1;
    } else if (!write_failed) {
        result->error_stage = 44;
        result->error_errno = (
            (u64) (-fsync_result)
        );
        write_failed = 1;
    }

    tf_close(target);
    tf_close(source);

    target = -1;
    source = -1;

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        write_failed
        || result->bytes_written
            != result->source_bytes
        || !result->source_revalidated
    ) {
        if (
            !write_failed
            && result->error_stage == 0
        ) {
            result->error_stage = 45;
        }

        goto stream_cleanup;
    }

    /*
     * Verify through a new read-only descriptor.
     */
    long verify = tf_open(
        TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        O_RDONLY
    );

    if (verify < 0) {
        result->error_stage = 46;
        result->error_errno = (u64) (-verify);
        goto stream_cleanup;
    }

    result->verification_open_succeeded = 1;

    u64 verified_bytes = 0;
    u64 verify_errno = 0;

    if (
        !tf_hash_fd_exact(
            verify,
            result->source_bytes,
            result->verified_sha256,
            &verified_bytes,
            &verify_errno
        )
    ) {
        tf_close(verify);

        result->error_stage = 47;
        result->error_errno = verify_errno;
        goto stream_cleanup;
    }

    tf_close(verify);

    result->verification_hash_succeeded = 1;

    result->verification_match = (
        verified_bytes == result->source_bytes
        && tf_string_equal(
            result->verified_sha256,
            result->source_sha256
        )
        && tf_string_equal(
            result->verified_sha256,
            result->streamed_sha256
        )
    );

    if (!result->verification_match) {
        result->error_stage = 48;
        goto stream_cleanup;
    }

    result->written = 1;
    result->error_stage = 0;
    result->error_errno = 0;

stream_cleanup:
    {
        long cleanup_result = tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_FLASH_NODE_PATH,
            0
        );

        if (
            cleanup_result == 0
            || cleanup_result == -2
        ) {
            result->target_node_created = 0;
        } else if (result->error_stage == 0) {
            result->error_stage = 49;
            result->error_errno = (
                (u64) (-cleanup_result)
            );
        }
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    return result->written;
}


/*
 * Preserve one public writer entry point.
 *
 * Persistent regular-file staging is consumed only after the writer has
 * reached final read-back acceptance. Cancelled, rejected, failed, and
 * unverified plans deliberately retain the staged file for retry/debugging.
 *
 * Streaming has no persistent full-image source and keeps its existing
 * independent lifecycle.
 */
static int tf_recovery_write_authorized_plan(
    struct tf_recovery_flash_plan_result *result
) {
    if (
        result
        && result->source_streaming
    ) {
        return (
            tf_recovery_write_authorized_stream_plan(
                result
            )
        );
    }

    int written = (
        tf_recovery_write_authorized_file_plan(
            result
        )
    );

    if (
        !written
        || !result
        || !result->written
        || !result->verification_match
    ) {
        return written;
    }

    /*
     * The regular staged image has now been completely consumed.
     *
     * Do not remove it earlier: staging on /metadata is intentionally
     * persistent across reboot so an image may be prepared before entering
     * Recovery.
     */
    long cleanup_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_FLASH_SOURCE_PATH,
        0
    );

    if (
        cleanup_result != 0
        && cleanup_result != -2
    ) {
        /*
         * The partition write remains truthfully verified. Report the
         * post-write source-cleanup failure without changing written=1.
         */
        if (result->error_stage == 0) {
            result->error_stage = 50;
            result->error_errno = (
                (u64) (-cleanup_result)
            );
        }
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    return written;
}





static u16 tf_lp_load_le16(
    const unsigned char *value
) {
    return (
        (u16) value[0]
        | (
            (u16) value[1]
            << 8
        )
    );
}


static u32 tf_lp_load_le32(
    const unsigned char *value
) {
    return (
        (u32) value[0]
        | (
            (u32) value[1]
            << 8
        )
        | (
            (u32) value[2]
            << 16
        )
        | (
            (u32) value[3]
            << 24
        )
    );
}


static u64 tf_lp_load_le64(
    const unsigned char *value
) {
    u64 result = 0;

    for (
        int index = 7;
        index >= 0;
        index--
    ) {
        result = (
            result << 8
        ) | (
            (u64) value[index]
        );
    }

    return result;
}


static int tf_lp_read_exact_at(
    long fd,
    u64 offset,
    void *buffer,
    usize length,
    u64 *error_errno
) {
    if (
        fd < 0
        || !buffer
        || !error_errno
        || offset > 0x7fffffffffffffffULL
    ) {
        return 0;
    }

    *error_errno = 0;

    long seek_result = tf_syscall3(
        SYS_LSEEK,
        fd,
        (long) offset,
        SEEK_SET
    );

    if (seek_result < 0) {
        *error_errno = (
            (u64) (-seek_result)
        );

        return 0;
    }

    if (
        (u64) seek_result
        != offset
    ) {
        return 0;
    }

    usize completed = 0;

    while (completed < length) {
        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) (
                (unsigned char *) buffer
                + completed
            ),
            (long) (
                length - completed
            )
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount == 0) {
            return 0;
        }

        completed += (
            (usize) amount
        );
    }

    return 1;
}


static void tf_lp_hash_memory(
    const unsigned char *data,
    usize length,
    unsigned char digest[32]
) {
    struct tf_sha256_context context;

    tf_sha256_init(
        &context
    );

    tf_sha256_update(
        &context,
        data,
        length
    );

    tf_sha256_final(
        &context,
        digest
    );
}


static int tf_lp_hash_region(
    long fd,
    u64 offset,
    u64 length,
    unsigned char digest[32],
    u64 *error_errno
) {
    if (
        fd < 0
        || !digest
        || !error_errno
        || offset > 0x7fffffffffffffffULL
    ) {
        return 0;
    }

    *error_errno = 0;

    long seek_result = tf_syscall3(
        SYS_LSEEK,
        fd,
        (long) offset,
        SEEK_SET
    );

    if (seek_result < 0) {
        *error_errno = (
            (u64) (-seek_result)
        );

        return 0;
    }

    if (
        (u64) seek_result
        != offset
    ) {
        return 0;
    }

    struct tf_sha256_context context;

    tf_sha256_init(
        &context
    );

    unsigned char buffer[4096];

    u64 remaining = length;

    while (remaining > 0) {
        usize requested = (
            remaining < (u64) sizeof(buffer)
            ? (usize) remaining
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) buffer,
            requested
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount == 0) {
            return 0;
        }

        tf_sha256_update(
            &context,
            buffer,
            (usize) amount
        );

        remaining -= (
            (u64) amount
        );
    }

    tf_sha256_final(
        &context,
        digest
    );

    return 1;
}


static int tf_lp_copy_fixed_name(
    const unsigned char *source,
    usize source_capacity,
    char *destination,
    usize destination_capacity
) {
    if (
        !source
        || !destination
        || destination_capacity == 0
    ) {
        return 0;
    }

    usize length = 0;

    while (
        length < source_capacity
        && source[length] != 0
    ) {
        length++;
    }

    if (
        length == 0
        || length + 1 > destination_capacity
    ) {
        destination[0] = '\0';
        return 0;
    }

    for (
        usize index = 0;
        index < length;
        index++
    ) {
        destination[index] = (
            (char) source[index]
        );
    }

    destination[length] = '\0';

    return 1;
}


static int tf_lp_append_slot_suffix(
    char *name,
    usize capacity,
    u32 metadata_slot
) {
    if (
        !name
        || capacity == 0
        || metadata_slot > 1U
    ) {
        return 0;
    }

    usize length = tf_strlen(
        name
    );

    if (
        length + 3 > capacity
    ) {
        return 0;
    }

    name[length] = '_';
    name[length + 1] = (
        (char) (
            'a'
            + metadata_slot
        )
    );
    name[length + 2] = '\0';

    return 1;
}


static int tf_recovery_read_prefix(
    long fd,
    unsigned char *buffer,
    usize capacity,
    usize *amount_read,
    u64 *error_errno
) {
    if (
        fd < 0
        || !buffer
        || !amount_read
        || !error_errno
    ) {
        return 0;
    }

    *amount_read = 0;
    *error_errno = 0;

    while (*amount_read < capacity) {
        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) (
                buffer
                + *amount_read
            ),
            capacity - *amount_read
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount == 0) {
            break;
        }

        *amount_read += (
            (usize) amount
        );
    }

    return 1;
}


static int tf_recovery_read_exact_discard(
    long fd,
    u64 bytes,
    u64 *error_errno
) {
    if (
        fd < 0
        || !error_errno
    ) {
        return 0;
    }

    unsigned char buffer[4096];

    while (bytes > 0) {
        usize requested = (
            bytes < (u64) sizeof(buffer)
            ? (usize) bytes
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) buffer,
            requested
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount == 0) {
            return 0;
        }

        bytes -= (
            (u64) amount
        );
    }

    return 1;
}


static int tf_recovery_add_u64(
    u64 *value,
    u64 add
) {
    if (!value) {
        return 0;
    }

    if (
        add
        > (
            0xffffffffffffffffULL
            - *value
        )
    ) {
        return 0;
    }

    *value += add;

    return 1;
}


static void tf_recovery_inspect_staged_image(
    struct tf_recovery_image_inspection *inspection
) {
    if (!inspection) {
        return;
    }

    memset(
        inspection,
        0,
        sizeof(*inspection)
    );

    long fd = tf_open(
        TREEFORGE_RECOVERY_FLASH_SOURCE_PATH,
        O_RDONLY
    );

    if (fd < 0) {
        inspection->error_stage = 1;
        inspection->error_errno = (
            (u64) (-fd)
        );

        return;
    }

    inspection->source_open_succeeded = 1;

    unsigned char header[
        TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    ];

    usize header_bytes = 0;
    u64 read_errno = 0;

    if (
        !tf_recovery_read_prefix(
            fd,
            header,
            sizeof(header),
            &header_bytes,
            &read_errno
        )
    ) {
        inspection->error_stage = 2;
        inspection->error_errno = read_errno;

        tf_close(fd);
        return;
    }

    if (header_bytes == 0) {
        inspection->error_stage = 3;

        tf_close(fd);
        return;
    }

    /*
     * A source is sparse only when the exact Android sparse magic is
     * present. Everything else is treated as a raw partition image.
     */
    int sparse = (
        header_bytes >= 4
        && tf_lp_load_le32(
            header
        )
            == TREEFORGE_RECOVERY_SPARSE_MAGIC
    );

    if (!sparse) {
        inspection->image_format = (
            TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        );

        inspection->source_bytes = (
            (u64) header_bytes
        );

        unsigned char buffer[4096];

        for (;;) {
            long amount = tf_syscall3(
                SYS_READ,
                fd,
                (long) buffer,
                sizeof(buffer)
            );

            if (amount < 0) {
                inspection->error_stage = 4;
                inspection->error_errno = (
                    (u64) (-amount)
                );

                tf_close(fd);
                return;
            }

            if (amount == 0) {
                break;
            }

            if (
                !tf_recovery_add_u64(
                    &inspection->source_bytes,
                    (u64) amount
                )
            ) {
                inspection->error_stage = 5;

                tf_close(fd);
                return;
            }
        }

        inspection->expanded_bytes = (
            inspection->source_bytes
        );

        inspection->inspection_complete = 1;

        tf_close(fd);
        return;
    }

    inspection->image_format = (
        TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
    );

    if (
        header_bytes
        != TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    ) {
        inspection->error_stage = 6;

        tf_close(fd);
        return;
    }

    u16 major_version = (
        tf_lp_load_le16(
            header + 4
        )
    );

    u16 file_header_size = (
        tf_lp_load_le16(
            header + 8
        )
    );

    u16 chunk_header_size = (
        tf_lp_load_le16(
            header + 10
        )
    );

    u32 block_size = (
        tf_lp_load_le32(
            header + 12
        )
    );

    u32 total_blocks = (
        tf_lp_load_le32(
            header + 16
        )
    );

    u32 total_chunks = (
        tf_lp_load_le32(
            header + 20
        )
    );

    if (
        major_version
            != TREEFORGE_RECOVERY_SPARSE_MAJOR_VERSION
        || file_header_size
            < TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
        || chunk_header_size
            < TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        || block_size == 0
        || (
            block_size
            % 4U
        ) != 0
    ) {
        inspection->error_stage = 7;

        tf_close(fd);
        return;
    }

    inspection->sparse_block_size = block_size;
    inspection->sparse_total_blocks = total_blocks;
    inspection->sparse_total_chunks = total_chunks;

    inspection->source_bytes = (
        TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    );

    inspection->expanded_bytes = (
        (u64) total_blocks
        * (u64) block_size
    );

    u64 file_header_extra = (
        (u64) file_header_size
        - TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    );

    if (file_header_extra > 0) {
        if (
            !tf_recovery_read_exact_discard(
                fd,
                file_header_extra,
                &read_errno
            )
        ) {
            inspection->error_stage = 8;
            inspection->error_errno = read_errno;

            tf_close(fd);
            return;
        }

        if (
            !tf_recovery_add_u64(
                &inspection->source_bytes,
                file_header_extra
            )
        ) {
            inspection->error_stage = 9;

            tf_close(fd);
            return;
        }
    }

    u64 output_blocks = 0;

    for (
        u32 chunk_index = 0;
        chunk_index < total_chunks;
        chunk_index++
    ) {
        unsigned char chunk_header[
            TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        ];

        usize chunk_header_bytes = 0;

        if (
            !tf_recovery_read_prefix(
                fd,
                chunk_header,
                sizeof(chunk_header),
                &chunk_header_bytes,
                &read_errno
            )
            || chunk_header_bytes
                != sizeof(chunk_header)
        ) {
            inspection->error_stage = 10;
            inspection->error_errno = read_errno;

            tf_close(fd);
            return;
        }

        if (
            !tf_recovery_add_u64(
                &inspection->source_bytes,
                sizeof(chunk_header)
            )
        ) {
            inspection->error_stage = 11;

            tf_close(fd);
            return;
        }

        u16 chunk_type = (
            tf_lp_load_le16(
                chunk_header
            )
        );

        u32 chunk_blocks = (
            tf_lp_load_le32(
                chunk_header + 4
            )
        );

        u32 total_size = (
            tf_lp_load_le32(
                chunk_header + 8
            )
        );

        if (
            total_size
            < chunk_header_size
        ) {
            inspection->error_stage = 12;

            tf_close(fd);
            return;
        }

        u64 chunk_header_extra = (
            (u64) chunk_header_size
            - TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        );

        if (chunk_header_extra > 0) {
            if (
                !tf_recovery_read_exact_discard(
                    fd,
                    chunk_header_extra,
                    &read_errno
                )
            ) {
                inspection->error_stage = 13;
                inspection->error_errno = read_errno;

                tf_close(fd);
                return;
            }

            if (
                !tf_recovery_add_u64(
                    &inspection->source_bytes,
                    chunk_header_extra
                )
            ) {
                inspection->error_stage = 14;

                tf_close(fd);
                return;
            }
        }

        u64 chunk_data_size = (
            (u64) total_size
            - (u64) chunk_header_size
        );

        int contributes_output_blocks = 0;

        if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_RAW
        ) {
            u64 expected = (
                (u64) chunk_blocks
                * (u64) block_size
            );

            if (chunk_data_size != expected) {
                inspection->error_stage = 15;

                tf_close(fd);
                return;
            }

            inspection->sparse_raw_chunks++;
            contributes_output_blocks = 1;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_FILL
        ) {
            if (chunk_data_size != 4ULL) {
                inspection->error_stage = 16;

                tf_close(fd);
                return;
            }

            inspection->sparse_fill_chunks++;
            contributes_output_blocks = 1;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_DONT_CARE
        ) {
            if (chunk_data_size != 0) {
                inspection->error_stage = 17;

                tf_close(fd);
                return;
            }

            inspection->sparse_dont_care_chunks++;
            contributes_output_blocks = 1;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_CRC32
        ) {
            if (chunk_data_size != 4ULL) {
                inspection->error_stage = 18;

                tf_close(fd);
                return;
            }

            inspection->sparse_crc32_chunks++;
        } else {
            inspection->error_stage = 19;

            tf_close(fd);
            return;
        }

        if (contributes_output_blocks) {
            if (
                (u64) chunk_blocks
                > (
                    0xffffffffffffffffULL
                    - output_blocks
                )
            ) {
                inspection->error_stage = 20;

                tf_close(fd);
                return;
            }

            output_blocks += (
                (u64) chunk_blocks
            );

            if (
                output_blocks
                > (u64) total_blocks
            ) {
                inspection->error_stage = 21;

                tf_close(fd);
                return;
            }
        }

        if (chunk_data_size > 0) {
            if (
                !tf_recovery_read_exact_discard(
                    fd,
                    chunk_data_size,
                    &read_errno
                )
            ) {
                inspection->error_stage = 22;
                inspection->error_errno = read_errno;

                tf_close(fd);
                return;
            }

            if (
                !tf_recovery_add_u64(
                    &inspection->source_bytes,
                    chunk_data_size
                )
            ) {
                inspection->error_stage = 23;

                tf_close(fd);
                return;
            }
        }
    }

    if (
        output_blocks
        != (u64) total_blocks
    ) {
        inspection->error_stage = 24;

        tf_close(fd);
        return;
    }

    /*
     * TreeForge accepts exactly one complete sparse image. Reject
     * trailing bytes instead of silently ignoring them.
     */
    unsigned char trailing = 0;

    long trailing_amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) &trailing,
        1
    );

    if (trailing_amount < 0) {
        inspection->error_stage = 25;
        inspection->error_errno = (
            (u64) (-trailing_amount)
        );

        tf_close(fd);
        return;
    }

    if (trailing_amount != 0) {
        inspection->error_stage = 26;

        tf_close(fd);
        return;
    }

    inspection->sparse_structure_valid = 1;
    inspection->inspection_complete = 1;

    tf_close(fd);
}


static const struct tf_recovery_flash_target *
tf_recovery_find_unified_flash_target(
    const char *partition_name
) {
    if (
        !partition_name
        || !partition_name[0]
    ) {
        return 0;
    }

    const struct tf_recovery_flash_target *match = 0;
    int matches = 0;

    for (
        int index = 0;
        index < tf_recovery_flash_targets.target_count;
        index++
    ) {
        const struct tf_recovery_flash_target *target = (
            &tf_recovery_flash_targets.targets[index]
        );

        if (
            !tf_string_equal(
                target->partition_name,
                partition_name
            )
        ) {
            continue;
        }

        match = target;
        matches++;
    }

    return (
        matches == 1
        ? match
        : 0
    );
}


static usize tf_append_text(
    char *destination,
    usize capacity,
    usize position,
    const char *source
);


static int tf_recovery_install_set_parse_name(
    const char *buffer,
    usize length,
    usize *position,
    const char *key,
    char *output,
    usize capacity
) {
    if (
        !buffer
        || !position
        || !key
        || !output
        || capacity == 0
    ) {
        return 0;
    }

    if (
        !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            key
        )
    ) {
        return 0;
    }

    usize output_position = 0;

    while (
        *position < length
        && buffer[*position] != '\n'
    ) {
        char value = buffer[*position];

        int valid = (
            (
                value >= 'a'
                && value <= 'z'
            )
            || (
                value >= '0'
                && value <= '9'
            )
            || value == '_'
        );

        if (
            !valid
            || output_position + 1 >= capacity
        ) {
            return 0;
        }

        output[output_position++] = value;
        (*position)++;
    }

    if (
        output_position == 0
        || *position >= length
        || buffer[*position] != '\n'
    ) {
        return 0;
    }

    output[output_position] = '\0';

    (*position)++;

    return 1;
}


static int tf_recovery_install_set_parse_format(
    const char *buffer,
    usize length,
    usize *position,
    int *format
) {
    if (
        !buffer
        || !position
        || !format
        || !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "format="
        )
    ) {
        return 0;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "raw\n"
        )
    ) {
        *format = (
            TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        );

        return 1;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "android-sparse\n"
        )
    ) {
        *format = (
            TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
        );

        return 1;
    }

    return 0;
}



static int tf_recovery_install_set_parse_named_sha256(
    const char *buffer,
    usize length,
    usize *position,
    const char *key,
    char sha256[65]
) {
    if (
        !buffer
        || !position
        || !key
        || !sha256
        || !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            key
        )
    ) {
        return 0;
    }

    for (
        int index = 0;
        index < 64;
        index++
    ) {
        if (*position >= length) {
            return 0;
        }

        char value = buffer[(*position)++];

        int valid = (
            (
                value >= '0'
                && value <= '9'
            )
            || (
                value >= 'a'
                && value <= 'f'
            )
            || (
                value >= 'A'
                && value <= 'F'
            )
        );

        if (!valid) {
            return 0;
        }

        if (
            value >= 'A'
            && value <= 'F'
        ) {
            value = (
                value
                - 'A'
                + 'a'
            );
        }

        sha256[index] = value;
    }

    sha256[64] = '\0';

    if (
        *position >= length
        || buffer[*position] != '\n'
    ) {
        return 0;
    }

    (*position)++;

    return 1;
}


static int tf_recovery_install_set_parse_method(
    const char *buffer,
    usize length,
    usize *position,
    int *method
) {
    if (
        !buffer
        || !position
        || !method
        || !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "method="
        )
    ) {
        return 0;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "physical-direct\n"
        )
    ) {
        *method = (
            TREEFORGE_RECOVERY_INSTALL_METHOD_PHYSICAL_DIRECT
        );

        return 1;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "logical-direct\n"
        )
    ) {
        *method = (
            TREEFORGE_RECOVERY_INSTALL_METHOD_LOGICAL_DIRECT
        );

        return 1;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "snapshot-cow\n"
        )
    ) {
        *method = (
            TREEFORGE_RECOVERY_INSTALL_METHOD_SNAPSHOT_COW
        );

        return 1;
    }

    return 0;
}


static int tf_recovery_install_set_parse_payload_kind(
    const char *buffer,
    usize length,
    usize *position,
    int *payload_kind
) {
    if (
        !buffer
        || !position
        || !payload_kind
        || !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "payload_kind="
        )
    ) {
        return 0;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "image\n"
        )
    ) {
        *payload_kind = (
            TREEFORGE_RECOVERY_PAYLOAD_KIND_IMAGE
        );

        return 1;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "cow\n"
        )
    ) {
        *payload_kind = (
            TREEFORGE_RECOVERY_PAYLOAD_KIND_COW
        );

        return 1;
    }

    return 0;
}


static int tf_recovery_install_set_parse_cow_compression(
    const char *buffer,
    usize length,
    usize *position,
    int *compression
) {
    if (
        !buffer
        || !position
        || !compression
        || !tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "cow_compression="
        )
    ) {
        return 0;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "none\n"
        )
    ) {
        *compression = (
            TREEFORGE_RECOVERY_COW_COMPRESSION_NONE
        );

        return 1;
    }

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            position,
            "lz4\n"
        )
    ) {
        *compression = (
            TREEFORGE_RECOVERY_COW_COMPRESSION_LZ4
        );

        return 1;
    }

    return 0;
}


static int tf_recovery_install_set_validate_v2_realization(
    const struct tf_recovery_install_set_image *image
) {
    if (
        !image
        || image->source_bytes == 0
        || image->expanded_bytes == 0
        || !image->sha256[0]
        || image->manifest_payload_bytes == 0
        || !image->manifest_payload_sha256[0]
    ) {
        return 0;
    }

    if (
        image->install_method
            == TREEFORGE_RECOVERY_INSTALL_METHOD_PHYSICAL_DIRECT
        || image->install_method
            == TREEFORGE_RECOVERY_INSTALL_METHOD_LOGICAL_DIRECT
    ) {
        return (
            image->manifest_payload_kind
                == TREEFORGE_RECOVERY_PAYLOAD_KIND_IMAGE
            && image->manifest_payload_bytes
                == image->source_bytes
            && tf_string_equal(
                image->manifest_payload_sha256,
                image->sha256
            )
            && image->cow_version_major == 0
            && image->cow_version_minor == 0
            && image->cow_block_size == 0
            && image->cow_merge_ops == 0
            && image->cow_data_ops == 0
            && image->cow_replace_ops == 0
            && image->cow_zero_ops == 0
            && image->cow_copy_ops == 0
            && image->cow_xor_ops == 0
            && image->cow_compression
                == TREEFORGE_RECOVERY_COW_COMPRESSION_NONE
        );
    }

    if (
        image->install_method
        != TREEFORGE_RECOVERY_INSTALL_METHOD_SNAPSHOT_COW
    ) {
        return 0;
    }

    return (
        image->manifest_payload_kind
            == TREEFORGE_RECOVERY_PAYLOAD_KIND_COW
        && image->image_format
            == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        && image->source_bytes
            == image->expanded_bytes
        && image->cow_version_major == 3
        && image->cow_version_minor == 0
        && image->cow_block_size == 4096
        && image->cow_merge_ops == 0
        && image->cow_data_ops
            == (
                image->cow_replace_ops
                + image->cow_zero_ops
                + image->cow_copy_ops
                + image->cow_xor_ops
            )
        && image->cow_data_ops > 0
        && image->cow_copy_ops == 0
        && image->cow_xor_ops == 0
        && image->cow_compression
            == TREEFORGE_RECOVERY_COW_COMPRESSION_LZ4
    );
}


static int tf_recovery_install_set_read_manifest(
    char *buffer,
    usize capacity,
    usize *length,
    u64 *error_errno
) {
    if (
        !buffer
        || capacity < 2
        || !length
        || !error_errno
    ) {
        return -1;
    }

    *length = 0;
    *error_errno = 0;

    long fd = tf_open(
        TREEFORGE_RECOVERY_INSTALL_SET_MANIFEST_PATH,
        O_RDONLY
        | O_NONBLOCK
    );

    if (fd < 0) {
        if (fd == -2) {
            return 0;
        }

        *error_errno = (
            (u64) (-fd)
        );

        return -1;
    }

    while (*length + 1 < capacity) {
        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) (
                buffer
                + *length
            ),
            capacity - *length - 1
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );

            tf_close(fd);
            return -1;
        }

        if (amount == 0) {
            buffer[*length] = '\0';

            tf_close(fd);

            return (
                *length > 0
                ? 1
                : -1
            );
        }

        *length += (
            (usize) amount
        );
    }

    /*
     * Buffer is full. A valid manifest must already be at EOF.
     */
    char extra = 0;

    long amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) &extra,
        1
    );

    tf_close(fd);

    if (amount != 0) {
        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );
        }

        return -1;
    }

    buffer[*length] = '\0';

    return 1;
}


static int tf_recovery_install_set_validate_image_metadata(
    struct tf_recovery_install_set_image *image
) {
    if (!image) {
        return 0;
    }

    if (
        image->source_bytes == 0
        || image->expanded_bytes == 0
        || !image->sha256[0]
    ) {
        return 0;
    }

    if (
        image->image_format
        == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
    ) {
        return (
            image->source_bytes
                == image->expanded_bytes
            && image->sparse_block_size == 0
            && image->sparse_total_blocks == 0
            && image->sparse_total_chunks == 0
            && image->sparse_raw_chunks == 0
            && image->sparse_fill_chunks == 0
            && image->sparse_dont_care_chunks == 0
            && image->sparse_crc32_chunks == 0
        );
    }

    if (
        image->image_format
        != TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
        || image->sparse_block_size == 0
        || (
            image->sparse_block_size
            % 4U
        ) != 0
        || image->sparse_total_blocks == 0
        || image->sparse_total_chunks == 0
    ) {
        return 0;
    }

    u64 expected_expanded = (
        (u64) image->sparse_block_size
        * (u64) image->sparse_total_blocks
    );

    u64 described_chunks = (
        (u64) image->sparse_raw_chunks
        + (u64) image->sparse_fill_chunks
        + (u64) image->sparse_dont_care_chunks
        + (u64) image->sparse_crc32_chunks
    );

    return (
        expected_expanded
            == image->expanded_bytes
        && described_chunks
            == (u64) image->sparse_total_chunks
    );
}


static int tf_recovery_load_install_set(
    struct tf_recovery_install_set_result *result
) {
    if (!result) {
        return -1;
    }

    memset(
        result,
        0,
        sizeof(*result)
    );

    /*
     * Large enough for the current complete Slot A set while keeping
     * the freestanding parser bounded.
     */
    char buffer[32768];
    usize length = 0;
    u64 read_errno = 0;

    int read_status = (
        tf_recovery_install_set_read_manifest(
            buffer,
            sizeof(buffer),
            &length,
            &read_errno
        )
    );

    if (read_status == 0) {
        return 0;
    }

    result->present = 1;

    if (read_status < 0) {
        result->error_stage = 1;
        result->error_errno = read_errno;

        return -1;
    }

    usize position = 0;

    if (
        tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "treeforge-recovery-install-set-v1\n"
        )
    ) {
        result->wire_version = (
            TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V1
        );
    } else {
        position = 0;

        if (
            !tf_recovery_manifest_match(
                buffer,
                length,
                &position,
                "treeforge-recovery-install-set-v2\n"
            )
        ) {
            result->error_stage = 2;
            return -1;
        }

        result->wire_version = (
            TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
        );
    }

    if (
        !tf_recovery_manifest_match(
            buffer,
            length,
            &position,
            "target_slot="
        )
    ) {
        result->error_stage = 2;
        return -1;
    }

    if (
        position + 2 > length
        || (
            buffer[position] != 'a'
            && buffer[position] != 'b'
        )
        || buffer[position + 1] != '\n'
    ) {
        result->error_stage = 3;
        return -1;
    }

    result->target_slot = (
        buffer[position]
    );

    position += 2;

    u64 image_count = 0;

    if (
        !tf_recovery_descriptor_parse_u64_field(
            buffer,
            length,
            &position,
            "image_count=",
            &image_count
        )
        || image_count == 0
        || image_count
            > TREEFORGE_RECOVERY_MAX_INSTALL_SET_IMAGES
    ) {
        result->error_stage = 4;
        return -1;
    }

    result->image_count = (
        (int) image_count
    );

    for (
        int index = 0;
        index < result->image_count;
        index++
    ) {
        struct tf_recovery_install_set_image *image = (
            &result->images[index]
        );

        u64 block_size = 0;
        u64 total_blocks = 0;
        u64 total_chunks = 0;
        u64 raw_chunks = 0;
        u64 fill_chunks = 0;
        u64 dont_care_chunks = 0;
        u64 crc32_chunks = 0;

        if (
            !tf_recovery_install_set_parse_name(
                buffer,
                length,
                &position,
                "image=",
                image->canonical_name,
                sizeof(image->canonical_name)
            )
        ) {
            result->error_stage = 5;
            result->error_image_index = index;

            return -1;
        }

        if (
            result->wire_version
                == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
            && (
                !tf_recovery_install_set_parse_method(
                    buffer,
                    length,
                    &position,
                    &image->install_method
                )
                || !tf_recovery_install_set_parse_payload_kind(
                    buffer,
                    length,
                    &position,
                    &image->manifest_payload_kind
                )
            )
        ) {
            result->error_stage = 20;
            result->error_image_index = index;

            return -1;
        }

        if (
            !tf_recovery_install_set_parse_format(
                buffer,
                length,
                &position,
                &image->image_format
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "bytes=",
                &image->source_bytes
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "expanded_bytes=",
                &image->expanded_bytes
            )
            || !tf_recovery_descriptor_parse_sha256(
                buffer,
                length,
                &position,
                image->sha256
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "block_size=",
                &block_size
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "total_blocks=",
                &total_blocks
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "total_chunks=",
                &total_chunks
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "raw_chunks=",
                &raw_chunks
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "fill_chunks=",
                &fill_chunks
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "dont_care_chunks=",
                &dont_care_chunks
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "crc32_chunks=",
                &crc32_chunks
            )
        ) {
            result->error_stage = 5;
            result->error_image_index = index;

            return -1;
        }

        if (
            result->wire_version
            == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V1
        ) {
            image->install_method = (
                TREEFORGE_RECOVERY_INSTALL_METHOD_UNKNOWN
            );

            image->manifest_payload_kind = (
                TREEFORGE_RECOVERY_PAYLOAD_KIND_IMAGE
            );

            image->manifest_payload_bytes = (
                image->source_bytes
            );

            tf_copy_string(
                image->manifest_payload_sha256,
                sizeof(image->manifest_payload_sha256),
                image->sha256
            );

            image->cow_compression = (
                TREEFORGE_RECOVERY_COW_COMPRESSION_NONE
            );
        } else if (
            !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "payload_bytes=",
                &image->manifest_payload_bytes
            )
            || !tf_recovery_install_set_parse_named_sha256(
                buffer,
                length,
                &position,
                "payload_sha256=",
                image->manifest_payload_sha256
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_version_major=",
                &image->cow_version_major
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_version_minor=",
                &image->cow_version_minor
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_block_size=",
                &image->cow_block_size
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_merge_ops=",
                &image->cow_merge_ops
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_data_ops=",
                &image->cow_data_ops
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_replace_ops=",
                &image->cow_replace_ops
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_zero_ops=",
                &image->cow_zero_ops
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_copy_ops=",
                &image->cow_copy_ops
            )
            || !tf_recovery_descriptor_parse_u64_field(
                buffer,
                length,
                &position,
                "cow_xor_ops=",
                &image->cow_xor_ops
            )
            || !tf_recovery_install_set_parse_cow_compression(
                buffer,
                length,
                &position,
                &image->cow_compression
            )
        ) {
            result->error_stage = 21;
            result->error_image_index = index;

            return -1;
        }

        if (
            block_size > 0xffffffffULL
            || total_blocks > 0xffffffffULL
            || total_chunks > 0xffffffffULL
            || raw_chunks > 0xffffffffULL
            || fill_chunks > 0xffffffffULL
            || dont_care_chunks > 0xffffffffULL
            || crc32_chunks > 0xffffffffULL
        ) {
            result->error_stage = 6;
            result->error_image_index = index;

            return -1;
        }

        image->sparse_block_size = (
            (u32) block_size
        );

        image->sparse_total_blocks = (
            (u32) total_blocks
        );

        image->sparse_total_chunks = (
            (u32) total_chunks
        );

        image->sparse_raw_chunks = (
            (u32) raw_chunks
        );

        image->sparse_fill_chunks = (
            (u32) fill_chunks
        );

        image->sparse_dont_care_chunks = (
            (u32) dont_care_chunks
        );

        image->sparse_crc32_chunks = (
            (u32) crc32_chunks
        );

        if (
            !tf_recovery_install_set_validate_image_metadata(
                image
            )
        ) {
            result->error_stage = 7;
            result->error_image_index = index;

            return -1;
        }

        if (
            result->wire_version
                == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
            && !tf_recovery_install_set_validate_v2_realization(
                image
            )
        ) {
            result->error_stage = 22;
            result->error_image_index = index;

            return -1;
        }

        /*
         * Canonical image names must be unique inside one transaction.
         */
        for (
            int previous = 0;
            previous < index;
            previous++
        ) {
            if (
                tf_string_equal(
                    result->images[previous]
                        .canonical_name,
                    image->canonical_name
                )
            ) {
                result->error_stage = 8;
                result->error_image_index = index;

                return -1;
            }
        }
    }

    if (position != length) {
        result->error_stage = 9;
        return -1;
    }

    /*
     * Everything below is Recovery-derived. The host does not declare
     * target type, capacity, active state, or allocation action.
     */
    result->active_slot_resolved = (
        tf_recovery_flash_targets
            .active_slot_resolved
    );

    result->active_slot = (
        tf_recovery_flash_targets
            .active_slot
    );

    result->target_slot_safe = (
        result->active_slot_resolved
        && result->active_slot
            != result->target_slot
    );

    if (!result->target_slot_safe) {
        result->error_stage = 10;
        return -1;
    }

    for (
        int index = 0;
        index < result->image_count;
        index++
    ) {
        struct tf_recovery_install_set_image *image = (
            &result->images[index]
        );

        char exact_target[
            TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
        ];

        exact_target[0] = '\0';

        usize exact_position = 0;

        exact_position = tf_append_text(
            exact_target,
            sizeof(exact_target),
            exact_position,
            image->canonical_name
        );

        char suffix[3];

        suffix[0] = '_';
        suffix[1] = result->target_slot;
        suffix[2] = '\0';

        tf_append_text(
            exact_target,
            sizeof(exact_target),
            exact_position,
            suffix
        );

        const struct tf_recovery_flash_target *target = (
            tf_recovery_find_unified_flash_target(
                exact_target
            )
        );

        if (!target) {
            result->error_stage = 11;
            result->error_image_index = index;

            return -1;
        }

        image->target_resolved = 1;

        tf_copy_string(
            image->target_partition_name,
            sizeof(image->target_partition_name),
            target->partition_name
        );

        image->target_type = (
            target->target_type
        );

        image->target_flash_policy = (
            target->flash_policy
        );

        image->target_active = (
            target->active
        );

        image->target_selectable = (
            target->selectable
        );

        image->target_capacity_bytes = (
            target->capacity_bytes
        );

        image->target_allocation_present = (
            target->allocation_present
        );

        if (
            target->flash_policy
                != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
            || target->active
            || !target->selectable
            || target->slot
                != result->target_slot
        ) {
            result->error_stage = 12;
            result->error_image_index = index;

            return -1;
        }

        if (
            result->wire_version
            == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
        ) {
            if (
                image->install_method
                    == TREEFORGE_RECOVERY_INSTALL_METHOD_PHYSICAL_DIRECT
            ) {
                if (
                    target->target_type
                    != TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
                ) {
                    result->error_stage = 23;
                    result->error_image_index = index;

                    return -1;
                }
            } else if (
                image->install_method
                    == TREEFORGE_RECOVERY_INSTALL_METHOD_LOGICAL_DIRECT
            ) {
                if (
                    target->target_type
                        != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
                    || tf_recovery_lp_inventory.virtual_ab
                ) {
                    result->error_stage = 23;
                    result->error_image_index = index;

                    return -1;
                }
            } else if (
                image->install_method
                    == TREEFORGE_RECOVERY_INSTALL_METHOD_SNAPSHOT_COW
            ) {
                if (
                    target->target_type
                        != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
                    || !tf_recovery_lp_inventory.virtual_ab
                ) {
                    result->error_stage = 24;
                    result->error_image_index = index;

                    return -1;
                }

                result->snapshot_cow_count++;
            } else {
                result->error_stage = 23;
                result->error_image_index = index;

                return -1;
            }
        }

        if (
            image->image_format
            == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        ) {
            result->raw_count++;
        } else {
            result->sparse_count++;
        }

        /*
         * A Virtual A/B snapshot target is intentionally not classified
         * through the direct LP allocation/resize path below.
         *
         * libsnapshot owns target metadata and COW backing allocation.
         */
        if (
            result->wire_version
                == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
            && image->install_method
                == TREEFORGE_RECOVERY_INSTALL_METHOD_SNAPSHOT_COW
        ) {
            result->logical_count++;

            image->install_action = (
                TREEFORGE_RECOVERY_INSTALL_ACTION_SNAPSHOT
            );

            continue;
        }

        if (
            target->target_type
            == TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        ) {
            result->physical_count++;

            if (
                image->expanded_bytes
                > target->capacity_bytes
            ) {
                result->error_stage = 13;
                result->error_image_index = index;

                return -1;
            }

            image->install_action = (
                TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
            );

            continue;
        }

        if (
            target->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        ) {
            result->error_stage = 14;
            result->error_image_index = index;

            return -1;
        }

        result->logical_count++;

        if (!target->allocation_present) {
            image->install_action = (
                TREEFORGE_RECOVERY_INSTALL_ACTION_ALLOCATE
            );

            result->allocation_count++;
        } else if (
            image->expanded_bytes
            > target->capacity_bytes
        ) {
            image->install_action = (
                TREEFORGE_RECOVERY_INSTALL_ACTION_RESIZE
            );

            result->resize_count++;
        } else {
            image->install_action = (
                TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
            );
        }
    }

    result->parsed = 1;
    result->plan_resolved = 1;

    return 1;
}


static const char *
tf_recovery_install_action_name(
    int action
) {
    if (
        action
        == TREEFORGE_RECOVERY_INSTALL_ACTION_ALLOCATE
    ) {
        return "ALLOCATE";
    }

    if (
        action
        == TREEFORGE_RECOVERY_INSTALL_ACTION_RESIZE
    ) {
        return "RESIZE";
    }

    if (
        action
        == TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
    ) {
        return "FITS";
    }

    if (
        action
        == TREEFORGE_RECOVERY_INSTALL_ACTION_SNAPSHOT
    ) {
        return "SNAPSHOT";
    }

    return "-";
}


static void tf_run_requested_unified_image_plan(
    struct tf_recovery_unified_image_plan_result *result
) {
    if (!result) {
        return;
    }

    char request[256];

    long amount = tf_read_path(
        TREEFORGE_RECOVERY_UNIFIED_IMAGE_PLAN_REQUEST_PATH,
        request,
        sizeof(request)
    );

    /*
     * No request means preserve the previous read-only plan for
     * Diagnostics inspection.
     */
    if (amount <= 0) {
        return;
    }

    memset(
        result,
        0,
        sizeof(*result)
    );

    result->requested = 1;

    /*
     * This planner cannot authorize a writer.
     */
    result->write_ready = 0;

    long unlink_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_UNIFIED_IMAGE_PLAN_REQUEST_PATH,
        0
    );

    if (unlink_result < 0) {
        result->error_stage = 1;
        result->error_errno = (
            (u64) (-unlink_result)
        );

        return;
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        !tf_parse_read_probe_name(
            request,
            (usize) amount,
            result->requested_partition_name,
            sizeof(
                result->requested_partition_name
            )
        )
    ) {
        result->error_stage = 2;
        return;
    }

    const struct tf_recovery_flash_target *target = (
        tf_recovery_find_unified_flash_target(
            result->requested_partition_name
        )
    );

    if (!target) {
        result->error_stage = 3;
        return;
    }

    result->target_resolved = 1;
    result->target_type = (
        target->target_type
    );

    result->target_flash_policy = (
        target->flash_policy
    );

    tf_copy_string(
        result->target_partition_name,
        sizeof(result->target_partition_name),
        target->partition_name
    );

    tf_copy_string(
        result->target_canonical_name,
        sizeof(result->target_canonical_name),
        target->canonical_name
    );

    result->target_slot = target->slot;
    result->target_active = target->active;
    result->target_selectable = (
        target->selectable
    );

    result->target_capacity_bytes = (
        target->capacity_bytes
    );

    result->target_allocation_present = (
        target->allocation_present
    );

    if (
        target->flash_policy
        != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
    ) {
        result->error_stage = 4;
        return;
    }

    if (target->active) {
        result->error_stage = 5;
        return;
    }

    if (!target->selectable) {
        result->error_stage = 6;
        return;
    }

    /*
     * Unified source selection.
     *
     * A streaming source never falls through to regular-file staging.
     * The descriptor and existing stream manifest must agree on the
     * exact source byte length and SHA-256 before descriptor-supplied
     * format metadata is trusted for planning.
     */
    struct tf_recovery_image_descriptor descriptor;

    int descriptor_status = (
        tf_recovery_load_image_descriptor(
            &descriptor
        )
    );

    if (descriptor_status < 0) {
        result->error_stage = 8;
        return;
    }

    u64 manifest_bytes = 0;
    char manifest_sha256[65];

    int manifest_status = (
        tf_recovery_load_stream_manifest(
            &manifest_bytes,
            manifest_sha256
        )
    );

    if (manifest_status < 0) {
        result->error_stage = 9;
        return;
    }

    if (descriptor_status == 1) {
        result->source_described = 1;
        result->source_descriptor_valid = 1;

        if (manifest_status != 1) {
            result->error_stage = 10;
            return;
        }

        result->source_streaming = 1;
        result->source_manifest_valid = 1;

        result->source_identity_match = (
            descriptor.source_bytes
                == manifest_bytes
            && tf_string_equal(
                descriptor.sha256,
                manifest_sha256
            )
        );

        if (!result->source_identity_match) {
            result->error_stage = 12;
            return;
        }

        result->source_format = (
            descriptor.image_format
        );

        tf_copy_string(
            result->source_sha256,
            sizeof(result->source_sha256),
            descriptor.sha256
        );

        result->source_bytes = (
            descriptor.source_bytes
        );

        result->expanded_bytes = (
            descriptor.expanded_bytes
        );

        /*
         * For descriptor-backed sparse planning this means the sparse
         * metadata is internally consistent. The actual streamed sparse
         * structure must still be validated while consuming the stream
         * before any future write can be committed.
         */
        result->sparse_structure_valid = (
            descriptor.sparse_metadata_valid
        );

        result->sparse_block_size = (
            descriptor.sparse_block_size
        );

        result->sparse_total_blocks = (
            descriptor.sparse_total_blocks
        );

        result->sparse_total_chunks = (
            descriptor.sparse_total_chunks
        );

        result->sparse_raw_chunks = (
            descriptor.sparse_raw_chunks
        );

        result->sparse_fill_chunks = (
            descriptor.sparse_fill_chunks
        );

        result->sparse_dont_care_chunks = (
            descriptor.sparse_dont_care_chunks
        );

        result->sparse_crc32_chunks = (
            descriptor.sparse_crc32_chunks
        );
    } else {
        /*
         * A stream manifest without a descriptor represents a real
         * streaming source, but the unified planner lacks the metadata
         * needed to determine RAW-vs-SPARSE expanded size. Fail closed
         * rather than silently inspecting a possibly stale regular file.
         */
        if (manifest_status == 1) {
            result->error_stage = 11;
            return;
        }

        struct tf_recovery_image_inspection inspection;

        tf_recovery_inspect_staged_image(
            &inspection
        );

        result->source_open_succeeded = (
            inspection.source_open_succeeded
        );

        if (!inspection.inspection_complete) {
            result->error_stage = (
                100
                + inspection.error_stage
            );

            result->error_errno = (
                inspection.error_errno
            );

            return;
        }

        result->source_inspected = 1;

        result->source_format = (
            inspection.image_format
        );

        result->source_bytes = (
            inspection.source_bytes
        );

        result->expanded_bytes = (
            inspection.expanded_bytes
        );

        result->sparse_structure_valid = (
            inspection.sparse_structure_valid
        );

        result->sparse_block_size = (
            inspection.sparse_block_size
        );

        result->sparse_total_blocks = (
            inspection.sparse_total_blocks
        );

        result->sparse_total_chunks = (
            inspection.sparse_total_chunks
        );

        result->sparse_raw_chunks = (
            inspection.sparse_raw_chunks
        );

        result->sparse_fill_chunks = (
            inspection.sparse_fill_chunks
        );

        result->sparse_dont_care_chunks = (
            inspection.sparse_dont_care_chunks
        );

        result->sparse_crc32_chunks = (
            inspection.sparse_crc32_chunks
        );
    }

    if (
        target->target_type
        == TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
    ) {
        result->physical_capacity_sufficient = (
            result->expanded_bytes
            <= target->capacity_bytes
        );

        result->fits_current_allocation = (
            result->physical_capacity_sufficient
        );

        result->plan_resolved = 1;

        return;
    }

    if (
        target->target_type
        != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
    ) {
        result->error_stage = 7;
        return;
    }

    /*
     * This first logical planner answers allocation questions only.
     *
     * It does not yet choose new physical extents or modify LP metadata.
     */
    result->fits_current_allocation = (
        target->allocation_present
        && result->expanded_bytes
            <= target->capacity_bytes
    );

    result->allocation_required = (
        !target->allocation_present
        && result->expanded_bytes > 0
    );

    result->resize_required = (
        result->expanded_bytes
        > target->capacity_bytes
    );

    result->metadata_update_required = (
        result->allocation_required
        || result->resize_required
    );

    result->plan_resolved = 1;

    /*
     * Intentionally remains zero.
     */
    result->write_ready = 0;
}


static const char *
tf_recovery_image_format_name(
    int format
) {
    if (
        format
        == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
    ) {
        return "RAW";
    }

    if (
        format
        == TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
    ) {
        return "ANDROID SPARSE";
    }

    return "-";
}


static int tf_lp_table_bounds_valid(
    u32 tables_size,
    const struct tf_recovery_lp_table_descriptor *table
) {
    if (!table) {
        return 0;
    }

    if (
        table->offset
        > tables_size
    ) {
        return 0;
    }

    u64 size = (
        (u64) table->num_entries
        * (u64) table->entry_size
    );

    if (
        size
        > (
            (u64) tables_size
            - (u64) table->offset
        )
    ) {
        return 0;
    }

    return 1;
}


static void tf_lp_read_descriptor(
    const unsigned char *header,
    usize offset,
    struct tf_recovery_lp_table_descriptor *descriptor
) {
    descriptor->offset = (
        tf_lp_load_le32(
            header + offset
        )
    );

    descriptor->num_entries = (
        tf_lp_load_le32(
            header + offset + 4
        )
    );

    descriptor->entry_size = (
        tf_lp_load_le32(
            header + offset + 8
        )
    );
}


static int tf_lp_parse_geometry_block(
    const unsigned char block[
        TREEFORGE_RECOVERY_LP_GEOMETRY_SIZE
    ],
    struct tf_recovery_lp_inventory *inventory
) {
    if (
        !block
        || !inventory
    ) {
        return 0;
    }

    if (
        tf_lp_load_le32(
            block
        )
        != TREEFORGE_RECOVERY_LP_GEOMETRY_MAGIC
    ) {
        return 0;
    }

    u32 struct_size = (
        tf_lp_load_le32(
            block + 4
        )
    );

    if (
        struct_size
        != TREEFORGE_RECOVERY_LP_GEOMETRY_STRUCT_SIZE
    ) {
        return 0;
    }

    unsigned char temporary[
        TREEFORGE_RECOVERY_LP_GEOMETRY_STRUCT_SIZE
    ];

    memcpy(
        temporary,
        block,
        sizeof(temporary)
    );

    memset(
        temporary + 8,
        0,
        32
    );

    unsigned char digest[32];

    tf_lp_hash_memory(
        temporary,
        sizeof(temporary),
        digest
    );

    if (
        memcmp(
            digest,
            block + 8,
            32
        ) != 0
    ) {
        return 0;
    }

    u32 metadata_max_size = (
        tf_lp_load_le32(
            block + 40
        )
    );

    u32 metadata_slot_count = (
        tf_lp_load_le32(
            block + 44
        )
    );

    u32 logical_block_size = (
        tf_lp_load_le32(
            block + 48
        )
    );

    if (
        metadata_max_size == 0
        || metadata_slot_count == 0
        || (
            metadata_max_size
            % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        ) != 0
        || logical_block_size == 0
        || (
            logical_block_size
            % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        ) != 0
    ) {
        return 0;
    }

    inventory->metadata_max_size = (
        metadata_max_size
    );

    inventory->metadata_slot_count = (
        metadata_slot_count
    );

    inventory->logical_block_size = (
        logical_block_size
    );

    return 1;
}


static int tf_lp_read_geometry(
    long fd,
    struct tf_recovery_lp_inventory *inventory
) {
    unsigned char block[
        TREEFORGE_RECOVERY_LP_GEOMETRY_SIZE
    ];

    u64 read_errno = 0;

    if (
        tf_lp_read_exact_at(
            fd,
            TREEFORGE_RECOVERY_LP_RESERVED_BYTES,
            block,
            sizeof(block),
            &read_errno
        )
        && tf_lp_parse_geometry_block(
            block,
            inventory
        )
    ) {
        inventory->geometry_resolved = 1;
        inventory->geometry_primary_valid = 1;
        inventory->geometry_backup_used = 0;
        return 1;
    }

    read_errno = 0;

    if (
        tf_lp_read_exact_at(
            fd,
            TREEFORGE_RECOVERY_LP_RESERVED_BYTES
                + TREEFORGE_RECOVERY_LP_GEOMETRY_SIZE,
            block,
            sizeof(block),
            &read_errno
        )
        && tf_lp_parse_geometry_block(
            block,
            inventory
        )
    ) {
        inventory->geometry_resolved = 1;
        inventory->geometry_primary_valid = 0;
        inventory->geometry_backup_used = 1;
        return 1;
    }

    inventory->error_stage = 5;
    inventory->error_errno = read_errno;

    return 0;
}


static u64 tf_lp_primary_metadata_offset(
    const struct tf_recovery_lp_inventory *inventory,
    u32 metadata_slot
) {
    return (
        TREEFORGE_RECOVERY_LP_RESERVED_BYTES
        + (
            TREEFORGE_RECOVERY_LP_GEOMETRY_SIZE
            * 2ULL
        )
        + (
            (u64) inventory->metadata_max_size
            * (u64) metadata_slot
        )
    );
}


static u64 tf_lp_backup_metadata_offset(
    const struct tf_recovery_lp_inventory *inventory,
    u32 metadata_slot
) {
    return (
        TREEFORGE_RECOVERY_LP_RESERVED_BYTES
        + (
            TREEFORGE_RECOVERY_LP_GEOMETRY_SIZE
            * 2ULL
        )
        + (
            (u64) inventory->metadata_max_size
            * (u64) inventory->metadata_slot_count
        )
        + (
            (u64) inventory->metadata_max_size
            * (u64) metadata_slot
        )
    );
}


static int tf_lp_read_table_entry(
    long fd,
    u64 metadata_offset,
    u32 header_size,
    const struct tf_recovery_lp_table_descriptor *table,
    u32 index,
    unsigned char *buffer,
    usize buffer_size,
    u64 *error_errno
) {
    if (
        !table
        || !buffer
        || index >= table->num_entries
        || buffer_size < table->entry_size
    ) {
        return 0;
    }

    u64 offset = (
        metadata_offset
        + (u64) header_size
        + (u64) table->offset
        + (
            (u64) index
            * (u64) table->entry_size
        )
    );

    return tf_lp_read_exact_at(
        fd,
        offset,
        buffer,
        table->entry_size,
        error_errno
    );
}


static int tf_lp_validate_metadata_copy(
    long fd,
    u64 metadata_offset,
    struct tf_recovery_lp_inventory *inventory,
    struct tf_recovery_lp_slot_result *slot,
    struct tf_recovery_lp_metadata_layout *layout
) {
    unsigned char header[
        TREEFORGE_RECOVERY_LP_HEADER_V1_2_SIZE
    ];

    memset(
        header,
        0,
        sizeof(header)
    );

    u64 read_errno = 0;

    if (
        !tf_lp_read_exact_at(
            fd,
            metadata_offset,
            header,
            TREEFORGE_RECOVERY_LP_HEADER_V1_0_SIZE,
            &read_errno
        )
    ) {
        slot->error_stage = 1;
        slot->error_errno = read_errno;
        return 0;
    }

    if (
        tf_lp_load_le32(
            header
        )
        != TREEFORGE_RECOVERY_LP_HEADER_MAGIC
    ) {
        slot->error_stage = 2;
        return 0;
    }

    u16 major_version = (
        tf_lp_load_le16(
            header + 4
        )
    );

    u16 minor_version = (
        tf_lp_load_le16(
            header + 6
        )
    );

    if (
        major_version
            != TREEFORGE_RECOVERY_LP_MAJOR_VERSION
        || minor_version
            > TREEFORGE_RECOVERY_LP_MINOR_VERSION_MAX
    ) {
        slot->error_stage = 2;
        return 0;
    }

    u32 expected_header_size = (
        minor_version < 2
        ? TREEFORGE_RECOVERY_LP_HEADER_V1_0_SIZE
        : TREEFORGE_RECOVERY_LP_HEADER_V1_2_SIZE
    );

    u32 header_size = (
        tf_lp_load_le32(
            header + 8
        )
    );

    if (
        header_size
        != expected_header_size
    ) {
        slot->error_stage = 2;
        return 0;
    }

    if (
        header_size
        > TREEFORGE_RECOVERY_LP_HEADER_V1_0_SIZE
    ) {
        read_errno = 0;

        if (
            !tf_lp_read_exact_at(
                fd,
                metadata_offset,
                header,
                header_size,
                &read_errno
            )
        ) {
            slot->error_stage = 1;
            slot->error_errno = read_errno;
            return 0;
        }
    }

    unsigned char temporary[
        TREEFORGE_RECOVERY_LP_HEADER_V1_2_SIZE
    ];

    memset(
        temporary,
        0,
        sizeof(temporary)
    );

    memcpy(
        temporary,
        header,
        header_size
    );

    memset(
        temporary + 12,
        0,
        32
    );

    unsigned char digest[32];

    tf_lp_hash_memory(
        temporary,
        header_size,
        digest
    );

    if (
        memcmp(
            digest,
            header + 12,
            32
        ) != 0
    ) {
        slot->error_stage = 3;
        return 0;
    }

    u32 tables_size = (
        tf_lp_load_le32(
            header + 44
        )
    );

    if (
        tables_size
            > inventory->metadata_max_size
        || (
            (u64) header_size
            + (u64) tables_size
        ) > (
            (u64) inventory->metadata_max_size
        )
    ) {
        slot->error_stage = 4;
        return 0;
    }

    memset(
        layout,
        0,
        sizeof(*layout)
    );

    layout->major_version = major_version;
    layout->minor_version = minor_version;
    layout->header_size = header_size;
    layout->tables_size = tables_size;

    tf_lp_read_descriptor(
        header,
        80,
        &layout->partitions
    );

    tf_lp_read_descriptor(
        header,
        92,
        &layout->extents
    );

    tf_lp_read_descriptor(
        header,
        104,
        &layout->groups
    );

    tf_lp_read_descriptor(
        header,
        116,
        &layout->block_devices
    );

    if (
        layout->partitions.entry_size
            != TREEFORGE_RECOVERY_LP_PARTITION_ENTRY_SIZE
        || layout->extents.entry_size
            != TREEFORGE_RECOVERY_LP_EXTENT_ENTRY_SIZE
        || layout->groups.entry_size
            != TREEFORGE_RECOVERY_LP_GROUP_ENTRY_SIZE
        || layout->block_devices.entry_size
            != TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_ENTRY_SIZE
        || !tf_lp_table_bounds_valid(
            tables_size,
            &layout->partitions
        )
        || !tf_lp_table_bounds_valid(
            tables_size,
            &layout->extents
        )
        || !tf_lp_table_bounds_valid(
            tables_size,
            &layout->groups
        )
        || !tf_lp_table_bounds_valid(
            tables_size,
            &layout->block_devices
        )
        || layout->block_devices.num_entries == 0
    ) {
        slot->error_stage = 4;
        return 0;
    }

    read_errno = 0;

    if (
        !tf_lp_hash_region(
            fd,
            metadata_offset
                + (u64) header_size,
            tables_size,
            digest,
            &read_errno
        )
    ) {
        slot->error_stage = 5;
        slot->error_errno = read_errno;
        return 0;
    }

    if (
        memcmp(
            digest,
            header + 48,
            32
        ) != 0
    ) {
        slot->error_stage = 5;
        return 0;
    }

    /*
     * Validate block-device records and the metadata/content boundary before
     * accepting any logical partition record.
     */
    for (
        u32 index = 0;
        index < layout->block_devices.num_entries;
        index++
    ) {
        unsigned char entry[
            TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_ENTRY_SIZE
        ];

        read_errno = 0;

        if (
            !tf_lp_read_table_entry(
                fd,
                metadata_offset,
                header_size,
                &layout->block_devices,
                index,
                entry,
                sizeof(entry),
                &read_errno
            )
        ) {
            slot->error_stage = 6;
            slot->error_errno = read_errno;
            return 0;
        }

        u32 alignment = (
            tf_lp_load_le32(
                entry + 8
            )
        );

        u32 alignment_offset = (
            tf_lp_load_le32(
                entry + 12
            )
        );

        u64 device_size = (
            tf_lp_load_le64(
                entry + 16
            )
        );

        if (
            (
                alignment
                % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            ) != 0
            || (
                alignment_offset
                % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            ) != 0
            || (
                alignment == 0
                && alignment_offset != 0
            )
            || (
                alignment != 0
                && alignment_offset > alignment
            )
        ) {
            slot->error_stage = 6;
            return 0;
        }

        if (
            index == 0
            && device_size
                > inventory->super_capacity_bytes
        ) {
            slot->error_stage = 6;
            return 0;
        }

        if (index == 0) {
            u64 first_logical_sector = (
                tf_lp_load_le64(
                    entry
                )
            );

            u64 metadata_region = (
                TREEFORGE_RECOVERY_LP_RESERVED_BYTES
                + (
                    TREEFORGE_RECOVERY_LP_GEOMETRY_SIZE
                    + (
                        (u64)
                            inventory->metadata_max_size
                        * (u64)
                            inventory->metadata_slot_count
                    )
                ) * 2ULL
            );

            if (
                first_logical_sector
                    > (
                        0xffffffffffffffffULL
                        / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
                    )
                || metadata_region
                    > (
                        first_logical_sector
                        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
                    )
            ) {
                slot->error_stage = 6;
                return 0;
            }
        }
    }

    /*
     * Validate group table readability.
     */
    for (
        u32 index = 0;
        index < layout->groups.num_entries;
        index++
    ) {
        unsigned char entry[
            TREEFORGE_RECOVERY_LP_GROUP_ENTRY_SIZE
        ];

        read_errno = 0;

        if (
            !tf_lp_read_table_entry(
                fd,
                metadata_offset,
                header_size,
                &layout->groups,
                index,
                entry,
                sizeof(entry),
                &read_errno
            )
        ) {
            slot->error_stage = 6;
            slot->error_errno = read_errno;
            return 0;
        }

        u32 group_flags = (
            tf_lp_load_le32(
                entry + 36
            )
        );

        if (
            group_flags
            & ~TREEFORGE_RECOVERY_LP_GROUP_SLOT_SUFFIXED
        ) {
            slot->error_stage = 6;
            return 0;
        }
    }

    /*
     * Validate every extent before any record is published.
     */
    for (
        u32 index = 0;
        index < layout->extents.num_entries;
        index++
    ) {
        unsigned char entry[
            TREEFORGE_RECOVERY_LP_EXTENT_ENTRY_SIZE
        ];

        read_errno = 0;

        if (
            !tf_lp_read_table_entry(
                fd,
                metadata_offset,
                header_size,
                &layout->extents,
                index,
                entry,
                sizeof(entry),
                &read_errno
            )
        ) {
            slot->error_stage = 7;
            slot->error_errno = read_errno;
            return 0;
        }

        u32 target_type = (
            tf_lp_load_le32(
                entry + 8
            )
        );

        u64 target_data = (
            tf_lp_load_le64(
                entry + 12
            )
        );

        u32 target_source = (
            tf_lp_load_le32(
                entry + 20
            )
        );

        if (
            target_type
                != TREEFORGE_RECOVERY_LP_TARGET_LINEAR
            && target_type
                != TREEFORGE_RECOVERY_LP_TARGET_ZERO
        ) {
            slot->error_stage = 7;
            return 0;
        }

        if (
            target_type
                == TREEFORGE_RECOVERY_LP_TARGET_LINEAR
            && target_source
                >= layout->block_devices.num_entries
        ) {
            slot->error_stage = 7;
            return 0;
        }

        if (
            target_type
                == TREEFORGE_RECOVERY_LP_TARGET_ZERO
            && (
                target_data != 0
                || target_source != 0
            )
        ) {
            slot->error_stage = 7;
            return 0;
        }
    }

    /*
     * Validate every partition's extent and group references.
     */
    for (
        u32 index = 0;
        index < layout->partitions.num_entries;
        index++
    ) {
        unsigned char entry[
            TREEFORGE_RECOVERY_LP_PARTITION_ENTRY_SIZE
        ];

        read_errno = 0;

        if (
            !tf_lp_read_table_entry(
                fd,
                metadata_offset,
                header_size,
                &layout->partitions,
                index,
                entry,
                sizeof(entry),
                &read_errno
            )
        ) {
            slot->error_stage = 8;
            slot->error_errno = read_errno;
            return 0;
        }

        u32 attributes = (
            tf_lp_load_le32(
                entry + 36
            )
        );

        u32 valid_attributes = (
            TREEFORGE_RECOVERY_LP_ATTR_READONLY
            | TREEFORGE_RECOVERY_LP_ATTR_SLOT_SUFFIXED
        );

        if (minor_version >= 1) {
            valid_attributes |= (
                TREEFORGE_RECOVERY_LP_ATTR_UPDATED
                | TREEFORGE_RECOVERY_LP_ATTR_DISABLED
            );
        }

        if (
            attributes
            & ~valid_attributes
        ) {
            slot->error_stage = 8;
            return 0;
        }

        u32 first_extent = (
            tf_lp_load_le32(
                entry + 40
            )
        );

        u32 num_extents = (
            tf_lp_load_le32(
                entry + 44
            )
        );

        u32 group_index = (
            tf_lp_load_le32(
                entry + 48
            )
        );

        u64 extent_end = (
            (u64) first_extent
            + (u64) num_extents
        );

        if (
            extent_end
                > layout->extents.num_entries
            || group_index
                >= layout->groups.num_entries
        ) {
            slot->error_stage = 8;
            return 0;
        }
    }

    slot->major_version = major_version;
    slot->minor_version = minor_version;
    slot->header_size = header_size;
    slot->tables_size = tables_size;

    slot->header_flags = (
        minor_version >= 2
        ? tf_lp_load_le32(
            header + 128
        )
        : 0U
    );

    slot->partition_count = (
        layout->partitions.num_entries
    );

    slot->extent_count = (
        layout->extents.num_entries
    );

    slot->group_count = (
        layout->groups.num_entries
    );

    slot->block_device_count = (
        layout->block_devices.num_entries
    );

    slot->error_stage = 0;
    slot->error_errno = 0;

    return 1;
}


static int tf_lp_adjusted_table_name(
    long fd,
    u64 metadata_offset,
    u32 header_size,
    const struct tf_recovery_lp_table_descriptor *table,
    u32 index,
    u32 name_offset,
    u32 name_capacity,
    u32 flags_offset,
    u32 slot_suffix_flag,
    u32 metadata_slot,
    char *output,
    usize output_capacity
) {
    unsigned char entry[
        TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_ENTRY_SIZE
    ];

    if (
        !table
        || table->entry_size > sizeof(entry)
        || name_capacity == 0
        || name_offset > table->entry_size
        || name_capacity
            > table->entry_size - name_offset
        || flags_offset > table->entry_size
        || 4U > table->entry_size - flags_offset
    ) {
        return 0;
    }

    u64 read_errno = 0;

    if (
        !tf_lp_read_table_entry(
            fd,
            metadata_offset,
            header_size,
            table,
            index,
            entry,
            sizeof(entry),
            &read_errno
        )
    ) {
        return 0;
    }

    if (
        !tf_lp_copy_fixed_name(
            entry + name_offset,
            name_capacity,
            output,
            output_capacity
        )
    ) {
        return 0;
    }

    u32 flags = (
        tf_lp_load_le32(
            entry + flags_offset
        )
    );

    if (
        flags
        & slot_suffix_flag
    ) {
        if (
            !tf_lp_append_slot_suffix(
                output,
                output_capacity,
                metadata_slot
            )
        ) {
            return 0;
        }
    }

    return 1;
}


static int tf_recovery_lp_align_sector(
    const struct tf_recovery_lp_inventory *inventory,
    u64 sector,
    u64 *aligned_sector
) {
    if (
        !inventory
        || !aligned_sector
        || sector
            > (
                0xffffffffffffffffULL
                / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            )
    ) {
        return 0;
    }

    u64 base = (
        sector
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    u32 alignment = (
        inventory->super_alignment_bytes
    );

    u32 alignment_offset = (
        inventory->super_alignment_offset_bytes
    );

    if (
        (
            alignment
            % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        ) != 0
        || (
            alignment_offset
            % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        ) != 0
        || (
            alignment == 0
            && alignment_offset != 0
        )
        || (
            alignment != 0
            && alignment_offset > alignment
        )
    ) {
        return 0;
    }

    u64 aligned = base;

    if (alignment != 0) {
        u64 remainder = (
            base % (u64) alignment
        );

        if (remainder != 0) {
            u64 add = (
                (u64) alignment
                - remainder
            );

            if (
                add
                > (
                    0xffffffffffffffffULL
                    - aligned
                )
            ) {
                return 0;
            }

            aligned += add;
        }

        if (
            alignment_offset
            > (
                0xffffffffffffffffULL
                - aligned
            )
        ) {
            return 0;
        }

        aligned += (
            (u64) alignment_offset
        );

        /*
         * Android 15 liblp AlignTo(base, alignment, offset):
         * use the preceding aligned boundary when adding the offset
         * would otherwise over-align the requested location.
         */
        if (
            aligned >= (u64) alignment
            && (
                aligned
                - (u64) alignment
            ) >= base
        ) {
            aligned -= (
                (u64) alignment
            );
        }
    }

    u64 sector_remainder = (
        aligned
        % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    if (sector_remainder != 0) {
        u64 add = (
            TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            - sector_remainder
        );

        if (
            add
            > (
                0xffffffffffffffffULL
                - aligned
            )
        ) {
            return 0;
        }

        aligned += add;
    }

    *aligned_sector = (
        aligned
        / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    return 1;
}


static int tf_recovery_lp_add_free_range(
    struct tf_recovery_lp_inventory *inventory,
    u64 start_sector,
    u64 end_sector
) {
    if (
        !inventory
        || start_sector >= end_sector
    ) {
        return 0;
    }

    u64 sectors = (
        end_sector - start_sector
    );

    if (
        sectors
        > (
            0xffffffffffffffffULL
            / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        )
    ) {
        return 0;
    }

    u64 bytes = (
        sectors
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    if (
        inventory->free_sectors
        > (
            0xffffffffffffffffULL
            - sectors
        )
        || inventory->free_bytes
        > (
            0xffffffffffffffffULL
            - bytes
        )
    ) {
        return 0;
    }

    inventory->free_sectors += sectors;
    inventory->free_bytes += bytes;

    if (
        sectors
        > inventory->largest_free_sectors
    ) {
        inventory->largest_free_start_sector = (
            start_sector
        );

        inventory->largest_free_sectors = sectors;
        inventory->largest_free_bytes = bytes;
    }

    if (
        inventory->free_range_count
        >= TREEFORGE_RECOVERY_LP_MAX_FREE_RANGES
    ) {
        inventory->free_ranges_omitted = 1;
        return 1;
    }

    struct tf_recovery_lp_free_range *range = (
        &inventory->free_ranges[
            inventory->free_range_count++
        ]
    );

    memset(
        range,
        0,
        sizeof(*range)
    );

    range->start_sector = start_sector;
    range->end_sector = end_sector;
    range->num_sectors = sectors;
    range->bytes = bytes;

    return 1;
}


static void tf_recovery_lp_publish_free_space(
    struct tf_recovery_lp_inventory *inventory
) {
    if (!inventory) {
        return;
    }

    inventory->free_space_resolved = 0;
    inventory->free_space_overlap = 0;

    inventory->free_range_count = 0;
    inventory->free_ranges_omitted = 0;

    inventory->free_sectors = 0;
    inventory->free_bytes = 0;

    inventory->largest_free_start_sector = 0;
    inventory->largest_free_sectors = 0;
    inventory->largest_free_bytes = 0;

    if (
        !inventory->super_data_region_resolved
        || inventory->super_first_logical_sector == 0
        || inventory->super_device_size_bytes == 0
        || (
            inventory->super_device_size_bytes
            % TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        ) != 0
        || inventory->extents_omitted
    ) {
        return;
    }

    /*
     * Scratch is static so a maximum-size metadata graph does not put
     * tens of KiB on Recovery's runtime stack.
     */
    static u64 starts[
        TREEFORGE_RECOVERY_LP_MAX_EXTENTS
    ];

    static u64 ends[
        TREEFORGE_RECOVERY_LP_MAX_EXTENTS
    ];

    int count = 0;

    for (
        int index = 0;
        index < inventory->extent_count;
        index++
    ) {
        const struct tf_recovery_logical_extent *extent = (
            &inventory->extents[index]
        );

        if (
            extent->target_type
                != TREEFORGE_RECOVERY_LP_TARGET_LINEAR
        ) {
            continue;
        }

        /*
         * This first allocator model supports exactly the canonical
         * source-0 super block device already required by the accepted
         * logical writer.
         */
        if (
            extent->target_source != 0
            || extent->num_sectors == 0
            || count
                >= TREEFORGE_RECOVERY_LP_MAX_EXTENTS
            || extent->target_data
                > (
                    0xffffffffffffffffULL
                    - extent->num_sectors
                )
        ) {
            return;
        }

        u64 end = (
            extent->target_data
            + extent->num_sectors
        );

        u64 device_end = (
            inventory->super_device_size_bytes
            / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        );

        if (
            extent->target_data
                < inventory->super_first_logical_sector
            || end > device_end
        ) {
            return;
        }

        starts[count] = extent->target_data;
        ends[count] = end;

        count++;
    }

    /*
     * Stable insertion sort by physical start sector.
     * LP metadata is small enough that this deterministic O(n^2)
     * read-only pass is preferable to introducing another allocator.
     */
    for (
        int index = 1;
        index < count;
        index++
    ) {
        u64 start_value = starts[index];
        u64 end_value = ends[index];

        int position = index;

        while (
            position > 0
            && starts[position - 1]
                > start_value
        ) {
            starts[position] = (
                starts[position - 1]
            );

            ends[position] = (
                ends[position - 1]
            );

            position--;
        }

        starts[position] = start_value;
        ends[position] = end_value;
    }

    for (
        int index = 1;
        index < count;
        index++
    ) {
        if (
            starts[index]
            < ends[index - 1]
        ) {
            inventory->free_space_overlap = 1;
            return;
        }
    }

    u64 cursor = (
        inventory->super_first_logical_sector
    );

    u64 device_end = (
        inventory->super_device_size_bytes
        / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    for (
        int index = 0;
        index < count;
        index++
    ) {
        u64 aligned_cursor = 0;

        if (
            !tf_recovery_lp_align_sector(
                inventory,
                cursor,
                &aligned_cursor
            )
        ) {
            return;
        }

        if (
            aligned_cursor
                < starts[index]
        ) {
            if (
                !tf_recovery_lp_add_free_range(
                    inventory,
                    aligned_cursor,
                    starts[index]
                )
            ) {
                return;
            }
        }

        if (ends[index] > cursor) {
            cursor = ends[index];
        }
    }

    u64 aligned_cursor = 0;

    if (
        !tf_recovery_lp_align_sector(
            inventory,
            cursor,
            &aligned_cursor
        )
    ) {
        return;
    }

    if (aligned_cursor < device_end) {
        if (
            !tf_recovery_lp_add_free_range(
                inventory,
                aligned_cursor,
                device_end
            )
        ) {
            return;
        }
    }

    inventory->free_space_resolved = 1;
}


static void tf_lp_publish_metadata(
    long fd,
    u64 metadata_offset,
    u32 metadata_slot,
    struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_lp_metadata_layout *layout
) {
    /*
     * Preserve the exact block-device data boundary from the same
     * authoritative metadata copy that owns the published partition
     * and extent graph.
     *
     * tf_lp_validate_metadata_copy() already validated this serialized
     * record before tf_lp_publish_metadata() can be called. Re-read it
     * here so downstream destructive planning does not have to infer
     * the boundary from geometry alone.
     */
    inventory->super_data_region_resolved = 0;
    inventory->super_first_logical_sector = 0;
    inventory->super_device_size_bytes = 0;

    inventory->super_alignment_bytes = 0;
    inventory->super_alignment_offset_bytes = 0;

    inventory->group_count = 0;
    inventory->groups_omitted = 0;

    inventory->free_space_resolved = 0;
    inventory->free_space_overlap = 0;
    inventory->free_range_count = 0;
    inventory->free_ranges_omitted = 0;
    inventory->free_sectors = 0;
    inventory->free_bytes = 0;
    inventory->largest_free_start_sector = 0;
    inventory->largest_free_sectors = 0;
    inventory->largest_free_bytes = 0;

    if (
        layout->block_devices.num_entries > 0
        && layout->block_devices.entry_size
            == TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_ENTRY_SIZE
    ) {
        unsigned char block_device_entry[
            TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_ENTRY_SIZE
        ];

        u64 block_device_errno = 0;

        if (
            tf_lp_read_table_entry(
                fd,
                metadata_offset,
                layout->header_size,
                &layout->block_devices,
                0,
                block_device_entry,
                sizeof(block_device_entry),
                &block_device_errno
            )
        ) {
            u64 first_logical_sector = (
                tf_lp_load_le64(
                    block_device_entry
                )
            );

            u32 alignment = (
                tf_lp_load_le32(
                    block_device_entry + 8
                )
            );

            u32 alignment_offset = (
                tf_lp_load_le32(
                    block_device_entry + 12
                )
            );

            u64 device_size = (
                tf_lp_load_le64(
                    block_device_entry + 16
                )
            );

            if (
                first_logical_sector > 0
                && first_logical_sector
                    <= (
                        0xffffffffffffffffULL
                        / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
                    )
                && device_size > 0
                && device_size
                    <= inventory->super_capacity_bytes
            ) {
                u64 first_logical_byte = (
                    first_logical_sector
                    * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
                );

                if (
                    first_logical_byte
                        < device_size
                ) {
                    inventory->super_first_logical_sector = (
                        first_logical_sector
                    );

                    inventory->super_device_size_bytes = (
                        device_size
                    );

                    inventory->super_alignment_bytes = (
                        alignment
                    );

                    inventory->super_alignment_offset_bytes = (
                        alignment_offset
                    );

                    inventory->super_data_region_resolved = 1;
                }
            }
        }
    }

    /*
     * Preserve authoritative serialized partition groups.
     *
     * Android's LpMetadataPartitionGroup layout is:
     *   0..35  name
     *   36..39 flags
     *   40..47 maximum_size bytes
     */
    for (
        u32 group_index = 0;
        group_index < layout->groups.num_entries;
        group_index++
    ) {
        unsigned char group_entry[
            TREEFORGE_RECOVERY_LP_GROUP_ENTRY_SIZE
        ];

        u64 group_errno = 0;

        if (
            !tf_lp_read_table_entry(
                fd,
                metadata_offset,
                layout->header_size,
                &layout->groups,
                group_index,
                group_entry,
                sizeof(group_entry),
                &group_errno
            )
        ) {
            inventory->groups_omitted = 1;
            continue;
        }

        if (
            inventory->group_count
            >= TREEFORGE_RECOVERY_LP_MAX_GROUPS
        ) {
            inventory->groups_omitted = 1;
            continue;
        }

        struct tf_recovery_lp_group *group = (
            &inventory->groups[
                inventory->group_count++
            ]
        );

        memset(
            group,
            0,
            sizeof(*group)
        );

        group->metadata_slot = metadata_slot;
        group->table_group_index = group_index;

        group->flags = (
            tf_lp_load_le32(
                group_entry + 36
            )
        );

        group->maximum_size_bytes = (
            tf_lp_load_le64(
                group_entry + 40
            )
        );

        group->unlimited = (
            group->maximum_size_bytes == 0
        );

        if (
            !tf_lp_copy_fixed_name(
                group_entry,
                36,
                group->group_name,
                sizeof(group->group_name)
            )
        ) {
            inventory->groups_omitted = 1;
            inventory->group_count--;
            continue;
        }

        if (
            group->flags
            & TREEFORGE_RECOVERY_LP_GROUP_SLOT_SUFFIXED
        ) {
            if (
                !tf_lp_append_slot_suffix(
                    group->group_name,
                    sizeof(group->group_name),
                    metadata_slot
                )
            ) {
                inventory->groups_omitted = 1;
                inventory->group_count--;
                continue;
            }
        }
    }

    for (
        u32 partition_index = 0;
        partition_index < layout->partitions.num_entries;
        partition_index++
    ) {
        unsigned char partition_entry[
            TREEFORGE_RECOVERY_LP_PARTITION_ENTRY_SIZE
        ];

        u64 read_errno = 0;

        if (
            !tf_lp_read_table_entry(
                fd,
                metadata_offset,
                layout->header_size,
                &layout->partitions,
                partition_index,
                partition_entry,
                sizeof(partition_entry),
                &read_errno
            )
        ) {
            inventory->partitions_omitted = 1;
            continue;
        }

        char partition_name[
            TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
        ];

        if (
            !tf_lp_copy_fixed_name(
                partition_entry,
                36,
                partition_name,
                sizeof(partition_name)
            )
        ) {
            inventory->partitions_omitted = 1;
            continue;
        }

        u32 attributes = (
            tf_lp_load_le32(
                partition_entry + 36
            )
        );

        if (
            attributes
            & TREEFORGE_RECOVERY_LP_ATTR_SLOT_SUFFIXED
        ) {
            if (
                !tf_lp_append_slot_suffix(
                    partition_name,
                    sizeof(partition_name),
                    metadata_slot
                )
            ) {
                inventory->partitions_omitted = 1;
                continue;
            }
        }

        u32 first_extent = (
            tf_lp_load_le32(
                partition_entry + 40
            )
        );

        u32 num_extents = (
            tf_lp_load_le32(
                partition_entry + 44
            )
        );

        u32 group_index = (
            tf_lp_load_le32(
                partition_entry + 48
            )
        );

        char group_name[
            TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
        ];

        group_name[0] = '\0';

        tf_lp_adjusted_table_name(
            fd,
            metadata_offset,
            layout->header_size,
            &layout->groups,
            group_index,
            0,
            36,
            36,
            TREEFORGE_RECOVERY_LP_GROUP_SLOT_SUFFIXED,
            metadata_slot,
            group_name,
            sizeof(group_name)
        );

        u64 partition_sectors = 0;

        for (
            u32 local_extent = 0;
            local_extent < num_extents;
            local_extent++
        ) {
            u32 table_extent = (
                first_extent
                + local_extent
            );

            unsigned char extent_entry[
                TREEFORGE_RECOVERY_LP_EXTENT_ENTRY_SIZE
            ];

            read_errno = 0;

            if (
                !tf_lp_read_table_entry(
                    fd,
                    metadata_offset,
                    layout->header_size,
                    &layout->extents,
                    table_extent,
                    extent_entry,
                    sizeof(extent_entry),
                    &read_errno
                )
            ) {
                inventory->extents_omitted = 1;
                continue;
            }

            u64 num_sectors = (
                tf_lp_load_le64(
                    extent_entry
                )
            );

            if (
                partition_sectors
                <= (
                    0xffffffffffffffffULL
                    - num_sectors
                )
            ) {
                partition_sectors += (
                    num_sectors
                );
            }

            if (
                inventory->extent_count
                >= TREEFORGE_RECOVERY_LP_MAX_EXTENTS
            ) {
                inventory->extents_omitted = 1;
                continue;
            }

            struct tf_recovery_logical_extent *extent = (
                &inventory->extents[
                    inventory->extent_count++
                ]
            );

            memset(
                extent,
                0,
                sizeof(*extent)
            );

            extent->metadata_slot = (
                metadata_slot
            );

            tf_copy_string(
                extent->partition_name,
                sizeof(extent->partition_name),
                partition_name
            );

            extent->partition_extent_index = (
                local_extent
            );

            extent->table_extent_index = (
                table_extent
            );

            extent->num_sectors = (
                num_sectors
            );

            extent->target_type = (
                tf_lp_load_le32(
                    extent_entry + 8
                )
            );

            extent->target_data = (
                tf_lp_load_le64(
                    extent_entry + 12
                )
            );

            extent->target_source = (
                tf_lp_load_le32(
                    extent_entry + 20
                )
            );

            if (
                extent->target_type
                == TREEFORGE_RECOVERY_LP_TARGET_LINEAR
            ) {
                tf_lp_adjusted_table_name(
                    fd,
                    metadata_offset,
                    layout->header_size,
                    &layout->block_devices,
                    extent->target_source,
                    24,
                    36,
                    60,
                    TREEFORGE_RECOVERY_LP_BLOCK_DEVICE_SLOT_SUFFIXED,
                    metadata_slot,
                    extent->block_device_name,
                    sizeof(
                        extent->block_device_name
                    )
                );
            } else {
                tf_copy_string(
                    extent->block_device_name,
                    sizeof(
                        extent->block_device_name
                    ),
                    "-"
                );
            }
        }

        if (
            inventory->partition_count
            >= TREEFORGE_RECOVERY_LP_MAX_PARTITIONS
        ) {
            inventory->partitions_omitted = 1;
            continue;
        }

        struct tf_recovery_logical_partition *record = (
            &inventory->partitions[
                inventory->partition_count++
            ]
        );

        memset(
            record,
            0,
            sizeof(*record)
        );

        record->metadata_slot = (
            metadata_slot
        );

        tf_copy_string(
            record->partition_name,
            sizeof(record->partition_name),
            partition_name
        );

        tf_copy_string(
            record->group_name,
            sizeof(record->group_name),
            (
                group_name[0]
                ? group_name
                : "-"
            )
        );

        char slot = 0;

        tf_partition_slot_candidate(
            partition_name,
            record->canonical_name,
            sizeof(record->canonical_name),
            &slot
        );

        record->slot = slot;

        record->slot_pair = (
            slot == 'a'
            || slot == 'b'
        );

        record->active = (
            record->slot_pair
            && tf_recovery_inventory.active_slot_resolved
            && slot
                == tf_recovery_inventory.active_slot
        );

        record->attributes = attributes;

        record->first_extent_index = (
            first_extent
        );

        record->num_extents = (
            num_extents
        );

        record->sectors = (
            partition_sectors
        );

        if (
            partition_sectors
            <= (
                0xffffffffffffffffULL
                / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            )
        ) {
            record->capacity_bytes = (
                partition_sectors
                * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            );
        }

        /*
         * Read-only acceptance milestone.
         */
        record->writable = 0;
    }

    /*
     * Group accounting uses actual LINEAR/ZERO logical partition sizes
     * already reconstructed from authoritative partition extents.
     */
    for (
        int group_index = 0;
        group_index < inventory->group_count;
        group_index++
    ) {
        struct tf_recovery_lp_group *group = (
            &inventory->groups[group_index]
        );

        group->allocated_bytes = 0;
        group->remaining_bytes = 0;
        group->over_limit = 0;

        for (
            int partition_index = 0;
            partition_index < inventory->partition_count;
            partition_index++
        ) {
            const struct tf_recovery_logical_partition *partition = (
                &inventory->partitions[partition_index]
            );

            if (
                partition->metadata_slot
                    != metadata_slot
                || !tf_string_equal(
                    partition->group_name,
                    group->group_name
                )
            ) {
                continue;
            }

            if (
                partition->capacity_bytes
                > (
                    0xffffffffffffffffULL
                    - group->allocated_bytes
                )
            ) {
                inventory->groups_omitted = 1;
                group->over_limit = 1;
                group->allocated_bytes = (
                    0xffffffffffffffffULL
                );
                break;
            }

            group->allocated_bytes += (
                partition->capacity_bytes
            );
        }

        if (group->unlimited) {
            group->remaining_bytes = (
                0xffffffffffffffffULL
            );
        } else if (
            group->allocated_bytes
            > group->maximum_size_bytes
        ) {
            group->over_limit = 1;
            group->remaining_bytes = 0;
        } else {
            group->remaining_bytes = (
                group->maximum_size_bytes
                - group->allocated_bytes
            );
        }
    }

    /*
     * Derive aligned physical allocation gaps only after the complete
     * authoritative partition/extent graph has been published.
     */
    tf_recovery_lp_publish_free_space(
        inventory
    );
}


static int tf_lp_read_metadata_slot(
    long fd,
    u32 metadata_slot,
    int publish_metadata,
    struct tf_recovery_lp_inventory *inventory,
    struct tf_recovery_lp_slot_result *slot
) {
    memset(
        slot,
        0,
        sizeof(*slot)
    );

    slot->attempted = 1;
    slot->metadata_slot = metadata_slot;

    slot->boot_slot_mapped = (
        metadata_slot <= 1U
    );

    if (slot->boot_slot_mapped) {
        slot->suffix = (
            (char) (
                'a'
                + metadata_slot
            )
        );
    }

    struct tf_recovery_lp_metadata_layout layout;

    u64 primary_offset = (
        tf_lp_primary_metadata_offset(
            inventory,
            metadata_slot
        )
    );

    if (
        tf_lp_validate_metadata_copy(
            fd,
            primary_offset,
            inventory,
            slot,
            &layout
        )
    ) {
        slot->valid = 1;
        slot->primary_valid = 1;
        slot->backup_used = 0;

        if (publish_metadata) {
            tf_lp_publish_metadata(
                fd,
                primary_offset,
                metadata_slot,
                inventory,
                &layout
            );
        }

        return 1;
    }

    u64 backup_offset = (
        tf_lp_backup_metadata_offset(
            inventory,
            metadata_slot
        )
    );

    if (
        tf_lp_validate_metadata_copy(
            fd,
            backup_offset,
            inventory,
            slot,
            &layout
        )
    ) {
        slot->valid = 1;
        slot->primary_valid = 0;
        slot->backup_used = 1;

        if (publish_metadata) {
            tf_lp_publish_metadata(
                fd,
                backup_offset,
                metadata_slot,
                inventory,
                &layout
            );
        }

        return 1;
    }

    slot->valid = 0;

    return 0;
}


static int tf_collect_lp_inventory(
    const struct tf_runtime_partition_inventory *physical,
    struct tf_recovery_lp_inventory *logical
) {
    if (
        !physical
        || !logical
    ) {
        return 0;
    }

    memset(
        logical,
        0,
        sizeof(*logical)
    );

    const struct tf_runtime_partition *super = 0;

    for (
        int index = 0;
        index < physical->partition_count;
        index++
    ) {
        const struct tf_runtime_partition *record = (
            &physical->partitions[index]
        );

        if (
            tf_string_equal(
                record->canonical_name,
                "super"
            )
            || tf_string_equal(
                record->partition_name,
                "super"
            )
        ) {
            super = record;
            break;
        }
    }

    if (!super) {
        logical->error_stage = 1;
        return 0;
    }

    logical->super_found = 1;

    logical->super_major = (
        super->major_number
    );

    logical->super_minor = (
        super->minor_number
    );

    logical->super_capacity_bytes = (
        super->capacity_bytes
    );

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            super->major_number,
            super->minor_number,
            &encoded_device
        )
    ) {
        logical->error_stage = 2;
        return 0;
    }

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        S_IFBLK | 0400,
        (long) encoded_device
    );

    if (node_result < 0) {
        logical->error_stage = 3;
        logical->error_errno = (
            (u64) (-node_result)
        );

        return 0;
    }

    logical->node_created = 1;

    long fd = tf_open(
        TREEFORGE_RECOVERY_LP_NODE_PATH,
        O_RDONLY
    );

    if (fd < 0) {
        logical->error_stage = 4;
        logical->error_errno = (
            (u64) (-fd)
        );

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            0
        );

        return 0;
    }

    logical->open_succeeded = 1;

    if (
        !tf_lp_read_geometry(
            fd,
            logical
        )
    ) {
        tf_close(
            fd
        );

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            0
        );

        return 0;
    }

    if (
        physical->active_slot_resolved
        && (
            physical->active_slot == 'a'
            || physical->active_slot == 'b'
        )
    ) {
        logical->authoritative_slot_resolved = 1;

        logical->authoritative_metadata_slot = (
            physical->active_slot == 'a'
            ? 0U
            : 1U
        );
    }

    u32 slots_to_read = (
        logical->metadata_slot_count
    );

    if (
        slots_to_read
        > TREEFORGE_RECOVERY_LP_MAX_METADATA_SLOTS
    ) {
        slots_to_read = (
            TREEFORGE_RECOVERY_LP_MAX_METADATA_SLOTS
        );

        logical->metadata_slots_omitted = 1;
    }

    for (
        u32 metadata_slot = 0;
        metadata_slot < slots_to_read;
        metadata_slot++
    ) {
        logical->metadata_slots_read++;

        int authoritative = (
            logical->authoritative_slot_resolved
            && metadata_slot
                == logical->authoritative_metadata_slot
        );

        if (
            tf_lp_read_metadata_slot(
                fd,
                metadata_slot,
                authoritative,
                logical,
                &logical->slots[
                    metadata_slot
                ]
            )
        ) {
            logical->metadata_slots_valid++;

            if (authoritative) {
                logical->authoritative_metadata_valid = 1;

                logical->virtual_ab = (
                    logical->slots[
                        metadata_slot
                    ].header_flags
                    & TREEFORGE_RECOVERY_LP_HEADER_VIRTUAL_AB_DEVICE
                ) ? 1 : 0;
            }
        }
    }

    if (
        logical->metadata_slots_valid == 0
        && logical->error_stage == 0
    ) {
        logical->error_stage = 6;
    }

    if (
        (
            !logical->authoritative_slot_resolved
            || logical->authoritative_metadata_slot
                >= logical->metadata_slot_count
            || !logical->authoritative_metadata_valid
        )
        && logical->error_stage == 0
    ) {
        /*
         * Valid auxiliary metadata is not sufficient for destructive
         * planning. TreeForge needs the metadata selected by the actual
         * Android boot slot.
         */
        logical->error_stage = 8;
    }

    tf_close(
        fd
    );

    long cleanup_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    if (
        cleanup_result < 0
        && cleanup_result != -2
        && logical->error_stage == 0
    ) {
        logical->error_stage = 7;
        logical->error_errno = (
            (u64) (-cleanup_result)
        );
    }

    return (
        logical->geometry_resolved
        && logical->metadata_slots_valid > 0
        && logical->authoritative_slot_resolved
        && logical->authoritative_metadata_valid
    );
}



static int tf_lp_hash_linear_extent(
    long fd,
    u64 physical_sector,
    u64 num_sectors,
    u64 super_capacity_bytes,
    struct tf_sha256_context *context,
    u64 *bytes_read,
    u64 *error_errno
) {
    if (
        fd < 0
        || !context
        || !bytes_read
        || !error_errno
    ) {
        return 0;
    }

    if (
        physical_sector
        > (
            0xffffffffffffffffULL
            / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        )
        || num_sectors
        > (
            0xffffffffffffffffULL
            / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
        )
    ) {
        return 0;
    }

    u64 offset = (
        physical_sector
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    u64 length = (
        num_sectors
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    if (
        offset > super_capacity_bytes
        || length
            > (
                super_capacity_bytes
                - offset
            )
        || offset
            > 0x7fffffffffffffffULL
    ) {
        return 0;
    }

    long seek_result = tf_syscall3(
        SYS_LSEEK,
        fd,
        (long) offset,
        SEEK_SET
    );

    if (seek_result < 0) {
        *error_errno = (
            (u64) (-seek_result)
        );

        return 0;
    }

    if (
        (u64) seek_result
        != offset
    ) {
        return 0;
    }

    unsigned char buffer[4096];

    u64 remaining = length;

    while (remaining > 0) {
        usize requested = (
            remaining < (u64) sizeof(buffer)
            ? (usize) remaining
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) buffer,
            requested
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount == 0) {
            return 0;
        }

        tf_sha256_update(
            context,
            buffer,
            (usize) amount
        );

        *bytes_read += (
            (u64) amount
        );

        remaining -= (
            (u64) amount
        );
    }

    return 1;
}


static int tf_lp_hash_zero_extent(
    u64 num_sectors,
    struct tf_sha256_context *context,
    u64 *bytes_read
) {
    if (
        !context
        || !bytes_read
        || num_sectors
            > (
                0xffffffffffffffffULL
                / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            )
    ) {
        return 0;
    }

    u64 remaining = (
        num_sectors
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    unsigned char zeros[4096];

    memset(
        zeros,
        0,
        sizeof(zeros)
    );

    while (remaining > 0) {
        usize amount = (
            remaining < (u64) sizeof(zeros)
            ? (usize) remaining
            : sizeof(zeros)
        );

        tf_sha256_update(
            context,
            zeros,
            amount
        );

        *bytes_read += (
            (u64) amount
        );

        remaining -= (
            (u64) amount
        );
    }

    return 1;
}


static const struct tf_recovery_logical_extent *
tf_lp_find_partition_extent(
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_partition *partition,
    u32 partition_extent_index,
    int *matches
) {
    if (
        !inventory
        || !partition
        || !matches
    ) {
        return 0;
    }

    *matches = 0;

    const struct tf_recovery_logical_extent *found = 0;

    for (
        int index = 0;
        index < inventory->extent_count;
        index++
    ) {
        const struct tf_recovery_logical_extent *extent = (
            &inventory->extents[index]
        );

        if (
            extent->metadata_slot
                != partition->metadata_slot
            || extent->partition_extent_index
                != partition_extent_index
            || !tf_string_equal(
                extent->partition_name,
                partition->partition_name
            )
        ) {
            continue;
        }

        found = extent;
        (*matches)++;
    }

    return found;
}


static void tf_run_requested_lp_read_probe(
    const struct tf_recovery_lp_inventory *inventory,
    struct tf_recovery_lp_read_probe_result *result
) {
    memset(
        result,
        0,
        sizeof(*result)
    );

    char request[256];

    long amount = tf_read_path(
        TREEFORGE_RECOVERY_LP_READ_PROBE_REQUEST_PATH,
        request,
        sizeof(request)
    );

    if (amount <= 0) {
        return;
    }

    result->requested = 1;

    /*
     * One-shot control contract: consume the request before touching
     * super so the operation cannot repeat across Recovery boots.
     */
    long unlink_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_LP_READ_PROBE_REQUEST_PATH,
        0
    );

    if (unlink_result < 0) {
        result->error_stage = 1;
        result->error_errno = (
            (u64) (-unlink_result)
        );
        return;
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        !tf_parse_read_probe_name(
            request,
            (usize) amount,
            result->requested_partition_name,
            sizeof(
                result->requested_partition_name
            )
        )
    ) {
        result->error_stage = 1;
        return;
    }

    if (
        !inventory
        || !inventory->geometry_resolved
        || !inventory->authoritative_slot_resolved
        || !inventory->authoritative_metadata_valid
    ) {
        result->error_stage = 2;
        return;
    }

    const struct tf_recovery_logical_partition *target = 0;
    int target_count = 0;

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        const struct tf_recovery_logical_partition *record = (
            &inventory->partitions[index]
        );

        if (
            !tf_string_equal(
                record->partition_name,
                result->requested_partition_name
            )
        ) {
            continue;
        }

        target = record;
        target_count++;
    }

    if (
        target_count != 1
        || !target
    ) {
        result->error_stage = 2;
        return;
    }

    result->target_resolved = 1;

    tf_copy_string(
        result->target_partition_name,
        sizeof(
            result->target_partition_name
        ),
        target->partition_name
    );

    result->target_slot = (
        target->slot
    );

    result->target_active = (
        target->active
    );

    result->metadata_slot = (
        target->metadata_slot
    );

    result->expected_extents = (
        target->num_extents
    );

    result->bytes_expected = (
        target->capacity_bytes
    );

    /*
     * Empty LP allocations are valid metadata, but there are no bytes
     * to reconstruct. Keep that distinct from an extent-walk success.
     */
    if (
        target->num_extents == 0
        || target->capacity_bytes == 0
    ) {
        result->error_stage = 3;
        return;
    }

    if (
        target->metadata_slot
        != inventory->authoritative_metadata_slot
    ) {
        result->error_stage = 3;
        return;
    }

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            inventory->super_major,
            inventory->super_minor,
            &encoded_device
        )
    ) {
        result->error_stage = 4;
        return;
    }

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        S_IFBLK | 0400,
        (long) encoded_device
    );

    if (node_result < 0) {
        result->error_stage = 5;
        result->error_errno = (
            (u64) (-node_result)
        );
        return;
    }

    result->super_node_created = 1;

    long fd = tf_open(
        TREEFORGE_RECOVERY_LP_NODE_PATH,
        O_RDONLY
    );

    if (fd < 0) {
        result->error_stage = 6;
        result->error_errno = (
            (u64) (-fd)
        );

        goto lp_read_probe_cleanup;
    }

    result->super_open_succeeded = 1;

    struct tf_sha256_context context;

    tf_sha256_init(
        &context
    );

    for (
        u32 local_extent = 0;
        local_extent < target->num_extents;
        local_extent++
    ) {
        int extent_matches = 0;

        const struct tf_recovery_logical_extent *extent = (
            tf_lp_find_partition_extent(
                inventory,
                target,
                local_extent,
                &extent_matches
            )
        );

        if (
            extent_matches != 1
            || !extent
        ) {
            result->error_stage = 7;
            goto lp_read_probe_close;
        }

        /*
         * This first hardware path supports the exact topology we have
         * discovered: LINEAR extents on the canonical super block device,
         * plus the AOSP ZERO target type.
         *
         * Multi-device super layouts remain explicit unsupported evidence
         * rather than being guessed.
         */
        if (
            extent->target_type
            == TREEFORGE_RECOVERY_LP_TARGET_LINEAR
        ) {
            if (
                extent->target_source != 0
                || !tf_string_equal(
                    extent->block_device_name,
                    "super"
                )
            ) {
                result->error_stage = 8;
                goto lp_read_probe_close;
            }

            u64 read_errno = 0;

            if (
                !tf_lp_hash_linear_extent(
                    fd,
                    extent->target_data,
                    extent->num_sectors,
                    inventory->super_capacity_bytes,
                    &context,
                    &result->bytes_read,
                    &read_errno
                )
            ) {
                result->error_stage = 9;
                result->error_errno = read_errno;
                goto lp_read_probe_close;
            }

            result->linear_extents++;
        } else if (
            extent->target_type
            == TREEFORGE_RECOVERY_LP_TARGET_ZERO
        ) {
            if (
                !tf_lp_hash_zero_extent(
                    extent->num_sectors,
                    &context,
                    &result->bytes_read
                )
            ) {
                result->error_stage = 10;
                goto lp_read_probe_close;
            }

            result->zero_extents++;
        } else {
            result->error_stage = 8;
            goto lp_read_probe_close;
        }

        result->extents_read++;
    }

    result->extent_map_complete = (
        result->extents_read
            == result->expected_extents
        && result->bytes_read
            == result->bytes_expected
    );

    if (!result->extent_map_complete) {
        result->error_stage = 11;
        goto lp_read_probe_close;
    }

    {
        unsigned char digest[32];

        tf_sha256_final(
            &context,
            digest
        );

        tf_sha256_hex(
            digest,
            result->sha256
        );
    }

    result->hash_succeeded = 1;
    result->error_stage = 0;
    result->error_errno = 0;

lp_read_probe_close:
    tf_close(
        fd
    );

lp_read_probe_cleanup:
    {
        long cleanup_result = tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            0
        );

        if (
            cleanup_result == 0
            || cleanup_result == -2
        ) {
            result->super_node_created = 0;
        } else if (
            result->error_stage == 0
        ) {
            result->error_stage = 12;
            result->error_errno = (
                (u64) (-cleanup_result)
            );
        }
    }
}



static int tf_recovery_flash_policy_for_canonical(
    const char *canonical_name
) {
    if (!canonical_name) {
        return TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL;
    }

    if (
        tf_string_equal(
            canonical_name,
            "abl"
        )
        || tf_string_equal(
            canonical_name,
            "bl1"
        )
        || tf_string_equal(
            canonical_name,
            "bl2"
        )
        || tf_string_equal(
            canonical_name,
            "bl31"
        )
        || tf_string_equal(
            canonical_name,
            "pbl"
        )
        || tf_string_equal(
            canonical_name,
            "tzsw"
        )
        || tf_string_equal(
            canonical_name,
            "gsa"
        )
        || tf_string_equal(
            canonical_name,
            "ldfw"
        )
        || tf_string_equal(
            canonical_name,
            "dpm"
        )
        || tf_string_equal(
            canonical_name,
            "dram_train"
        )
    ) {
        return (
            TREEFORGE_RECOVERY_FLASH_POLICY_BLOCKED_BOOTLOADER
        );
    }

    return TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL;
}


static struct tf_recovery_flash_target *
tf_recovery_append_flash_target(
    struct tf_recovery_flash_target_inventory *inventory
) {
    if (!inventory) {
        return 0;
    }

    if (
        inventory->target_count
        >= TREEFORGE_RECOVERY_MAX_FLASH_TARGETS
    ) {
        inventory->targets_omitted = 1;
        return 0;
    }

    struct tf_recovery_flash_target *target = (
        &inventory->targets[
            inventory->target_count++
        ]
    );

    memset(
        target,
        0,
        sizeof(*target)
    );

    /*
     * Unified discovery remains read-only.
     */
    target->writable = 0;

    return target;
}


static void tf_collect_unified_flash_targets(
    const struct tf_runtime_partition_inventory *physical,
    const struct tf_recovery_lp_inventory *logical,
    struct tf_recovery_flash_target_inventory *unified
) {
    if (!unified) {
        return;
    }

    memset(
        unified,
        0,
        sizeof(*unified)
    );

    if (!physical) {
        return;
    }

    if (
        physical->active_slot_resolved
        && (
            physical->active_slot == 'a'
            || physical->active_slot == 'b'
        )
    ) {
        unified->active_slot_resolved = 1;
        unified->active_slot = (
            physical->active_slot
        );

        unified->default_install_slot_resolved = 1;
        unified->default_install_slot = (
            physical->active_slot == 'a'
            ? 'b'
            : 'a'
        );
    }

    /*
     * Every discovered physical A/B sibling is represented.
     *
     * This deliberately includes boot-chain and firmware A/B partitions
     * rather than maintaining another small hard-coded list.
     *
     * Non-slotted physical partitions are not placed into the normal
     * inactive-slot installer yet. They can later receive a separate,
     * explicit advanced/no-slot policy.
     */
    for (
        int index = 0;
        index < physical->partition_count;
        index++
    ) {
        const struct tf_runtime_partition *record = (
            &physical->partitions[index]
        );

        if (
            !record->slot_pair
            || (
                record->slot != 'a'
                && record->slot != 'b'
            )
        ) {
            continue;
        }

        struct tf_recovery_flash_target *target = (
            tf_recovery_append_flash_target(
                unified
            )
        );

        if (!target) {
            continue;
        }

        target->target_type = (
            TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        );

        target->flash_policy = (
            tf_recovery_flash_policy_for_canonical(
                record->canonical_name
            )
        );

        tf_copy_string(
            target->partition_name,
            sizeof(target->partition_name),
            record->partition_name
        );

        tf_copy_string(
            target->canonical_name,
            sizeof(target->canonical_name),
            record->canonical_name
        );

        target->slot = record->slot;
        target->slot_pair = 1;

        target->active = (
            unified->active_slot_resolved
            && record->slot
                == unified->active_slot
        );

        target->selectable = (
            unified->active_slot_resolved
            && record->slot
                != unified->active_slot
            && target->flash_policy
                == TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        );

        target->capacity_bytes = (
            record->capacity_bytes
        );

        target->physical_major = (
            record->major_number
        );

        target->physical_minor = (
            record->minor_number
        );

        target->allocation_present = (
            record->capacity_bytes > 0
        );

        if (
            target->flash_policy
            == TREEFORGE_RECOVERY_FLASH_POLICY_BLOCKED_BOOTLOADER
        ) {
            unified->bootloader_blocked_count++;
        }

        unified->physical_count++;

        if (target->selectable) {
            unified->inactive_selectable_count++;
        } else if (target->active) {
            unified->active_blocked_count++;
        }
    }

    /*
     * Publish logical targets only when the authoritative LP surface itself
     * passed its hardware-enforced selection rules.
     */
    if (
        !logical
        || !logical->geometry_resolved
        || !logical->authoritative_slot_resolved
        || !logical->authoritative_metadata_valid
    ) {
        return;
    }

    for (
        int index = 0;
        index < logical->partition_count;
        index++
    ) {
        const struct tf_recovery_logical_partition *record = (
            &logical->partitions[index]
        );

        if (
            !record->slot_pair
            || (
                record->slot != 'a'
                && record->slot != 'b'
            )
        ) {
            continue;
        }

        struct tf_recovery_flash_target *target = (
            tf_recovery_append_flash_target(
                unified
            )
        );

        if (!target) {
            continue;
        }

        target->target_type = (
            TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        );

        target->flash_policy = (
            TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        );

        tf_copy_string(
            target->partition_name,
            sizeof(target->partition_name),
            record->partition_name
        );

        tf_copy_string(
            target->canonical_name,
            sizeof(target->canonical_name),
            record->canonical_name
        );

        target->slot = record->slot;
        target->slot_pair = 1;

        target->active = (
            unified->active_slot_resolved
            && record->slot
                == unified->active_slot
        );

        target->selectable = (
            unified->active_slot_resolved
            && record->slot
                != unified->active_slot
        );

        target->capacity_bytes = (
            record->capacity_bytes
        );

        target->metadata_slot = (
            record->metadata_slot
        );

        target->first_extent_index = (
            record->first_extent_index
        );

        target->num_extents = (
            record->num_extents
        );

        target->attributes = (
            record->attributes
        );

        target->allocation_present = (
            record->num_extents > 0
            && record->capacity_bytes > 0
        );

        unified->logical_count++;

        if (target->selectable) {
            unified->inactive_selectable_count++;
        } else if (target->active) {
            unified->active_blocked_count++;
        }
    }
}


static int tf_collect_inventory(
    struct tf_runtime_partition_inventory *inventory
) {
    if (!inventory) {
        return 0;
    }

    memset(
        inventory,
        0,
        sizeof(*inventory)
    );

    char active_slot = (
        tf_resolve_active_slot()
    );

    if (
        active_slot == 'a'
        || active_slot == 'b'
    ) {
        inventory->active_slot_resolved = 1;
        inventory->active_slot = active_slot;
    }

    /*
     * This is an ordinary sysfs directory walk. Nonblocking mode is
     * unnecessary and must not become part of TreeForge's runtime
     * partition-discovery contract.
     */
    long directory_fd = tf_open(
        "/sys/class/block",
        O_RDONLY
        | O_DIRECTORY
    );

    if (directory_fd < 0) {
        inventory->enumeration_error = 1;
        inventory->enumeration_stage = 1;
        inventory->enumeration_errno = (
            (u64) (
                -directory_fd
            )
        );
        return 0;
    }

    unsigned char directory_buffer[4096];

    for (;;) {
        long amount = tf_syscall3(
            SYS_GETDENTS64,
            directory_fd,
            (long) directory_buffer,
            sizeof(directory_buffer)
        );

        if (amount < 0) {
            inventory->enumeration_error = 1;
            inventory->enumeration_stage = 2;
            inventory->enumeration_errno = (
                (u64) (
                    -amount
                )
            );
            break;
        }

        if (amount == 0) {
            break;
        }

        usize offset = 0;

        while (
            offset < (usize) amount
        ) {
            struct tf_linux_dirent64 *entry = (
                (struct tf_linux_dirent64 *)
                (
                    directory_buffer
                    + offset
                )
            );

            usize name_offset = (
                (usize) (
                    entry->d_name
                    - (char *) entry
                )
            );

            if (
                entry->d_reclen <= name_offset
                || offset
                    + entry->d_reclen
                    > (usize) amount
            ) {
                inventory->enumeration_error = 1;
                inventory->enumeration_stage = 3;
                inventory->enumeration_errno = 0;
                offset = (usize) amount;
                break;
            }

            if (
                !tf_string_equal(
                    entry->d_name,
                    "."
                )
                && !tf_string_equal(
                    entry->d_name,
                    ".."
                )
            ) {
                tf_collect_partition(
                    entry->d_name,
                    inventory
                );
            }

            offset += entry->d_reclen;
        }
    }

    tf_close(
        directory_fd
    );

    tf_resolve_slot_pairs(
        inventory
    );

    /*
     * Runtime topology is now complete. Compare live identities only
     * after A/B sibling pairing has produced canonical base names.
     */
    tf_apply_canonical_expectations(
        inventory
    );

    /*
     * Logical-partition discovery is read-only and additive. A malformed or
     * unavailable super metadata surface is reported independently and never
     * weakens the already-accepted physical partition inventory.
     */
    tf_collect_lp_inventory(
        inventory,
        &tf_recovery_lp_inventory
    );

    /*
     * Build the generic Recovery partition-image target surface only after
     * both physical topology and authoritative LP topology are known.
     */
    tf_collect_unified_flash_targets(
        inventory,
        &tf_recovery_lp_inventory,
        &tf_recovery_flash_targets
    );

    return (
        inventory->enumeration_error
        ? 0
        : 1
    );
}


static usize tf_append_text(
    char *buffer,
    usize capacity,
    usize position,
    const char *text
) {
    if (
        !buffer
        || !text
        || position >= capacity
    ) {
        return position;
    }

    for (
        usize index = 0;
        text[index] != '\0';
        index++
    ) {
        if (
            position + 1
            >= capacity
        ) {
            break;
        }

        buffer[position++] = text[index];
    }

    buffer[position] = '\0';

    return position;
}


static usize tf_append_u64(
    char *buffer,
    usize capacity,
    usize position,
    u64 value
) {
    char digits[32];
    usize count = 0;

    if (value == 0) {
        return tf_append_text(
            buffer,
            capacity,
            position,
            "0"
        );
    }

    while (
        value > 0
        && count < sizeof(digits)
    ) {
        digits[count++] = (
            '0'
            + (
                value % 10ULL
            )
        );

        value /= 10ULL;
    }

    while (count > 0) {
        count--;

        char character[2];

        character[0] = digits[count];
        character[1] = '\0';

        position = tf_append_text(
            buffer,
            capacity,
            position,
            character
        );
    }

    return position;
}


static int tf_write_buffer(
    long fd,
    const char *buffer,
    usize length
) {
    if (
        fd < 0
        || !buffer
    ) {
        return 0;
    }

    usize offset = 0;

    while (
        offset < length
    ) {
        long written = tf_syscall3(
            SYS_WRITE,
            fd,
            (long) (
                buffer
                + offset
            ),
            (long) (
                length
                - offset
            )
        );

        if (written <= 0) {
            return 0;
        }

        offset += (
            (usize) written
        );
    }

    return 1;
}



static void tf_emit_read_probe_fd(
    long fd,
    const struct tf_recovery_read_probe_result *result
) {
    if (
        fd < 0
        || !result
    ) {
        return;
    }

    char line[1024];
    usize position = 0;

    line[0] = '\0';

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "TreeForge recovery: read_probe requested="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->requested
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " name="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->requested
            ? result->requested_canonical_name
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target_resolved="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_resolved
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->target_resolved
            ? result->target_partition_name
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " slot="
    );

    if (result->target_slot) {
        char slot[2] = {
            result->target_slot,
            '\0',
        };

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            slot
        );
    } else {
        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "-"
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " active="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_active
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " major="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->target_major
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " minor="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->target_minor
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " bytes_requested="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->bytes_requested
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " bytes_read="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->bytes_read
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " node="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->node_created
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " open="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->open_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " hash="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->hash_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " match="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->hash_match
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " error_stage="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->error_stage
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " errno="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->error_errno
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " expected_sha256="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->expected_sha256[0]
            ? result->expected_sha256
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " actual_sha256="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->actual_sha256[0]
            ? result->actual_sha256
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "\n"
    );

    tf_write_buffer(
        fd,
        line,
        position
    );
}



static void tf_emit_flash_plan_fd(
    long fd,
    const struct tf_recovery_flash_plan_result *result
) {
    if (
        fd < 0
        || !result
    ) {
        return;
    }

    char line[2048];
    usize position = 0;

    line[0] = '\0';

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "TreeForge recovery: flash_plan requested="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->requested
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " name="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->requested
            ? result->requested_canonical_name
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target_resolved="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_resolved
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->target_resolved
            ? result->target_partition_name
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " slot="
    );

    if (result->target_slot) {
        char slot[2] = {
            result->target_slot,
            '\0',
        };

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            slot
        );
    } else {
        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "-"
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " active="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_active
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " major="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->target_major
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " minor="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->target_minor
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target_bytes="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->target_capacity_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " canonical_bytes="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->canonical_image_size_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " source_stream="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_streaming
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " manifest_valid="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_manifest_valid
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " stream_ready="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_stream_ready
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " source_open="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_open_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " source_hash="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_hash_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " source_oversized="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_oversized
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " source_bytes="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->source_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " size_match="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_size_matches_canonical
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " fits="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_fits_target
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " canonical_match="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_matches_canonical
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target_ready="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_ready
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " plan_ready="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->plan_ready
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " authorization_requested="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->authorization_requested
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " authorization_match="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->authorization_match
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " activation_eligible="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->activation_eligible
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " authorized="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->authorized
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " source_revalidated="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->source_revalidated
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target_open="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_open_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " bytes_written="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->bytes_written
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " write_synced="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->write_synced
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " stream_hash="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->streamed_hash_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " streamed_sha256="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->streamed_sha256[0]
            ? result->streamed_sha256
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " verification_open="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->verification_open_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " verification_hash="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->verification_hash_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " verification_match="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->verification_match
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " written="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->written
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " error_stage="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->error_stage
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " errno="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->error_errno
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " canonical_sha256="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->canonical_sha256[0]
            ? result->canonical_sha256
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " source_sha256="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->source_sha256[0]
            ? result->source_sha256
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " verified_sha256="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->verified_sha256[0]
            ? result->verified_sha256
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "\n"
    );

    tf_write_buffer(
        fd,
        line,
        position
    );
}





static void tf_emit_flash_targets_fd(
    long fd,
    const struct tf_recovery_flash_target_inventory *inventory
) {
    if (
        fd < 0
        || !inventory
    ) {
        return;
    }

    char line[1024];
    usize position = 0;

    position = tf_append_text(
        line,
        sizeof(line),
        0,
        "TreeForge recovery: flash_targets active_slot="
    );

    if (inventory->active_slot_resolved) {
        char slot[2] = {
            inventory->active_slot,
            '\0',
        };

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            slot
        );
    } else {
        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "unresolved"
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " default_install_slot="
    );

    if (inventory->default_install_slot_resolved) {
        char slot[2] = {
            inventory->default_install_slot,
            '\0',
        };

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            slot
        );
    } else {
        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "-"
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " targets="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->target_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " physical="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->physical_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " logical="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->logical_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " selectable="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->inactive_selectable_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " active_blocked="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->active_blocked_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " bootloader_blocked="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->bootloader_blocked_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " omitted="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->targets_omitted
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " writable=0\n"
    );

    tf_write_buffer(
        fd,
        line,
        position
    );

    for (
        int index = 0;
        index < inventory->target_count;
        index++
    ) {
        const struct tf_recovery_flash_target *target = (
            &inventory->targets[index]
        );

        position = tf_append_text(
            line,
            sizeof(line),
            0,
            "TreeForge recovery: flash_target type="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            (
                target->target_type
                    == TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
                ? "physical"
                : "logical"
            )
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " policy="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            (
                target->flash_policy
                    == TREEFORGE_RECOVERY_FLASH_POLICY_BLOCKED_BOOTLOADER
                ? "blocked_bootloader"
                : "normal"
            )
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " name="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            target->partition_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " canonical="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            target->canonical_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " slot="
        );

        if (
            target->slot == 'a'
            || target->slot == 'b'
        ) {
            char slot[2] = {
                target->slot,
                '\0',
            };

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                slot
            );
        } else {
            position = tf_append_text(
                line,
                sizeof(line),
                position,
                "-"
            );
        }

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " active="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) target->active
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " selectable="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) target->selectable
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            target->capacity_bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " allocated="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) target->allocation_present
        );

        if (
            target->target_type
            == TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        ) {
            position = tf_append_text(
                line,
                sizeof(line),
                position,
                " major="
            );

            position = tf_append_u64(
                line,
                sizeof(line),
                position,
                target->physical_major
            );

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                " minor="
            );

            position = tf_append_u64(
                line,
                sizeof(line),
                position,
                target->physical_minor
            );

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                " metadata_slot=- extents=0 attributes=0"
            );
        } else {
            position = tf_append_text(
                line,
                sizeof(line),
                position,
                " major=0 minor=0 metadata_slot="
            );

            position = tf_append_u64(
                line,
                sizeof(line),
                position,
                target->metadata_slot
            );

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                " extents="
            );

            position = tf_append_u64(
                line,
                sizeof(line),
                position,
                target->num_extents
            );

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                " attributes="
            );

            position = tf_append_u64(
                line,
                sizeof(line),
                position,
                target->attributes
            );
        }

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " writable=0\n"
        );

        tf_write_buffer(
            fd,
            line,
            position
        );
    }
}


static void tf_emit_lp_read_probe_fd(
    long fd,
    const struct tf_recovery_lp_read_probe_result *result
) {
    if (
        fd < 0
        || !result
    ) {
        return;
    }

    char line[1024];

    usize position = tf_append_text(
        line,
        sizeof(line),
        0,
        "TreeForge recovery: lp_read_probe requested="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->requested
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " name="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->requested_partition_name[0]
            ? result->requested_partition_name
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target_resolved="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_resolved
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " target="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->target_partition_name[0]
            ? result->target_partition_name
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " slot="
    );

    if (
        result->target_slot == 'a'
        || result->target_slot == 'b'
    ) {
        char slot[2] = {
            result->target_slot,
            '\0',
        };

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            slot
        );
    } else {
        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "-"
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " active="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->target_active
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " metadata_slot="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->metadata_slot
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " expected_extents="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->expected_extents
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " extents_read="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->extents_read
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " linear="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->linear_extents
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " zero="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->zero_extents
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " bytes_expected="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->bytes_expected
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " bytes_read="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->bytes_read
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " map_complete="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->extent_map_complete
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " node="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->super_node_created
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " open="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->super_open_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " hash="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->hash_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " error_stage="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) result->error_stage
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " errno="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        result->error_errno
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " sha256="
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        (
            result->sha256[0]
            ? result->sha256
            : "-"
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "\n"
    );

    tf_write_buffer(
        fd,
        line,
        position
    );
}



static void tf_emit_lp_read_probe_report(
    const struct tf_recovery_lp_read_probe_result *result
) {
    if (
        !result
        || !result->requested
    ) {
        return;
    }

    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_LP_READ_PROBE_REPORT_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return;
    }

    static const char version[] =
        "treeforge-recovery-lp-read-probe-v1\n";

    tf_write_buffer(
        fd,
        version,
        sizeof(version) - 1
    );

    tf_emit_lp_read_probe_fd(
        fd,
        result
    );

    tf_syscall1(
        SYS_FSYNC,
        fd
    );

    tf_close(
        fd
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );
}


static void tf_emit_lp_inventory_fd(
    long fd,
    const struct tf_recovery_lp_inventory *inventory
) {
    if (
        fd < 0
        || !inventory
    ) {
        return;
    }

    char line[1024];
    usize position = 0;

    position = tf_append_text(
        line,
        sizeof(line),
        0,
        "TreeForge recovery: lp_geometry super_found="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->super_found
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " major="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->super_major
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " minor="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->super_minor
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " bytes="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->super_capacity_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " data_region="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->super_data_region_resolved
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " first_logical_sector="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->super_first_logical_sector
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " alignment="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->super_alignment_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " alignment_offset="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->super_alignment_offset_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " device_size="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->super_device_size_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " node="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->node_created
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " open="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->open_succeeded
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " resolved="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->geometry_resolved
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " primary="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->geometry_primary_valid
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " backup="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->geometry_backup_used
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " metadata_max_size="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->metadata_max_size
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " metadata_slots="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->metadata_slot_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " logical_block_size="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->logical_block_size
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " authoritative_slot="
    );

    if (inventory->authoritative_slot_resolved) {
        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            inventory->authoritative_metadata_slot
        );
    } else {
        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "-"
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " authoritative_valid="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->authoritative_metadata_valid
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " virtual_ab="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->virtual_ab
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " slots_read="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->metadata_slots_read
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " slots_valid="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->metadata_slots_valid
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " slots_omitted="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->metadata_slots_omitted
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " partitions="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->partition_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " partitions_omitted="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->partitions_omitted
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " extents="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->extent_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " extents_omitted="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->extents_omitted
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " error_stage="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->error_stage
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " errno="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->error_errno
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "\n"
    );

    tf_write_buffer(
        fd,
        line,
        position
    );

    for (
        int index = 0;
        index < inventory->metadata_slots_read
            && index
                < TREEFORGE_RECOVERY_LP_MAX_METADATA_SLOTS;
        index++
    ) {
        const struct tf_recovery_lp_slot_result *slot = (
            &inventory->slots[index]
        );

        position = tf_append_text(
            line,
            sizeof(line),
            0,
            "TreeForge recovery: lp_slot index="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->metadata_slot
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " suffix="
        );

        if (slot->suffix) {
            char suffix[2] = {
                slot->suffix,
                '\0',
            };

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                suffix
            );
        } else {
            position = tf_append_text(
                line,
                sizeof(line),
                position,
                "-"
            );
        }

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " boot_slot_mapped="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) slot->boot_slot_mapped
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " authoritative="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (
                inventory->authoritative_slot_resolved
                && slot->metadata_slot
                    == inventory->authoritative_metadata_slot
            ) ? 1ULL : 0ULL
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " valid="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) slot->valid
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " primary="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) slot->primary_valid
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " backup_used="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) slot->backup_used
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " major_version="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->major_version
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " minor_version="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->minor_version
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " header_size="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->header_size
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " tables_size="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->tables_size
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " header_flags="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->header_flags
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " virtual_ab="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (
                slot->header_flags
                & TREEFORGE_RECOVERY_LP_HEADER_VIRTUAL_AB_DEVICE
            ) ? 1ULL : 0ULL
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " partitions="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->partition_count
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " extents="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->extent_count
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " groups="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->group_count
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " block_devices="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->block_device_count
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " error_stage="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) slot->error_stage
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " errno="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            slot->error_errno
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "\n"
        );

        tf_write_buffer(
            fd,
            line,
            position
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        0,
        "TreeForge recovery: lp_allocation free_resolved="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->free_space_resolved
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " overlap="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->free_space_overlap
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " groups="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->group_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " groups_omitted="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->groups_omitted
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " free_ranges="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->free_range_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " ranges_omitted="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->free_ranges_omitted
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " free_sectors="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->free_sectors
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " free_bytes="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->free_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " largest_start="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->largest_free_start_sector
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " largest_sectors="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->largest_free_sectors
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " largest_bytes="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->largest_free_bytes
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "\n"
    );

    tf_write_buffer(
        fd,
        line,
        position
    );

    for (
        int index = 0;
        index < inventory->group_count;
        index++
    ) {
        const struct tf_recovery_lp_group *group = (
            &inventory->groups[index]
        );

        position = tf_append_text(
            line,
            sizeof(line),
            0,
            "TreeForge recovery: lp_group metadata_slot="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            group->metadata_slot
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " table_index="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            group->table_group_index
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " name="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            group->group_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " flags="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            group->flags
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " unlimited="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) group->unlimited
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " maximum_bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            group->maximum_size_bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " allocated_bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            group->allocated_bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " remaining_bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            group->remaining_bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " over_limit="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) group->over_limit
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "\n"
        );

        tf_write_buffer(
            fd,
            line,
            position
        );
    }

    for (
        int index = 0;
        index < inventory->free_range_count;
        index++
    ) {
        const struct tf_recovery_lp_free_range *range = (
            &inventory->free_ranges[index]
        );

        position = tf_append_text(
            line,
            sizeof(line),
            0,
            "TreeForge recovery: lp_free_range index="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) index
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " start_sector="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            range->start_sector
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " end_sector="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            range->end_sector
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " sectors="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            range->num_sectors
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            range->bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "\n"
        );

        tf_write_buffer(
            fd,
            line,
            position
        );
    }

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        const struct tf_recovery_logical_partition *record = (
            &inventory->partitions[index]
        );

        position = tf_append_text(
            line,
            sizeof(line),
            0,
            "TreeForge recovery: logical_partition metadata_slot="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->metadata_slot
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " name="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            record->partition_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " canonical="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            record->canonical_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " slot="
        );

        if (record->slot_pair) {
            char slot[2] = {
                record->slot,
                '\0',
            };

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                slot
            );
        } else {
            position = tf_append_text(
                line,
                sizeof(line),
                position,
                "-"
            );
        }

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " active="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) record->active
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " group="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            record->group_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " attributes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->attributes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " readonly="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (
                record->attributes
                & TREEFORGE_RECOVERY_LP_ATTR_READONLY
            ) ? 1ULL : 0ULL
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " disabled="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (
                record->attributes
                & TREEFORGE_RECOVERY_LP_ATTR_DISABLED
            ) ? 1ULL : 0ULL
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " first_extent="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->first_extent_index
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " extents="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->num_extents
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " sectors="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->sectors
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->capacity_bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " writable=0\n"
        );

        tf_write_buffer(
            fd,
            line,
            position
        );
    }

    for (
        int index = 0;
        index < inventory->extent_count;
        index++
    ) {
        const struct tf_recovery_logical_extent *extent = (
            &inventory->extents[index]
        );

        position = tf_append_text(
            line,
            sizeof(line),
            0,
            "TreeForge recovery: logical_extent metadata_slot="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            extent->metadata_slot
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " partition="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            extent->partition_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " partition_extent="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            extent->partition_extent_index
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " table_extent="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            extent->table_extent_index
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " type="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            (
                extent->target_type
                    == TREEFORGE_RECOVERY_LP_TARGET_LINEAR
                ? "linear"
                : "zero"
            )
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " sectors="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            extent->num_sectors
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " physical_sector="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            extent->target_data
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " target_source="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            extent->target_source
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " block_device="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            (
                extent->block_device_name[0]
                ? extent->block_device_name
                : "-"
            )
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "\n"
        );

        tf_write_buffer(
            fd,
            line,
            position
        );
    }
}


static void tf_emit_inventory_fd(
    long fd,
    const struct tf_runtime_partition_inventory *inventory
) {
    if (
        fd < 0
        || !inventory
    ) {
        return;
    }

    static const char version[] =
        "treeforge-recovery-inventory-v1\n";

    tf_write_buffer(
        fd,
        version,
        sizeof(version) - 1
    );

    char line[512];
    usize position = 0;

    line[0] = '\0';

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "TreeForge recovery: inventory active_slot="
    );

    if (
        inventory->active_slot_resolved
    ) {
        char slot[2] = {
            inventory->active_slot,
            '\0',
        };

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            slot
        );
    } else {
        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "unresolved"
        );
    }

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " partitions="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->partition_count
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " omitted="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->partitions_omitted
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " error="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->enumeration_error
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " stage="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) inventory->enumeration_stage
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " errno="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        inventory->enumeration_errno
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " expectations="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        (u64) TREEFORGE_RECOVERY_CANONICAL_EXPECTATION_COUNT
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        " read_probe_eligible="
    );

    position = tf_append_u64(
        line,
        sizeof(line),
        position,
        tf_read_probe_eligible_count(
            inventory
        )
    );

    position = tf_append_text(
        line,
        sizeof(line),
        position,
        "\n"
    );

    tf_write_buffer(
        fd,
        line,
        position
    );

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        const struct tf_runtime_partition *record = (
            &inventory->partitions[index]
        );

        position = 0;
        line[0] = '\0';

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "TreeForge recovery: partition="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            record->partition_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " canonical="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            record->canonical_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " slot="
        );

        if (record->slot_pair) {
            char slot[2] = {
                record->slot,
                '\0',
            };

            position = tf_append_text(
                line,
                sizeof(line),
                position,
                slot
            );
        } else {
            position = tf_append_text(
                line,
                sizeof(line),
                position,
                "-"
            );
        }

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " active="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) record->active
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " dev="
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            record->device_name
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " major="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->major_number
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " minor="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->minor_number
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " sectors="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->sectors
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->capacity_bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " writable=0 expected="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) record->canonical_expected
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " image_size_resolved="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) record->canonical_size_resolved
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " image_bytes="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            record->canonical_image_size_bytes
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " capacity_ok="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) record->canonical_capacity_sufficient
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            " read_probe="
        );

        position = tf_append_u64(
            line,
            sizeof(line),
            position,
            (u64) record->read_probe_eligible
        );

        position = tf_append_text(
            line,
            sizeof(line),
            position,
            "\n"
        );

        tf_write_buffer(
            fd,
            line,
            position
        );
    }

    tf_emit_lp_inventory_fd(
        fd,
        &tf_recovery_lp_inventory
    );

    tf_emit_flash_targets_fd(
        fd,
        &tf_recovery_flash_targets
    );

    tf_emit_lp_read_probe_fd(
        fd,
        &tf_recovery_lp_read_probe
    );

    tf_emit_read_probe_fd(
        fd,
        &tf_recovery_read_probe
    );

    tf_emit_flash_plan_fd(
        fd,
        &tf_recovery_flash_plan
    );
}


static void tf_emit_inventory(
    const struct tf_runtime_partition_inventory *inventory
) {
    /*
     * Keep a transient kernel-log copy for immediate diagnostics.
     */
    long kmsg = tf_open(
        "/dev/kmsg",
        O_WRONLY
        | O_NONBLOCK
    );

    if (kmsg >= 0) {
        tf_emit_inventory_fd(
            kmsg,
            inventory
        );

        tf_close(
            kmsg
        );
    }

    /*
     * Recovery is entered only after Android FirstStageMain has
     * established the canonical /metadata mount.
     *
     * TreeForge owns only /metadata/treeforge. Directory creation is
     * idempotent and the report is replaced atomically from the
     * perspective of later consumers by opening it with O_TRUNC.
     */
    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/metadata/treeforge",
        0755
    );

    long report = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_REPORT_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (report >= 0) {
        tf_emit_inventory_fd(
            report,
            inventory
        );

        tf_close(
            report
        );
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );
}



/* TREEFORGE_RECOVERY_UI_V1 */

/*
 * Recovery UI uses O_RDWR only for the DRM/KMS character device.
 *
 * The staged-image writer realizes its own transient block node only
 * after interactive confirmation and exact plan/source revalidation.
 * No persistent writable partition descriptor exists.
 */

#ifndef SYS_IOCTL
#define SYS_IOCTL 29
#endif

#ifndef SYS_NANOSLEEP
#define SYS_NANOSLEEP 101
#endif

#ifndef SYS_MUNMAP
#define SYS_MUNMAP 215
#endif

#ifndef SYS_MMAP
#define SYS_MMAP 222
#endif

#ifndef AT_REMOVEDIR
#define AT_REMOVEDIR 0x200
#endif

#ifndef O_RDWR
#define O_RDWR 2
#endif

#ifndef PROT_READ
#define PROT_READ 1
#endif

#ifndef PROT_WRITE
#define PROT_WRITE 2
#endif

#ifndef MAP_SHARED
#define MAP_SHARED 1
#endif

#ifndef S_IFCHR
#define S_IFCHR 0020000
#endif

#ifndef LINUX_REBOOT_CMD_RESTART2
#define LINUX_REBOOT_CMD_RESTART2 0xa1b2c3d4UL
#endif

#define EV_KEY 1

#define KEY_VOLUMEDOWN 114
#define KEY_VOLUMEUP 115
#define KEY_POWER 116

#define TREEFORGE_RECOVERY_UI_INPUT_COUNT 32
#define TREEFORGE_RECOVERY_UI_POLL_MS 25
#define TREEFORGE_RECOVERY_UI_MAX_TARGETS 16
#define TREEFORGE_RECOVERY_UI_PARTITIONS_PER_PAGE 6


struct tf_recovery_ui_input_event {
    long tv_sec;
    long tv_usec;
    u16 type;
    u16 code;
    int value;
};


struct tf_recovery_ui_timespec {
    long tv_sec;
    long tv_nsec;
};


/*
 * Recovery ADB is implemented after the UI code in this freestanding
 * translation unit. The UI poll loop uses this forward declaration to
 * reap adbd and tear down a dead gadget without blocking local Recovery.
 */
static void tf_recovery_adbd_maintain(void);


static long tf_recovery_ui_syscall6(
    long number,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4,
    long a5
) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x5 asm("x5") = a5;
    register long x8 asm("x8") = number;

    asm volatile(
        "svc 0"
        : "+r"(x0)
        : "r"(x1),
          "r"(x2),
          "r"(x3),
          "r"(x4),
          "r"(x5),
          "r"(x8)
        : "memory"
    );

    return x0;
}


static long tf_recovery_ui_syscall2(
    long number,
    long a0,
    long a1
) {
    return tf_recovery_ui_syscall6(
        number,
        a0,
        a1,
        0,
        0,
        0,
        0
    );
}


static long tf_recovery_ui_ioctl(
    long fd,
    unsigned long request,
    void *argument
) {
    return tf_syscall3(
        SYS_IOCTL,
        fd,
        (long) request,
        (long) argument
    );
}


static unsigned long tf_recovery_ui_makedev(
    unsigned long major,
    unsigned long minor
) {
    return (
        (minor & 0xffUL)
        | ((major & 0xfffUL) << 8)
        | ((minor & ~0xffUL) << 12)
        | ((major & ~0xfffUL) << 32)
    );
}


static long tf_recovery_ui_mknod_path(
    const char *path,
    long mode,
    unsigned long device
) {
    return tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long) path,
        mode,
        (long) device
    );
}


static int tf_recovery_ui_probe_readable_path(
    const char *path
) {
    long fd = tf_open(
        path,
        O_RDONLY
        | O_NONBLOCK
    );

    if (fd < 0) {
        return 0;
    }

    tf_close(
        fd
    );

    return 1;
}


static void tf_recovery_ui_create_presence_marker(
    const char *path
) {
    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) path,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd >= 0) {
        tf_close(
            fd
        );
    }
}


static void tf_recovery_ui_sleep_ms(
    long milliseconds
) {
    struct tf_recovery_ui_timespec request;

    request.tv_sec = (
        milliseconds / 1000
    );

    request.tv_nsec = (
        milliseconds % 1000
    ) * 1000000L;

    tf_recovery_ui_syscall2(
        SYS_NANOSLEEP,
        (long) &request,
        0
    );
}


struct tf_drm_mode_modeinfo {
    u32 clock;

    u16 hdisplay;
    u16 hsync_start;
    u16 hsync_end;
    u16 htotal;
    u16 hskew;

    u16 vdisplay;
    u16 vsync_start;
    u16 vsync_end;
    u16 vtotal;
    u16 vscan;

    u32 vrefresh;
    u32 flags;
    u32 type;

    char name[32];
};



struct tf_drm_set_client_cap {
    u64 capability;
    u64 value;
};


struct tf_drm_get_cap {
    u64 capability;
    u64 value;
};


struct tf_drm_mode_get_encoder {
    u32 encoder_id;
    u32 encoder_type;
    u32 crtc_id;
    u32 possible_crtcs;
    u32 possible_clones;
};


struct tf_drm_mode_obj_get_properties {
    u64 props_ptr;
    u64 prop_values_ptr;
    u32 count_props;
    u32 obj_id;
    u32 obj_type;
};


struct tf_drm_mode_get_property {
    u64 values_ptr;
    u64 enum_blob_ptr;

    u32 prop_id;
    u32 flags;

    char name[32];

    u32 count_values;
    u32 count_enum_blobs;
};


struct tf_drm_mode_property_enum {
    u64 value;
    char name[32];
};


struct tf_drm_mode_create_blob {
    u64 data;
    u32 length;
    u32 blob_id;
};


struct tf_drm_mode_destroy_blob {
    u32 blob_id;
};


struct tf_drm_mode_create_dumb {
    u32 height;
    u32 width;
    u32 bpp;
    u32 flags;
    u32 handle;
    u32 pitch;
    u64 size;
};


struct tf_drm_mode_destroy_dumb {
    u32 handle;
};


struct tf_drm_mode_map_dumb {
    u32 handle;
    u32 pad;
    u64 offset;
};


struct tf_drm_mode_fb_cmd2 {
    u32 fb_id;
    u32 width;
    u32 height;
    u32 pixel_format;
    u32 flags;

    u32 handles[4];
    u32 pitches[4];
    u32 offsets[4];
    u64 modifier[4];
};


struct tf_drm_mode_rmfb {
    u32 fb_id;
};


struct tf_drm_mode_atomic {
    u32 flags;
    u32 count_objs;

    u64 objs_ptr;
    u64 count_props_ptr;
    u64 props_ptr;
    u64 prop_values_ptr;

    u64 reserved;
    u64 user_data;
};


struct tf_drm_mode_get_plane_res {
    u64 plane_id_ptr;
    u32 count_planes;
    u32 pad;
};


struct tf_drm_mode_get_plane {
    u32 plane_id;
    u32 crtc_id;
    u32 fb_id;
    u32 possible_crtcs;
    u32 gamma_size;
    u32 count_format_types;
    u64 format_type_ptr;
};


#define TF_DRM_CLIENT_CAP_UNIVERSAL_PLANES 2
#define TF_DRM_CLIENT_CAP_ATOMIC 3

#define TF_DRM_CAP_DUMB_BUFFER 0x1

#define TF_DRM_MODE_LIMIT 16
#define TF_DRM_ENCODER_LIMIT 16

#define TF_DRM_PLANE_LIMIT 32

#define TF_DRM_MODE_OBJECT_CRTC 0xccccccccU
#define TF_DRM_MODE_OBJECT_CONNECTOR 0xc0c0c0c0U
#define TF_DRM_MODE_OBJECT_PLANE 0xeeeeeeeeU

#define TF_DRM_PLANE_TYPE_PRIMARY 1

#define TF_DRM_MODE_TYPE_PREFERRED (1U << 3)

#define TF_DRM_MODE_ATOMIC_TEST_ONLY 0x0100U
#define TF_DRM_MODE_ATOMIC_ALLOW_MODESET 0x0400U

#define TF_DRM_PROPERTY_LIMIT 64

#define TF_DRM_PROPERTY_ENUM_LIMIT 16
#define TF_DRM_PROPERTY_VALUE_LIMIT 16

#define TF_DRM_MODE_ROTATE_0   (1ULL << 0)
#define TF_DRM_MODE_ROTATE_90  (1ULL << 1)
#define TF_DRM_MODE_ROTATE_180 (1ULL << 2)
#define TF_DRM_MODE_ROTATE_270 (1ULL << 3)

#define TF_DRM_MODE_REFLECT_X  (1ULL << 4)
#define TF_DRM_MODE_REFLECT_Y  (1ULL << 5)

#define TF_DRM_PANEL_ORIENTATION_NORMAL   0
#define TF_DRM_PANEL_ORIENTATION_BOTTOM_UP 1
#define TF_DRM_PANEL_ORIENTATION_LEFT_UP   2
#define TF_DRM_PANEL_ORIENTATION_RIGHT_UP  3

#define TF_DRM_FORMAT_CODE(a, b, c, d) \
    ( \
        ((u32) (a)) \
        | ((u32) (b) << 8) \
        | ((u32) (c) << 16) \
        | ((u32) (d) << 24) \
    )

#define TF_DRM_FORMAT_XRGB8888 \
    TF_DRM_FORMAT_CODE('X', 'R', '2', '4')

struct tf_drm_mode_card_res {
    u64 fb_id_ptr;
    u64 crtc_id_ptr;
    u64 connector_id_ptr;
    u64 encoder_id_ptr;

    u32 count_fbs;
    u32 count_crtcs;
    u32 count_connectors;
    u32 count_encoders;

    u32 min_width;
    u32 max_width;
    u32 min_height;
    u32 max_height;
};


struct tf_drm_mode_crtc {
    u64 set_connectors_ptr;

    u32 count_connectors;
    u32 crtc_id;
    u32 fb_id;
    u32 x;
    u32 y;
    u32 gamma_size;
    u32 mode_valid;

    struct tf_drm_mode_modeinfo mode;
};


struct tf_drm_mode_get_connector {
    u64 encoders_ptr;
    u64 modes_ptr;
    u64 props_ptr;
    u64 prop_values_ptr;

    u32 count_modes;
    u32 count_props;
    u32 count_encoders;

    u32 encoder_id;
    u32 connector_id;
    u32 connector_type;
    u32 connector_type_id;
    u32 connection;

    u32 mm_width;
    u32 mm_height;
    u32 subpixel;
    u32 pad;
};


#define TF_IOC_NRBITS 8
#define TF_IOC_TYPEBITS 8
#define TF_IOC_SIZEBITS 14

#define TF_IOC_NRSHIFT 0
#define TF_IOC_TYPESHIFT \
    (TF_IOC_NRSHIFT + TF_IOC_NRBITS)
#define TF_IOC_SIZESHIFT \
    (TF_IOC_TYPESHIFT + TF_IOC_TYPEBITS)
#define TF_IOC_DIRSHIFT \
    (TF_IOC_SIZESHIFT + TF_IOC_SIZEBITS)

#define TF_IOC_WRITE 1U
#define TF_IOC_READ 2U

#define TF_IOC(dir, type, nr, size) \
    ( \
        ((unsigned long) (dir) << TF_IOC_DIRSHIFT) \
        | ((unsigned long) (type) << TF_IOC_TYPESHIFT) \
        | ((unsigned long) (nr) << TF_IOC_NRSHIFT) \
        | ((unsigned long) (size) << TF_IOC_SIZESHIFT) \
    )

#define TF_DRM_IOW(nr, type) \
    TF_IOC( \
        TF_IOC_WRITE, \
        'd', \
        nr, \
        sizeof(type) \
    )

#define TF_DRM_IOWR(nr, type) \
    TF_IOC( \
        TF_IOC_READ | TF_IOC_WRITE, \
        'd', \
        nr, \
        sizeof(type) \
    )



#define TF_DRM_IOCTL_GET_CAP \
    TF_DRM_IOWR( \
        0x0C, \
        struct tf_drm_get_cap \
    )

#define TF_DRM_IOCTL_SET_CLIENT_CAP \
    TF_DRM_IOW( \
        0x0D, \
        struct tf_drm_set_client_cap \
    )



#define TF_DRM_IOCTL_MODE_RMFB \
    TF_DRM_IOWR( \
        0xAF, \
        u32 \
    )

#define TF_DRM_IOCTL_MODE_CREATE_DUMB \
    TF_DRM_IOWR( \
        0xB2, \
        struct tf_drm_mode_create_dumb \
    )


#define TF_DRM_IOCTL_MODE_MAP_DUMB \
    TF_DRM_IOWR( \
        0xB3, \
        struct tf_drm_mode_map_dumb \
    )

#define TF_DRM_IOCTL_MODE_DESTROY_DUMB \
    TF_DRM_IOWR( \
        0xB4, \
        struct tf_drm_mode_destroy_dumb \
    )

#define TF_DRM_IOCTL_MODE_GETPLANERESOURCES \
    TF_DRM_IOWR( \
        0xB5, \
        struct tf_drm_mode_get_plane_res \
    )

#define TF_DRM_IOCTL_MODE_GETPLANE \
    TF_DRM_IOWR( \
        0xB6, \
        struct tf_drm_mode_get_plane \
    )


#define TF_DRM_IOCTL_MODE_ADDFB2 \
    TF_DRM_IOWR( \
        0xB8, \
        struct tf_drm_mode_fb_cmd2 \
    )

#define TF_DRM_IOCTL_MODE_OBJ_GETPROPERTIES \
    TF_DRM_IOWR( \
        0xB9, \
        struct tf_drm_mode_obj_get_properties \
    )

#define TF_DRM_IOCTL_MODE_ATOMIC \
    TF_DRM_IOWR( \
        0xBC, \
        struct tf_drm_mode_atomic \
    )

#define TF_DRM_IOCTL_MODE_CREATEPROPBLOB \
    TF_DRM_IOWR( \
        0xBD, \
        struct tf_drm_mode_create_blob \
    )

#define TF_DRM_IOCTL_MODE_DESTROYPROPBLOB \
    TF_DRM_IOWR( \
        0xBE, \
        struct tf_drm_mode_destroy_blob \
    )

#define TF_DRM_IOCTL_MODE_GETRESOURCES \
    TF_DRM_IOWR( \
        0xA0, \
        struct tf_drm_mode_card_res \
    )

#define TF_DRM_IOCTL_MODE_GETCRTC \
    TF_DRM_IOWR( \
        0xA1, \
        struct tf_drm_mode_crtc \
    )


#define TF_DRM_IOCTL_MODE_GETENCODER \
    TF_DRM_IOWR( \
        0xA6, \
        struct tf_drm_mode_get_encoder \
    )


#define TF_DRM_IOCTL_MODE_GETPROPERTY \
    TF_DRM_IOWR( \
        0xAA, \
        struct tf_drm_mode_get_property \
    )

#define TF_DRM_IOCTL_MODE_GETCONNECTOR \
    TF_DRM_IOWR( \
        0xA7, \
        struct tf_drm_mode_get_connector \
    )

#define TF_DRM_CONNECTOR_CONNECTED 1

#define TF_DRM_RESOURCE_LIMIT 16



static long tf_drm_menu_fd = -1;
static int tf_drm_menu_active = 0;

static int tf_drm_menu_created_dri_directory = 0;
static int tf_drm_menu_created_card0 = 0;

static long tf_drm_menu_mapped_address = -1;
static u64 tf_drm_menu_mapped_size = 0;

static u32 tf_drm_menu_width = 0;
static u32 tf_drm_menu_height = 0;
static u32 tf_drm_menu_pitch = 0;

static u32 tf_drm_menu_framebuffer_id = 0;
static u32 tf_drm_menu_dumb_handle = 0;
static u32 tf_drm_menu_blob_id = 0;

static u32 tf_drm_menu_connector = 0;
static u32 tf_drm_menu_crtc = 0;
static u32 tf_drm_menu_plane = 0;

static u32 tf_drm_menu_connector_crtc_property = 0;
static u32 tf_drm_menu_crtc_mode_property = 0;
static u32 tf_drm_menu_crtc_active_property = 0;
static u32 tf_drm_menu_plane_fb_property = 0;
static u32 tf_drm_menu_plane_crtc_property = 0;




static void tf_drm_fill_rect(
    u32 x,
    u32 y,
    u32 width,
    u32 height,
    u32 pixel
) {
    if (
        !tf_drm_menu_active
        || tf_drm_menu_mapped_address < 0
        || x >= tf_drm_menu_width
        || y >= tf_drm_menu_height
    ) {
        return;
    }

    if (
        width
        > tf_drm_menu_width - x
    ) {
        width = (
            tf_drm_menu_width - x
        );
    }

    if (
        height
        > tf_drm_menu_height - y
    ) {
        height = (
            tf_drm_menu_height - y
        );
    }

    volatile unsigned char *base = (
        (volatile unsigned char *)
        (usize) tf_drm_menu_mapped_address
    );

    for (
        u32 row_index = 0;
        row_index < height;
        row_index++
    ) {
        volatile u32 *row = (
            (volatile u32 *)
            (
                base
                + (
                    (usize) (
                        y + row_index
                    )
                    * (usize) tf_drm_menu_pitch
                )
            )
        );

        for (
            u32 column = 0;
            column < width;
            column++
        ) {
            row[
                x + column
            ] = pixel;
        }
    }
}


static unsigned char tf_drm_glyph_row(
    char value,
    int row
) {
    if (
        row < 0
        || row >= 7
    ) {
        return 0;
    }

    switch (value) {
        case 'A': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x11, 0x1f, 0x11, 0x11, 0x11
            };
            return rows[row];
        }

        case 'B': {
            static const unsigned char rows[7] = {
                0x1e, 0x11, 0x11, 0x1e, 0x11, 0x11, 0x1e
            };
            return rows[row];
        }

        case 'C': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0e
            };
            return rows[row];
        }

        case 'D': {
            static const unsigned char rows[7] = {
                0x1e, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1e
            };
            return rows[row];
        }

        case 'E': {
            static const unsigned char rows[7] = {
                0x1f, 0x10, 0x10, 0x1e, 0x10, 0x10, 0x1f
            };
            return rows[row];
        }

        case 'F': {
            static const unsigned char rows[7] = {
                0x1f, 0x10, 0x10, 0x1e, 0x10, 0x10, 0x10
            };
            return rows[row];
        }

        case 'G': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0f
            };
            return rows[row];
        }

        case 'H': {
            static const unsigned char rows[7] = {
                0x11, 0x11, 0x11, 0x1f, 0x11, 0x11, 0x11
            };
            return rows[row];
        }

        case 'I': {
            static const unsigned char rows[7] = {
                0x1f, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1f
            };
            return rows[row];
        }

        case 'J': {
            static const unsigned char rows[7] = {
                0x01, 0x01, 0x01, 0x01, 0x11, 0x11, 0x0e
            };
            return rows[row];
        }

        case 'N': {
            static const unsigned char rows[7] = {
                0x11, 0x19, 0x19, 0x15, 0x13, 0x13, 0x11
            };
            return rows[row];
        }

        case 'O': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0e
            };
            return rows[row];
        }

        case 'Q': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0d
            };
            return rows[row];
        }

        case 'R': {
            static const unsigned char rows[7] = {
                0x1e, 0x11, 0x11, 0x1e, 0x14, 0x12, 0x11
            };
            return rows[row];
        }

        case 'S': {
            static const unsigned char rows[7] = {
                0x0f, 0x10, 0x10, 0x0e, 0x01, 0x01, 0x1e
            };
            return rows[row];
        }

        case 'T': {
            static const unsigned char rows[7] = {
                0x1f, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04
            };
            return rows[row];
        }

        case 'V': {
            static const unsigned char rows[7] = {
                0x11, 0x11, 0x11, 0x11, 0x11, 0x0a, 0x04
            };
            return rows[row];
        }

        case 'X': {
            static const unsigned char rows[7] = {
                0x11, 0x11, 0x0a, 0x04, 0x0a, 0x11, 0x11
            };
            return rows[row];
        }

        case 'Y': {
            static const unsigned char rows[7] = {
                0x11, 0x11, 0x0a, 0x04, 0x04, 0x04, 0x04
            };
            return rows[row];
        }

        case 'Z': {
            static const unsigned char rows[7] = {
                0x1f, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1f
            };
            return rows[row];
        }

        case 'K': {
            static const unsigned char rows[7] = {
                0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11
            };
            return rows[row];
        }

        case 'L': {
            static const unsigned char rows[7] = {
                0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1f
            };
            return rows[row];
        }

        case 'P': {
            static const unsigned char rows[7] = {
                0x1e, 0x11, 0x11, 0x1e, 0x10, 0x10, 0x10
            };
            return rows[row];
        }

        case 'U': {
            static const unsigned char rows[7] = {
                0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0e
            };
            return rows[row];
        }

        case '0': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0e
            };
            return rows[row];
        }

        case '1': {
            static const unsigned char rows[7] = {
                0x04, 0x0c, 0x14, 0x04, 0x04, 0x04, 0x1f
            };
            return rows[row];
        }

        case '2': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1f
            };
            return rows[row];
        }

        case '3': {
            static const unsigned char rows[7] = {
                0x1e, 0x01, 0x01, 0x0e, 0x01, 0x01, 0x1e
            };
            return rows[row];
        }

        case '4': {
            static const unsigned char rows[7] = {
                0x02, 0x06, 0x0a, 0x12, 0x1f, 0x02, 0x02
            };
            return rows[row];
        }

        case '5': {
            static const unsigned char rows[7] = {
                0x1f, 0x10, 0x10, 0x1e, 0x01, 0x01, 0x1e
            };
            return rows[row];
        }

        case '6': {
            static const unsigned char rows[7] = {
                0x0e, 0x10, 0x10, 0x1e, 0x11, 0x11, 0x0e
            };
            return rows[row];
        }

        case '7': {
            static const unsigned char rows[7] = {
                0x1f, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08
            };
            return rows[row];
        }

        case '8': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x11, 0x0e, 0x11, 0x11, 0x0e
            };
            return rows[row];
        }

        case '9': {
            static const unsigned char rows[7] = {
                0x0e, 0x11, 0x11, 0x0f, 0x01, 0x01, 0x0e
            };
            return rows[row];
        }

        case '.': {
            static const unsigned char rows[7] = {
                0x00, 0x00, 0x00, 0x00, 0x00, 0x0c, 0x0c
            };
            return rows[row];
        }

        case ':': {
            static const unsigned char rows[7] = {
                0x00, 0x0c, 0x0c, 0x00, 0x0c, 0x0c, 0x00
            };
            return rows[row];
        }

        case '+': {
            static const unsigned char rows[7] = {
                0x00, 0x04, 0x04, 0x1f, 0x04, 0x04, 0x00
            };
            return rows[row];
        }

        case '-': {
            static const unsigned char rows[7] = {
                0x00, 0x00, 0x00, 0x1f, 0x00, 0x00, 0x00
            };
            return rows[row];
        }

        case '/': {
            static const unsigned char rows[7] = {
                0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10
            };
            return rows[row];
        }

        case '>': {
            static const unsigned char rows[7] = {
                0x10, 0x08, 0x04, 0x02, 0x04, 0x08, 0x10
            };
            return rows[row];
        }

        case '(': {
            static const unsigned char rows[7] = {
                0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02
            };
            return rows[row];
        }

        case ')': {
            static const unsigned char rows[7] = {
                0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08
            };
            return rows[row];
        }

        case 'M': {
            static const unsigned char rows[7] = {
                0x11, 0x1b, 0x15, 0x15, 0x11, 0x11, 0x11
            };
            return rows[row];
        }

        case 'W': {
            static const unsigned char rows[7] = {
                0x11, 0x11, 0x11, 0x15, 0x15, 0x1b, 0x11
            };
            return rows[row];
        }

        default:
            return 0;
    }
}


static void tf_drm_draw_char(
    u32 x,
    u32 y,
    char value,
    u32 scale,
    u32 pixel
) {
    for (
        int row = 0;
        row < 7;
        row++
    ) {
        unsigned char bits = (
            tf_drm_glyph_row(
                value,
                row
            )
        );

        for (
            int column = 0;
            column < 5;
            column++
        ) {
            if (
                bits
                & (
                    1U
                    << (
                        4 - column
                    )
                )
            ) {
                tf_drm_fill_rect(
                    x + (
                        (u32) column
                        * scale
                    ),
                    y + (
                        (u32) row
                        * scale
                    ),
                    scale,
                    scale,
                    pixel
                );
            }
        }
    }
}


static u32 tf_drm_text_width(
    const char *value,
    u32 scale
) {
    usize length = (
        tf_strlen(
            value
        )
    );

    if (length == 0) {
        return 0;
    }

    return (
        ((u32) length * 6U * scale)
        - scale
    );
}


static void tf_drm_draw_text(
    u32 x,
    u32 y,
    const char *value,
    u32 scale,
    u32 pixel
) {
    u32 cursor = x;

    for (
        usize index = 0;
        value[index] != '\0';
        index++
    ) {
        if (value[index] != ' ') {
            tf_drm_draw_char(
                cursor,
                y,
                value[index],
                scale,
                pixel
            );
        }

        cursor += (
            6U * scale
        );
    }
}


static void tf_drm_draw_management_line(
    const char *value,
    u32 y,
    u32 scale,
    u32 pixel
) {
    u32 line_scale = scale;

    u32 margin = (
        8U * scale
    );

    u32 available_width = (
        tf_drm_menu_width > margin
        ? tf_drm_menu_width - margin
        : tf_drm_menu_width
    );

    while (
        line_scale > 2U
        && tf_drm_text_width(
            value,
            line_scale
        ) > available_width
    ) {
        line_scale--;
    }

    u32 width = (
        tf_drm_text_width(
            value,
            line_scale
        )
    );

    u32 x = (
        tf_drm_menu_width > width
        ? (
            tf_drm_menu_width
            - width
        ) / 2U
        : 0
    );

    tf_drm_draw_text(
        x,
        y,
        value,
        line_scale,
        pixel
    );
}

static void tf_recovery_ui_event_path(
    int index,
    char *output
) {
    static const char prefix[] =
        "/dev/input/event";

    int position = 0;

    for (
        int i = 0;
        prefix[i] != '\0';
        i++
    ) {
        output[position++] = (
            prefix[i]
        );
    }

    if (index >= 10) {
        output[position++] = (
            '0'
            + (
                index
                / 10
            )
        );
    }

    output[position++] = (
        '0'
        + (
            index
            % 10
        )
    );

    output[position] = '\0';
}

static void tf_recovery_ui_sysfs_event_dev_path(
    int index,
    char *output
) {
    static const char prefix[] =
        "/sys/class/input/event";

    static const char suffix[] =
        "/dev";

    int position = 0;

    for (
        int i = 0;
        prefix[i] != '\0';
        i++
    ) {
        output[position++] = (
            prefix[i]
        );
    }

    if (index >= 10) {
        output[position++] = (
            '0'
            + (
                index
                / 10
            )
        );
    }

    output[position++] = (
        '0'
        + (
            index
            % 10
        )
    );

    for (
        int i = 0;
        suffix[i] != '\0';
        i++
    ) {
        output[position++] = (
            suffix[i]
        );
    }

    output[position] = '\0';
}


static int tf_recovery_ui_parse_device_number(
    const char *value,
    long length,
    unsigned int *major_number,
    unsigned int *minor_number
) {
    if (
        value == 0
        || length <= 0
        || major_number == 0
        || minor_number == 0
    ) {
        return -1;
    }

    long position = 0;

    unsigned int major_value = 0;
    unsigned int minor_value = 0;

    int major_digits = 0;
    int minor_digits = 0;

    while (
        position < length
        && value[position] >= '0'
        && value[position] <= '9'
    ) {
        major_value = (
            major_value * 10U
            + (
                (unsigned int)
                (
                    value[position]
                    - '0'
                )
            )
        );

        if (major_value > 0xfffU) {
            return -1;
        }

        position++;
        major_digits++;
    }

    if (
        major_digits == 0
        || position >= length
        || value[position] != ':'
    ) {
        return -1;
    }

    position++;

    while (
        position < length
        && value[position] >= '0'
        && value[position] <= '9'
    ) {
        minor_value = (
            minor_value * 10U
            + (
                (unsigned int)
                (
                    value[position]
                    - '0'
                )
            )
        );

        if (minor_value > 0xfffffU) {
            return -1;
        }

        position++;
        minor_digits++;
    }

    if (minor_digits == 0) {
        return -1;
    }

    *major_number = major_value;
    *minor_number = minor_value;

    return 0;
}


static int tf_recovery_ui_prepare_input_node(
    int index,
    const char *device_path
) {
    char sysfs_path[48];

    tf_recovery_ui_sysfs_event_dev_path(
        index,
        sysfs_path
    );

    long fd = tf_open(
        sysfs_path,
        O_RDONLY
    );

    if (fd < 0) {
        return -1;
    }

    char value[32];

    long amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) value,
        (long) sizeof(value)
    );

    tf_close(
        fd
    );

    if (amount <= 0) {
        return -1;
    }

    unsigned int major_number;
    unsigned int minor_number;

    if (
        tf_recovery_ui_parse_device_number(
            value,
            amount,
            &major_number,
            &minor_number
        )
        != 0
    ) {
        return -1;
    }

    long result = tf_recovery_ui_mknod_path(
        device_path,
        S_IFCHR | 0600,
        tf_recovery_ui_makedev(
            major_number,
            minor_number
        )
    );

    /*
     * -17 is EEXIST. The node may already have been synthesized by an
     * earlier scan iteration.
     */
    if (
        result == 0
        || result == -17
    ) {
        return 0;
    }

    return -1;
}



static void tf_recovery_ui_runtime_sysfs_event_dev_path(
    int index,
    char *output
) {
    static const char prefix[] =
        "/sys/class/input/event";

    static const char suffix[] =
        "/dev";

    int position = 0;

    for (
        int i = 0;
        prefix[i] != '\0';
        i++
    ) {
        output[position++] = prefix[i];
    }

    if (index >= 10) {
        output[position++] = (
            '0'
            + (
                index
                / 10
            )
        );
    }

    output[position++] = (
        '0'
        + (
            index
            % 10
        )
    );

    for (
        int i = 0;
        suffix[i] != '\0';
        i++
    ) {
        output[position++] = suffix[i];
    }

    output[position] = '\0';
}

static unsigned long tf_recovery_ui_runtime_makedev(
    unsigned long major,
    unsigned long minor
) {
    /*
     * Linux userspace dev_t encoding, equivalent to makedev().
     */
    return (
        (minor & 0xffUL)
        | ((major & 0xfffUL) << 8)
        | ((minor & ~0xffUL) << 12)
        | ((major & ~0xfffUL) << 32)
    );
}

static int tf_recovery_ui_runtime_parse_device_number(
    const char *value,
    long length,
    unsigned long *major,
    unsigned long *minor
) {
    unsigned long parsed_major = 0;
    unsigned long parsed_minor = 0;

    int position = 0;
    int major_digits = 0;
    int minor_digits = 0;

    while (
        position < length
        && value[position] >= '0'
        && value[position] <= '9'
    ) {
        parsed_major = (
            parsed_major * 10UL
            + (unsigned long) (
                value[position]
                - '0'
            )
        );

        position++;
        major_digits++;
    }

    if (
        major_digits == 0
        || position >= length
        || value[position] != ':'
    ) {
        return -1;
    }

    position++;

    while (
        position < length
        && value[position] >= '0'
        && value[position] <= '9'
    ) {
        parsed_minor = (
            parsed_minor * 10UL
            + (unsigned long) (
                value[position]
                - '0'
            )
        );

        position++;
        minor_digits++;
    }

    if (minor_digits == 0) {
        return -1;
    }

    *major = parsed_major;
    *minor = parsed_minor;

    return 0;
}

static int tf_recovery_ui_get_event_device_number(
    int index,
    unsigned long *major,
    unsigned long *minor
) {
    char path[64];

    tf_recovery_ui_runtime_sysfs_event_dev_path(
        index,
        path
    );

    long fd = tf_open(
        path,
        O_RDONLY
    );

    if (fd < 0) {
        return -1;
    }

    char buffer[32];

    long amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) buffer,
        (long) (
            sizeof(buffer)
            - 1
        )
    );

    tf_close(
        fd
    );

    if (amount <= 0) {
        return -1;
    }

    buffer[amount] = '\0';

    return tf_recovery_ui_runtime_parse_device_number(
        buffer,
        amount,
        major,
        minor
    );
}

static int tf_recovery_ui_realize_input_nodes(
    int *created_input_directory,
    int *created_nodes,
    int *sysfs_devices_seen
) {
    *created_input_directory = 0;
    *sysfs_devices_seen = 0;

    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_UI_INPUT_COUNT;
        index++
    ) {
        created_nodes[index] = 0;
    }

    /*
     * Android FirstStageMain has already mounted its canonical /dev
     * tmpfs. TreeForge only adds the missing input subdirectory if
     * necessary.
     */
    long mkdir_result = tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/dev/input",
        0755
    );

    if (mkdir_result == 0) {
        *created_input_directory = 1;
    } else if (mkdir_result != -17) {
        return -1;
    }

    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_UI_INPUT_COUNT;
        index++
    ) {
        unsigned long major;
        unsigned long minor;

        if (
            tf_recovery_ui_get_event_device_number(
                index,
                &major,
                &minor
            )
            != 0
        ) {
            continue;
        }

        (*sysfs_devices_seen)++;

        char path[32];

        tf_recovery_ui_event_path(
            index,
            path
        );

        long result = tf_syscall4(
            SYS_MKNODAT,
            AT_FDCWD,
            (long) path,
            S_IFCHR | 0600,
            (long) tf_recovery_ui_runtime_makedev(
                major,
                minor
            )
        );

        if (result == 0) {
            created_nodes[index] = 1;
            continue;
        }

        /*
         * EEXIST means Android already supplied this node.
         */
        if (result == -17) {
            continue;
        }
    }

    return 0;
}

static void tf_recovery_ui_cleanup_realized_input_nodes(
    int created_input_directory,
    int *created_nodes
) {
    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_UI_INPUT_COUNT;
        index++
    ) {
        if (!created_nodes[index]) {
            continue;
        }

        char path[32];

        tf_recovery_ui_event_path(
            index,
            path
        );

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) path,
            0
        );

        created_nodes[index] = 0;
    }

    if (created_input_directory) {
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) "/dev/input",
            AT_REMOVEDIR
        );
    }
}

static void tf_recovery_ui_close_inputs(
    long *inputs
) {
    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_UI_INPUT_COUNT;
        index++
    ) {
        if (inputs[index] >= 0) {
            tf_close(
                inputs[index]
            );

            inputs[index] = -1;
        }
    }
}



static int tf_display_device_number(
    const char *sysfs_path,
    unsigned int *major_number,
    unsigned int *minor_number
) {
    char buffer[64];

    long fd = tf_open(
        sysfs_path,
        O_RDONLY
        | O_NONBLOCK
    );

    if (fd < 0) {
        return -1;
    }

    long amount = tf_syscall3(
        SYS_READ,
        fd,
        (long) buffer,
        (long) (
            sizeof(buffer)
            - 1
        )
    );

    tf_close(
        fd
    );

    if (amount <= 0) {
        return -1;
    }

    buffer[amount] = '\0';

    return tf_recovery_ui_parse_device_number(
        buffer,
        amount,
        major_number,
        minor_number
    );
}


static int tf_realize_drm_card0(
    int *created_directory,
    int *created_node
) {
    *created_directory = 0;
    *created_node = 0;

    /*
     * If Android has already created the DRM node, consume it
     * exactly as-is.
     */
    long existing = tf_open(
        "/dev/dri/card0",
        O_RDWR
        | O_NONBLOCK
    );

    if (existing >= 0) {
        tf_close(
            existing
        );

        return 1;
    }

    /*
     * DRM is registered in sysfs before Android's ueventd has
     * necessarily materialized /dev/dri/card0.
     *
     * Derive the device identity from the kernel rather than
     * assuming a DRM major/minor.
     */
    unsigned int major_number = 0;
    unsigned int minor_number = 0;

    if (
        tf_display_device_number(
            "/sys/class/drm/card0/dev",
            &major_number,
            &minor_number
        ) != 0
    ) {
        return 0;
    }

    long mkdir_result = tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/dev/dri",
        0755
    );

    if (mkdir_result == 0) {
        *created_directory = 1;
    } else if (mkdir_result != -17) {
        /*
         * -17 == EEXIST.
         */
        return 0;
    }

    long node_result = tf_recovery_ui_mknod_path(
        "/dev/dri/card0",
        S_IFCHR | 0600,
        tf_recovery_ui_makedev(
            major_number,
            minor_number
        )
    );

    if (node_result == 0) {
        *created_node = 1;
    } else if (node_result != -17) {
        if (*created_directory) {
            tf_syscall3(
                SYS_UNLINKAT,
                AT_FDCWD,
                (long) "/dev/dri",
                AT_REMOVEDIR
            );

            *created_directory = 0;
        }

        return 0;
    }

    long drm_fd = tf_open(
        "/dev/dri/card0",
        O_RDWR
        | O_NONBLOCK
    );

    if (drm_fd < 0) {
        if (*created_node) {
            tf_syscall3(
                SYS_UNLINKAT,
                AT_FDCWD,
                (long) "/dev/dri/card0",
                0
            );

            *created_node = 0;
        }

        if (*created_directory) {
            tf_syscall3(
                SYS_UNLINKAT,
                AT_FDCWD,
                (long) "/dev/dri",
                AT_REMOVEDIR
            );

            *created_directory = 0;
        }

        return 0;
    }

    tf_close(
        drm_fd
    );

    return 1;
}


static void tf_cleanup_drm_card0(
    int created_directory,
    int created_node
) {
    if (created_node) {
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) "/dev/dri/card0",
            0
        );
    }

    if (created_directory) {
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) "/dev/dri",
            AT_REMOVEDIR
        );
    }
}




static void tf_probe_drm_plane_state(
    long drm_fd
) {
    /*
     * Universal-plane discovery is client-local state only.
     * No plane, CRTC, framebuffer, connector, or hardware state
     * is modified by this probe.
     */
    struct tf_drm_set_client_cap capability;

    capability.capability = (
        TF_DRM_CLIENT_CAP_UNIVERSAL_PLANES
    );

    capability.value = 1;

    long result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_SET_CLIENT_CAP,
        &capability
    );

    if (result < 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-universal-planes-failed"
        );

        return;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-universal-planes-ok"
    );

    static struct tf_drm_mode_get_plane_res resources;

    resources.plane_id_ptr = 0;
    resources.count_planes = 0;
    resources.pad = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETPLANERESOURCES,
        &resources
    );

    if (result < 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-plane-resources-failed"
        );

        return;
    }

    if (resources.count_planes == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-planes-empty"
        );

        return;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-planes-present"
    );

    if (
        resources.count_planes
        > TF_DRM_PLANE_LIMIT
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-plane-overflow"
        );

        return;
    }

    u32 plane_count = resources.count_planes;

    static u32 plane_ids[
        TF_DRM_PLANE_LIMIT
    ];

    resources.plane_id_ptr = (
        (u64) (usize) plane_ids
    );

    resources.count_planes = plane_count;
    resources.pad = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETPLANERESOURCES,
        &resources
    );

    if (result < 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-plane-ids-failed"
        );

        return;
    }

    if (
        resources.count_planes
        > plane_count
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-plane-race"
        );

        return;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-plane-ids-ok"
    );

    int queried_plane = 0;
    int attached_plane = 0;
    int framebuffer_plane = 0;

    static struct tf_drm_mode_get_plane plane;

    for (
        u32 index = 0;
        index < resources.count_planes;
        index++
    ) {
        plane.plane_id = plane_ids[index];
        plane.crtc_id = 0;
        plane.fb_id = 0;
        plane.possible_crtcs = 0;
        plane.gamma_size = 0;
        plane.count_format_types = 0;
        plane.format_type_ptr = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETPLANE,
            &plane
        );

        if (result < 0) {
            continue;
        }

        queried_plane = 1;

        if (plane.crtc_id != 0) {
            attached_plane = 1;
        }

        if (plane.fb_id != 0) {
            framebuffer_plane = 1;
        }
    }

    if (queried_plane) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-plane-query-ok"
        );
    }

    if (attached_plane) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-plane-attached"
        );
    }

    if (framebuffer_plane) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-plane-framebuffer"
        );
    }
}




static int tf_drm_property_name_equal(
    const char *left,
    const char *right
) {
    for (
        int index = 0;
        index < 32;
        index++
    ) {
        if (left[index] != right[index]) {
            return 0;
        }

        if (left[index] == '\0') {
            return 1;
        }
    }

    return 0;
}


static u32 tf_drm_find_property(
    long drm_fd,
    u32 object_id,
    u32 object_type,
    const char *wanted_name,
    u64 *current_value
) {
    static struct tf_drm_mode_obj_get_properties object_properties;

    static u32 property_ids[
        TF_DRM_PROPERTY_LIMIT
    ];

    static u64 property_values[
        TF_DRM_PROPERTY_LIMIT
    ];

    object_properties.props_ptr = 0;
    object_properties.prop_values_ptr = 0;
    object_properties.count_props = 0;
    object_properties.obj_id = object_id;
    object_properties.obj_type = object_type;

    long result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_OBJ_GETPROPERTIES,
        &object_properties
    );

    if (
        result < 0
        || object_properties.count_props == 0
        || object_properties.count_props
            > TF_DRM_PROPERTY_LIMIT
    ) {
        return 0;
    }

    u32 property_count = (
        object_properties.count_props
    );

    object_properties.props_ptr = (
        (u64) (usize) property_ids
    );

    object_properties.prop_values_ptr = (
        (u64) (usize) property_values
    );

    object_properties.count_props = (
        property_count
    );

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_OBJ_GETPROPERTIES,
        &object_properties
    );

    if (
        result < 0
        || object_properties.count_props
            > property_count
    ) {
        return 0;
    }

    for (
        u32 index = 0;
        index < object_properties.count_props;
        index++
    ) {
        struct tf_drm_mode_get_property property;

        property.values_ptr = 0;
        property.enum_blob_ptr = 0;
        property.prop_id = property_ids[index];
        property.flags = 0;

        for (
            int name_index = 0;
            name_index < 32;
            name_index++
        ) {
            property.name[name_index] = '\0';
        }

        property.count_values = 0;
        property.count_enum_blobs = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETPROPERTY,
            &property
        );

        if (result < 0) {
            continue;
        }

        if (
            tf_drm_property_name_equal(
                property.name,
                wanted_name
            )
        ) {
            if (current_value != 0) {
                *current_value = (
                    property_values[index]
                );
            }

            return property_ids[index];
        }
    }

    return 0;
}



static void tf_probe_drm_orientation_state(
    long drm_fd,
    u32 connector_id,
    u32 plane_id,
    const struct tf_drm_mode_modeinfo *mode
) {
    /*
     * Native DRM mode geometry.
     *
     * This is scanout geometry, not necessarily the same orientation
     * that the user is physically holding the device in.
     */
    if (mode->hdisplay > mode->vdisplay) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-orientation-mode-landscape"
        );
    } else if (mode->vdisplay > mode->hdisplay) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-orientation-mode-portrait"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-orientation-mode-square"
        );
    }


    /*
     * Primary-plane rotation.
     *
     * This property describes the DRM plane transform. Its current
     * value is separate from the panel's fixed mounting orientation.
     */
    u64 rotation_value = 0;

    u32 rotation_property = tf_drm_find_property(
        drm_fd,
        plane_id,
        TF_DRM_MODE_OBJECT_PLANE,
        "rotation",
        &rotation_value
    );

    if (rotation_property == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-orientation-plane-rotation-absent"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-orientation-plane-rotation-present"
        );

        if (rotation_value == 0) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-zero"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_0
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-0"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_90
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-90"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_180
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-180"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_270
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-270"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_REFLECT_X
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-reflect-x"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_REFLECT_Y
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-reflect-y"
            );
        }


        /*
         * Query the bitmask enumeration so TreeForge knows which
         * transforms this particular primary plane can perform.
         */
        struct tf_drm_mode_get_property property;

        property.values_ptr = 0;
        property.enum_blob_ptr = 0;
        property.prop_id = rotation_property;
        property.flags = 0;

        for (
            int index = 0;
            index < 32;
            index++
        ) {
            property.name[index] = '\0';
        }

        property.count_values = 0;
        property.count_enum_blobs = 0;

        long result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETPROPERTY,
            &property
        );

        if (
            result == 0
            && property.count_enum_blobs > 0
            && property.count_enum_blobs
                <= TF_DRM_PROPERTY_ENUM_LIMIT
            && property.count_values
                <= TF_DRM_PROPERTY_VALUE_LIMIT
        ) {
            u32 enum_count = (
                property.count_enum_blobs
            );

            u32 value_count = (
                property.count_values
            );

            static struct tf_drm_mode_property_enum enums[
                TF_DRM_PROPERTY_ENUM_LIMIT
            ];

            static u64 property_values[
                TF_DRM_PROPERTY_VALUE_LIMIT
            ];

            property.enum_blob_ptr = (
                (u64) (usize) enums
            );

            property.values_ptr = (
                value_count > 0
                ? (u64) (usize) property_values
                : 0
            );

            property.count_enum_blobs = enum_count;
            property.count_values = value_count;

            result = tf_recovery_ui_ioctl(
                drm_fd,
                TF_DRM_IOCTL_MODE_GETPROPERTY,
                &property
            );

            if (
                result == 0
                && property.count_enum_blobs
                    <= enum_count
                && property.count_values
                    <= value_count
            ) {
                tf_recovery_ui_create_presence_marker(
                    "/dev/treeforge-display-orientation-plane-enums-ok"
                );

                for (
                    u32 index = 0;
                    index < property.count_enum_blobs;
                    index++
                ) {
                    if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "rotate-0"
                        )
                    ) {
                        tf_recovery_ui_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-0"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "rotate-90"
                        )
                    ) {
                        tf_recovery_ui_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-90"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "rotate-180"
                        )
                    ) {
                        tf_recovery_ui_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-180"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "rotate-270"
                        )
                    ) {
                        tf_recovery_ui_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-270"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "reflect-x"
                        )
                    ) {
                        tf_recovery_ui_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-reflect-x"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "reflect-y"
                        )
                    ) {
                        tf_recovery_ui_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-reflect-y"
                        );
                    }
                }
            } else {
                tf_recovery_ui_create_presence_marker(
                    "/dev/treeforge-display-orientation-plane-enums-failed"
                );
            }
        } else {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-enums-unavailable"
            );
        }
    }


    /*
     * Fixed panel mounting orientation.
     *
     * This is chassis-relative metadata. It does NOT represent live
     * accelerometer/device orientation.
     */
    u64 panel_orientation = 0;

    u32 panel_orientation_property = (
        tf_drm_find_property(
            drm_fd,
            connector_id,
            TF_DRM_MODE_OBJECT_CONNECTOR,
            "panel orientation",
            &panel_orientation
        )
    );

    if (panel_orientation_property == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-orientation-panel-property-absent"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-orientation-panel-property-present"
        );

        if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_NORMAL
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-normal"
            );
        } else if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_BOTTOM_UP
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-bottom-up"
            );
        } else if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_LEFT_UP
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-left-up"
            );
        } else if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_RIGHT_UP
        ) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-right-up"
            );
        } else {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-value-unknown"
            );
        }
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-orientation-audit-complete"
    );
}


static void tf_probe_drm_scanout_requirements(
    long drm_fd
) {
    /*
     * Final pre-scanout discovery.
     *
     * This verifies:
     *   - dumb-buffer support;
     *   - atomic modesetting support;
     *   - connector mode discovery;
     *   - encoder -> CRTC compatibility.
     *
     * The connector force-probe may briefly disturb/flicker the
     * panel, but no framebuffer or modeset is committed here.
     */

    struct tf_drm_get_cap dumb_cap;

    dumb_cap.capability = (
        TF_DRM_CAP_DUMB_BUFFER
    );

    dumb_cap.value = 0;

    long result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_GET_CAP,
        &dumb_cap
    );

    if (
        result == 0
        && dumb_cap.value != 0
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-dumb-buffer-ok"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-dumb-buffer-failed"
        );
    }

    struct tf_drm_set_client_cap atomic_cap;

    atomic_cap.capability = (
        TF_DRM_CLIENT_CAP_ATOMIC
    );

    atomic_cap.value = 1;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_SET_CLIENT_CAP,
        &atomic_cap
    );

    if (result == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-ok"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-failed"
        );
    }

    /*
     * Obtain connector/CRTC object IDs.
     */
    static struct tf_drm_mode_card_res resources;

    resources.fb_id_ptr = 0;
    resources.crtc_id_ptr = 0;
    resources.connector_id_ptr = 0;
    resources.encoder_id_ptr = 0;

    resources.count_fbs = 0;
    resources.count_crtcs = 0;
    resources.count_connectors = 0;
    resources.count_encoders = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (
        result < 0
        || resources.count_crtcs == 0
        || resources.count_connectors == 0
        || resources.count_crtcs > TF_DRM_RESOURCE_LIMIT
        || resources.count_connectors > TF_DRM_RESOURCE_LIMIT
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-scanout-resources-failed"
        );

        return;
    }

    u32 crtc_count = resources.count_crtcs;
    u32 connector_count = resources.count_connectors;

    static u32 crtc_ids[
        TF_DRM_RESOURCE_LIMIT
    ];

    static u32 connector_ids[
        TF_DRM_RESOURCE_LIMIT
    ];

    resources.fb_id_ptr = 0;

    resources.crtc_id_ptr = (
        (u64) (usize) crtc_ids
    );

    resources.connector_id_ptr = (
        (u64) (usize) connector_ids
    );

    resources.encoder_id_ptr = 0;

    /*
     * Only request the identifier populations for which TreeForge
     * supplied output arrays. GETRESOURCES treats a non-zero count
     * as a request to copy that identifier population.
     */
    resources.count_fbs = 0;
    resources.count_crtcs = crtc_count;
    resources.count_connectors = connector_count;
    resources.count_encoders = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (
        result < 0
        || resources.count_crtcs > crtc_count
        || resources.count_connectors > connector_count
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-scanout-resource-ids-failed"
        );

        return;
    }

    int force_probe_ok = 0;
    int modes_present = 0;
    int preferred_mode_present = 0;
    int encoders_present = 0;
    int encoder_query_ok = 0;
    int compatible_crtc = 0;

    static struct tf_drm_mode_get_connector connector;

    static struct tf_drm_mode_modeinfo modes[
        TF_DRM_MODE_LIMIT
    ];

    static u32 encoder_ids[
        TF_DRM_ENCODER_LIMIT
    ];

    for (
        u32 connector_index = 0;
        connector_index < connector_count;
        connector_index++
    ) {
        /*
         * count_modes=0 intentionally requests a force-probe.
         *
         * The DRM client must be master for the kernel to perform
         * this operation.
         */
        connector.encoders_ptr = 0;
        connector.modes_ptr = 0;
        connector.props_ptr = 0;
        connector.prop_values_ptr = 0;

        connector.count_modes = 0;
        connector.count_props = 0;
        connector.count_encoders = 0;

        connector.encoder_id = 0;
        connector.connector_id = (
            connector_ids[
                connector_index
            ]
        );

        connector.connector_type = 0;
        connector.connector_type_id = 0;
        connector.connection = 0;
        connector.mm_width = 0;
        connector.mm_height = 0;
        connector.subpixel = 0;
        connector.pad = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETCONNECTOR,
            &connector
        );

        if (result < 0) {
            continue;
        }

        force_probe_ok = 1;

        if (
            connector.connection
            != TF_DRM_CONNECTOR_CONNECTED
        ) {
            continue;
        }

        if (
            connector.count_modes == 0
            || connector.count_modes
                > TF_DRM_MODE_LIMIT
        ) {
            continue;
        }

        modes_present = 1;

        if (
            connector.count_encoders
            > TF_DRM_ENCODER_LIMIT
        ) {
            continue;
        }

        u32 mode_count = (
            connector.count_modes
        );

        u32 encoder_count = (
            connector.count_encoders
        );

        connector.modes_ptr = (
            (u64) (usize) modes
        );

        connector.encoders_ptr = (
            encoder_count > 0
            ? (u64) (usize) encoder_ids
            : 0
        );

        connector.count_modes = mode_count;
        connector.count_encoders = encoder_count;

        /*
         * We are not retrieving connector properties in this
         * checkpoint.
         */
        connector.props_ptr = 0;
        connector.prop_values_ptr = 0;
        connector.count_props = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETCONNECTOR,
            &connector
        );

        if (
            result < 0
            || connector.count_modes > mode_count
            || connector.count_encoders > encoder_count
        ) {
            continue;
        }

        for (
            u32 mode_index = 0;
            mode_index < connector.count_modes;
            mode_index++
        ) {
            if (
                modes[mode_index].type
                & (1U << 3)
            ) {
                preferred_mode_present = 1;
            }
        }

        if (connector.count_encoders > 0) {
            encoders_present = 1;
        }

        for (
            u32 encoder_index = 0;
            encoder_index < connector.count_encoders;
            encoder_index++
        ) {
            struct tf_drm_mode_get_encoder encoder;

            encoder.encoder_id = (
                encoder_ids[
                    encoder_index
                ]
            );

            encoder.encoder_type = 0;
            encoder.crtc_id = 0;
            encoder.possible_crtcs = 0;
            encoder.possible_clones = 0;

            result = tf_recovery_ui_ioctl(
                drm_fd,
                TF_DRM_IOCTL_MODE_GETENCODER,
                &encoder
            );

            if (result < 0) {
                continue;
            }

            encoder_query_ok = 1;

            for (
                u32 crtc_index = 0;
                crtc_index < crtc_count;
                crtc_index++
            ) {
                if (
                    encoder.possible_crtcs
                    & (
                        1U
                        << crtc_index
                    )
                ) {
                    compatible_crtc = 1;
                }
            }
        }
    }

    if (force_probe_ok) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-force-probe-ok"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-force-probe-failed"
        );
    }

    if (modes_present) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-modes-present"
        );
    }

    if (preferred_mode_present) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-preferred-mode"
        );
    }

    if (encoders_present) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-encoders-present"
        );
    }

    if (encoder_query_ok) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-encoder-query-ok"
        );
    }

    if (compatible_crtc) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-compatible-crtc"
        );
    }
}



static int tf_drm_menu_begin(
    long drm_fd
) {
    /*
     * Build a complete TreeForge-owned KMS state and ask the kernel
     * to validate it with TEST_ONLY.
     *
     * This allocates DRM objects but makes no hardware/display change.
     */

    static struct tf_drm_mode_card_res resources;

    static u32 crtc_ids[
        TF_DRM_RESOURCE_LIMIT
    ];

    static u32 connector_ids[
        TF_DRM_RESOURCE_LIMIT
    ];

    resources.fb_id_ptr = 0;
    resources.crtc_id_ptr = 0;
    resources.connector_id_ptr = 0;
    resources.encoder_id_ptr = 0;

    resources.count_fbs = 0;
    resources.count_crtcs = 0;
    resources.count_connectors = 0;
    resources.count_encoders = 0;

    long result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (
        result < 0
        || resources.count_crtcs == 0
        || resources.count_connectors == 0
        || resources.count_crtcs > TF_DRM_RESOURCE_LIMIT
        || resources.count_connectors > TF_DRM_RESOURCE_LIMIT
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-test-resources-failed"
        );

        return 0;
    }

    u32 crtc_count = resources.count_crtcs;
    u32 connector_count = resources.count_connectors;

    resources.crtc_id_ptr = (
        (u64) (usize) crtc_ids
    );

    resources.connector_id_ptr = (
        (u64) (usize) connector_ids
    );

    resources.count_fbs = 0;
    resources.count_crtcs = crtc_count;
    resources.count_connectors = connector_count;
    resources.count_encoders = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (result < 0) {
        return 0;
    }

    u32 selected_connector = 0;
    u32 selected_crtc = 0;
    u32 selected_crtc_index = 0;

    static struct tf_drm_mode_modeinfo selected_mode;

    static struct tf_drm_mode_get_connector connector;

    static struct tf_drm_mode_modeinfo modes[
        TF_DRM_MODE_LIMIT
    ];

    static u32 encoder_ids[
        TF_DRM_ENCODER_LIMIT
    ];

    for (
        u32 connector_index = 0;
        connector_index < connector_count;
        connector_index++
    ) {
        connector.encoders_ptr = 0;
        connector.modes_ptr = 0;
        connector.props_ptr = 0;
        connector.prop_values_ptr = 0;

        connector.count_modes = 0;
        connector.count_props = 0;
        connector.count_encoders = 0;
        connector.connector_id = connector_ids[connector_index];

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETCONNECTOR,
            &connector
        );

        if (
            result < 0
            || connector.connection
                != TF_DRM_CONNECTOR_CONNECTED
            || connector.count_modes == 0
            || connector.count_modes > TF_DRM_MODE_LIMIT
            || connector.count_encoders > TF_DRM_ENCODER_LIMIT
        ) {
            continue;
        }

        u32 mode_count = connector.count_modes;
        u32 encoder_count = connector.count_encoders;

        connector.modes_ptr = (
            (u64) (usize) modes
        );

        connector.encoders_ptr = (
            encoder_count > 0
            ? (u64) (usize) encoder_ids
            : 0
        );

        connector.count_modes = mode_count;
        connector.count_encoders = encoder_count;
        connector.count_props = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETCONNECTOR,
            &connector
        );

        if (result < 0) {
            continue;
        }

        u32 mode_index = 0;

        for (
            u32 index = 0;
            index < connector.count_modes;
            index++
        ) {
            if (
                modes[index].type
                & TF_DRM_MODE_TYPE_PREFERRED
            ) {
                mode_index = index;
                break;
            }
        }

        for (
            u32 encoder_index = 0;
            encoder_index < connector.count_encoders;
            encoder_index++
        ) {
            struct tf_drm_mode_get_encoder encoder;

            encoder.encoder_id = encoder_ids[encoder_index];

            result = tf_recovery_ui_ioctl(
                drm_fd,
                TF_DRM_IOCTL_MODE_GETENCODER,
                &encoder
            );

            if (result < 0) {
                continue;
            }

            for (
                u32 crtc_index = 0;
                crtc_index < crtc_count;
                crtc_index++
            ) {
                if (
                    encoder.possible_crtcs
                    & (1U << crtc_index)
                ) {
                    selected_connector = (
                        connector.connector_id
                    );

                    selected_crtc = (
                        crtc_ids[crtc_index]
                    );

                    selected_crtc_index = crtc_index;
                    selected_mode = modes[mode_index];

                    break;
                }
            }

            if (selected_crtc != 0) {
                break;
            }
        }

        if (selected_crtc != 0) {
            break;
        }
    }

    if (
        selected_connector == 0
        || selected_crtc == 0
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-test-route-failed"
        );

        return 0;
    }

    /*
     * Find a compatible Primary plane.
     */
    static struct tf_drm_mode_get_plane_res plane_resources;

    static u32 plane_ids[
        TF_DRM_PLANE_LIMIT
    ];

    plane_resources.plane_id_ptr = 0;
    plane_resources.count_planes = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETPLANERESOURCES,
        &plane_resources
    );

    if (
        result < 0
        || plane_resources.count_planes == 0
        || plane_resources.count_planes > TF_DRM_PLANE_LIMIT
    ) {
        return 0;
    }

    u32 plane_count = plane_resources.count_planes;

    plane_resources.plane_id_ptr = (
        (u64) (usize) plane_ids
    );

    plane_resources.count_planes = plane_count;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETPLANERESOURCES,
        &plane_resources
    );

    if (result < 0) {
        return 0;
    }

    u32 selected_plane = 0;

    static u32 formats[64];

    for (
        u32 plane_index = 0;
        plane_index < plane_resources.count_planes;
        plane_index++
    ) {
        struct tf_drm_mode_get_plane plane;

        plane.plane_id = plane_ids[plane_index];
        plane.count_format_types = 0;
        plane.format_type_ptr = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETPLANE,
            &plane
        );

        if (
            result < 0
            || !(plane.possible_crtcs
                & (1U << selected_crtc_index))
            || plane.count_format_types == 0
            || plane.count_format_types > 64
        ) {
            continue;
        }

        u64 type_value = 0;

        u32 type_property = tf_drm_find_property(
            drm_fd,
            plane.plane_id,
            TF_DRM_MODE_OBJECT_PLANE,
            "type",
            &type_value
        );

        if (
            type_property == 0
            || type_value
                != TF_DRM_PLANE_TYPE_PRIMARY
        ) {
            continue;
        }

        u32 format_count = plane.count_format_types;

        plane.count_format_types = format_count;
        plane.format_type_ptr = (
            (u64) (usize) formats
        );

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETPLANE,
            &plane
        );

        if (result < 0) {
            continue;
        }

        int supports_xrgb8888 = 0;

        for (
            u32 format_index = 0;
            format_index < plane.count_format_types;
            format_index++
        ) {
            if (
                formats[format_index]
                == TF_DRM_FORMAT_XRGB8888
            ) {
                supports_xrgb8888 = 1;
                break;
            }
        }

        if (!supports_xrgb8888) {
            continue;
        }

        selected_plane = plane.plane_id;
        break;
    }

    if (selected_plane == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-test-primary-plane-failed"
        );

        return 0;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-primary-plane-ok"
    );

    tf_probe_drm_orientation_state(
        drm_fd,
        selected_connector,
        selected_plane,
        &selected_mode
    );

    /*
     * Native-coordinate menu checkpoint.
     *
     * The first-pixel commit has already been proven. Continue using
     * the kernel's native hdisplay/vdisplay coordinates directly.
     * No rotation transform is applied.
     */

    /*
     * Required standardized atomic properties.
     */
    u32 connector_crtc = tf_drm_find_property(
        drm_fd,
        selected_connector,
        TF_DRM_MODE_OBJECT_CONNECTOR,
        "CRTC_ID",
        0
    );

    u32 crtc_mode = tf_drm_find_property(
        drm_fd,
        selected_crtc,
        TF_DRM_MODE_OBJECT_CRTC,
        "MODE_ID",
        0
    );

    u32 crtc_active = tf_drm_find_property(
        drm_fd,
        selected_crtc,
        TF_DRM_MODE_OBJECT_CRTC,
        "ACTIVE",
        0
    );

    u32 plane_fb = tf_drm_find_property(
        drm_fd,
        selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "FB_ID",
        0
    );

    u32 plane_crtc = tf_drm_find_property(
        drm_fd,
        selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "CRTC_ID",
        0
    );

    u32 plane_src_x = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "SRC_X", 0
    );

    u32 plane_src_y = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "SRC_Y", 0
    );

    u32 plane_src_w = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "SRC_W", 0
    );

    u32 plane_src_h = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "SRC_H", 0
    );

    u32 plane_crtc_x = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "CRTC_X", 0
    );

    u32 plane_crtc_y = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "CRTC_Y", 0
    );

    u32 plane_crtc_w = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "CRTC_W", 0
    );

    u32 plane_crtc_h = tf_drm_find_property(
        drm_fd, selected_plane,
        TF_DRM_MODE_OBJECT_PLANE,
        "CRTC_H", 0
    );

    if (
        connector_crtc == 0
        || crtc_mode == 0
        || crtc_active == 0
        || plane_fb == 0
        || plane_crtc == 0
        || plane_src_x == 0
        || plane_src_y == 0
        || plane_src_w == 0
        || plane_src_h == 0
        || plane_crtc_x == 0
        || plane_crtc_y == 0
        || plane_crtc_w == 0
        || plane_crtc_h == 0
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-properties-failed"
        );

        return 0;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-atomic-properties-ok"
    );

    /*
     * Mode blob.
     */
    struct tf_drm_mode_create_blob blob;

    blob.data = (
        (u64) (usize) &selected_mode
    );

    blob.length = sizeof(selected_mode);
    blob.blob_id = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_CREATEPROPBLOB,
        &blob
    );

    if (result < 0 || blob.blob_id == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-mode-blob-failed"
        );

        return 0;
    }

    /*
     * Dumb buffer.
     */
    struct tf_drm_mode_create_dumb dumb;

    dumb.height = selected_mode.vdisplay;
    dumb.width = selected_mode.hdisplay;
    dumb.bpp = 32;
    dumb.flags = 0;
    dumb.handle = 0;
    dumb.pitch = 0;
    dumb.size = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_CREATE_DUMB,
        &dumb
    );

    if (result < 0 || dumb.handle == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-dumb-create-failed"
        );

        struct tf_drm_mode_destroy_blob destroy_blob;
        destroy_blob.blob_id = blob.blob_id;

        tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_DESTROYPROPBLOB,
            &destroy_blob
        );

        return 0;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-dumb-create-ok"
    );

    /*
     * Register the dumb BO as an XRGB8888 framebuffer.
     */
    struct tf_drm_mode_fb_cmd2 framebuffer;

    framebuffer.fb_id = 0;
    framebuffer.width = selected_mode.hdisplay;
    framebuffer.height = selected_mode.vdisplay;
    framebuffer.pixel_format = TF_DRM_FORMAT_XRGB8888;
    framebuffer.flags = 0;

    for (
        int index = 0;
        index < 4;
        index++
    ) {
        framebuffer.handles[index] = 0;
        framebuffer.pitches[index] = 0;
        framebuffer.offsets[index] = 0;
        framebuffer.modifier[index] = 0;
    }

    framebuffer.handles[0] = dumb.handle;
    framebuffer.pitches[0] = dumb.pitch;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_ADDFB2,
        &framebuffer
    );

    if (
        result < 0
        || framebuffer.fb_id == 0
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-addfb2-failed"
        );

        struct tf_drm_mode_destroy_dumb destroy_dumb;
        destroy_dumb.handle = dumb.handle;

        tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_DESTROY_DUMB,
            &destroy_dumb
        );

        struct tf_drm_mode_destroy_blob destroy_blob;
        destroy_blob.blob_id = blob.blob_id;

        tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_DESTROYPROPBLOB,
            &destroy_blob
        );

        return 0;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-addfb2-ok"
    );

    /*
     * Atomic state:
     *
     * connector:
     *   CRTC_ID
     *
     * CRTC:
     *   MODE_ID
     *   ACTIVE
     *
     * primary plane:
     *   FB_ID / CRTC_ID
     *   full-screen source and destination rectangles
     */
    static u32 objects[3];

    static u32 property_counts[3];

    static u32 properties[13];

    static u64 values[13];

    objects[0] = selected_connector;
    objects[1] = selected_crtc;
    objects[2] = selected_plane;

    property_counts[0] = 1;
    property_counts[1] = 2;
    property_counts[2] = 10;

    int property_index = 0;

    properties[property_index] = connector_crtc;
    values[property_index++] = selected_crtc;

    properties[property_index] = crtc_mode;
    values[property_index++] = blob.blob_id;

    properties[property_index] = crtc_active;
    values[property_index++] = 1;

    properties[property_index] = plane_fb;
    values[property_index++] = framebuffer.fb_id;

    properties[property_index] = plane_crtc;
    values[property_index++] = selected_crtc;

    properties[property_index] = plane_src_x;
    values[property_index++] = 0;

    properties[property_index] = plane_src_y;
    values[property_index++] = 0;

    properties[property_index] = plane_src_w;
    values[property_index++] = (
        ((u64) selected_mode.hdisplay) << 16
    );

    properties[property_index] = plane_src_h;
    values[property_index++] = (
        ((u64) selected_mode.vdisplay) << 16
    );

    properties[property_index] = plane_crtc_x;
    values[property_index++] = 0;

    properties[property_index] = plane_crtc_y;
    values[property_index++] = 0;

    properties[property_index] = plane_crtc_w;
    values[property_index++] = selected_mode.hdisplay;

    properties[property_index] = plane_crtc_h;
    values[property_index++] = selected_mode.vdisplay;

    struct tf_drm_mode_atomic atomic;

    atomic.flags = (
        TF_DRM_MODE_ATOMIC_TEST_ONLY
        | TF_DRM_MODE_ATOMIC_ALLOW_MODESET
    );

    atomic.count_objs = 3;
    atomic.objs_ptr = (u64) (usize) objects;
    atomic.count_props_ptr = (
        (u64) (usize) property_counts
    );
    atomic.props_ptr = (
        (u64) (usize) properties
    );
    atomic.prop_values_ptr = (
        (u64) (usize) values
    );
    atomic.reserved = 0;
    atomic.user_data = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_ATOMIC,
        &atomic
    );

    if (result == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-test-ok"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-test-failed"
        );
    }

    /*
     * The prospective state has passed TEST_ONLY.
     *
     * For the first visible TreeForge display checkpoint, map the dumb
     * buffer, paint an unmistakable software-rendered RGB test image,
     * apply the exact state for real, keep it visible briefly, then
     * disable only the TreeForge-owned KMS state before Android
     * continues.
     */

    int real_scanout_active = 0;
    long mapped_address = -1;

    if (result == 0) {
        struct tf_drm_mode_map_dumb map_dumb;

        map_dumb.handle = dumb.handle;
        map_dumb.pad = 0;
        map_dumb.offset = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_MAP_DUMB,
            &map_dumb
        );

        if (result == 0) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-drm-map-dumb-ok"
            );

            mapped_address = tf_recovery_ui_syscall6(
                SYS_MMAP,
                0,
                (long) dumb.size,
                PROT_READ | PROT_WRITE,
                MAP_SHARED,
                drm_fd,
                (long) map_dumb.offset
            );

            if (mapped_address >= 0) {
                tf_recovery_ui_create_presence_marker(
                    "/dev/treeforge-display-drm-mmap-ok"
                );

                /*
                 * XRGB8888 test pattern:
                 *
                 *   left third   red
                 *   middle       green
                 *   right third  blue
                 *
                 * Use the driver-provided pitch rather than assuming
                 * tightly packed rows.
                 */
                volatile unsigned char *base = (
                    (volatile unsigned char *)
                    (usize) mapped_address
                );

                u32 width = selected_mode.hdisplay;
                u32 height = selected_mode.vdisplay;

                for (
                    u32 y = 0;
                    y < height;
                    y++
                ) {
                    volatile u32 *row = (
                        (volatile u32 *)
                        (
                            base
                            + (
                                (usize) y
                                * (usize) dumb.pitch
                            )
                        )
                    );

                    for (
                        u32 x = 0;
                        x < width;
                        x++
                    ) {
                        u32 pixel;

                        if (
                            x
                            < (
                                width
                                / 3U
                            )
                        ) {
                            pixel = 0x00ff0000U;
                        } else if (
                            x
                            < (
                                (
                                    width
                                    * 2U
                                )
                                / 3U
                            )
                        ) {
                            pixel = 0x0000ff00U;
                        } else {
                            pixel = 0x000000ffU;
                        }

                        row[x] = pixel;
                    }
                }

                tf_recovery_ui_create_presence_marker(
                    "/dev/treeforge-display-drm-pattern-rendered"
                );

                /*
                 * Apply the exact state that already passed TEST_ONLY.
                 */
                atomic.flags = (
                    TF_DRM_MODE_ATOMIC_ALLOW_MODESET
                );

                result = tf_recovery_ui_ioctl(
                    drm_fd,
                    TF_DRM_IOCTL_MODE_ATOMIC,
                    &atomic
                );

                if (result == 0) {
                    real_scanout_active = 1;

                    tf_recovery_ui_create_presence_marker(
                        "/dev/treeforge-display-drm-real-commit-ok"
                    );

                    /*
                     * The real commit is now retained for the entire
                     * interactive TreeForge menu session.
                     */
                } else {
                    tf_recovery_ui_create_presence_marker(
                        "/dev/treeforge-display-drm-real-commit-failed"
                    );
                }
            } else {
                tf_recovery_ui_create_presence_marker(
                    "/dev/treeforge-display-drm-mmap-failed"
                );
            }
        } else {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-drm-map-dumb-failed"
            );
        }
    }

    if (
        real_scanout_active
        && mapped_address >= 0
    ) {
        tf_drm_menu_fd = drm_fd;
        tf_drm_menu_active = 1;

        tf_drm_menu_mapped_address = (
            mapped_address
        );

        tf_drm_menu_mapped_size = (
            dumb.size
        );

        tf_drm_menu_width = (
            selected_mode.hdisplay
        );

        tf_drm_menu_height = (
            selected_mode.vdisplay
        );

        tf_drm_menu_pitch = (
            dumb.pitch
        );

        tf_drm_menu_framebuffer_id = (
            framebuffer.fb_id
        );

        tf_drm_menu_dumb_handle = (
            dumb.handle
        );

        tf_drm_menu_blob_id = (
            blob.blob_id
        );

        tf_drm_menu_connector = (
            selected_connector
        );

        tf_drm_menu_crtc = (
            selected_crtc
        );

        tf_drm_menu_plane = (
            selected_plane
        );

        tf_drm_menu_connector_crtc_property = (
            connector_crtc
        );

        tf_drm_menu_crtc_mode_property = (
            crtc_mode
        );

        tf_drm_menu_crtc_active_property = (
            crtc_active
        );

        tf_drm_menu_plane_fb_property = (
            plane_fb
        );

        tf_drm_menu_plane_crtc_property = (
            plane_crtc
        );

        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-menu-session-active"
        );

        return 1;
    }

    /*
     * A failed retained-session start owns no persistent KMS state.
     * Release everything allocated during the attempt.
     */
    if (mapped_address >= 0) {
        tf_recovery_ui_syscall2(
            SYS_MUNMAP,
            mapped_address,
            (long) dumb.size
        );
    }

    u32 framebuffer_id = (
        framebuffer.fb_id
    );

    tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_RMFB,
        &framebuffer_id
    );

    struct tf_drm_mode_destroy_dumb destroy_dumb;
    destroy_dumb.handle = dumb.handle;

    tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_DESTROY_DUMB,
        &destroy_dumb
    );

    struct tf_drm_mode_destroy_blob destroy_blob;
    destroy_blob.blob_id = blob.blob_id;

    tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_DESTROYPROPBLOB,
        &destroy_blob
    );

    return 0;
}


static void tf_drm_menu_cleanup(void) {
    if (!tf_drm_menu_active) {
        return;
    }

    /*
     * Disable only the KMS state TreeForge installed.
     */
    u32 objects[3] = {
        tf_drm_menu_connector,
        tf_drm_menu_crtc,
        tf_drm_menu_plane,
    };

    u32 property_counts[3] = {
        1,
        2,
        2,
    };

    u32 properties[5] = {
        tf_drm_menu_connector_crtc_property,
        tf_drm_menu_crtc_mode_property,
        tf_drm_menu_crtc_active_property,
        tf_drm_menu_plane_fb_property,
        tf_drm_menu_plane_crtc_property,
    };

    u64 values[5] = {
        0,
        0,
        0,
        0,
        0,
    };

    struct tf_drm_mode_atomic atomic;

    atomic.flags = (
        TF_DRM_MODE_ATOMIC_ALLOW_MODESET
    );

    atomic.count_objs = 3;
    atomic.objs_ptr = (
        (u64) (usize) objects
    );
    atomic.count_props_ptr = (
        (u64) (usize) property_counts
    );
    atomic.props_ptr = (
        (u64) (usize) properties
    );
    atomic.prop_values_ptr = (
        (u64) (usize) values
    );
    atomic.reserved = 0;
    atomic.user_data = 0;

    long result = tf_recovery_ui_ioctl(
        tf_drm_menu_fd,
        TF_DRM_IOCTL_MODE_ATOMIC,
        &atomic
    );

    if (result == 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-menu-disable-ok"
        );
    } else {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-menu-disable-failed"
        );
    }

    if (
        tf_drm_menu_mapped_address >= 0
    ) {
        tf_recovery_ui_syscall2(
            SYS_MUNMAP,
            tf_drm_menu_mapped_address,
            (long) tf_drm_menu_mapped_size
        );
    }

    if (
        tf_drm_menu_framebuffer_id != 0
    ) {
        u32 framebuffer_id = (
            tf_drm_menu_framebuffer_id
        );

        tf_recovery_ui_ioctl(
            tf_drm_menu_fd,
            TF_DRM_IOCTL_MODE_RMFB,
            &framebuffer_id
        );
    }

    if (
        tf_drm_menu_dumb_handle != 0
    ) {
        struct tf_drm_mode_destroy_dumb destroy_dumb;

        destroy_dumb.handle = (
            tf_drm_menu_dumb_handle
        );

        tf_recovery_ui_ioctl(
            tf_drm_menu_fd,
            TF_DRM_IOCTL_MODE_DESTROY_DUMB,
            &destroy_dumb
        );
    }

    if (
        tf_drm_menu_blob_id != 0
    ) {
        struct tf_drm_mode_destroy_blob destroy_blob;

        destroy_blob.blob_id = (
            tf_drm_menu_blob_id
        );

        tf_recovery_ui_ioctl(
            tf_drm_menu_fd,
            TF_DRM_IOCTL_MODE_DESTROYPROPBLOB,
            &destroy_blob
        );
    }

    tf_close(
        tf_drm_menu_fd
    );

    tf_cleanup_drm_card0(
        tf_drm_menu_created_dri_directory,
        tf_drm_menu_created_card0
    );

    tf_drm_menu_fd = -1;
    tf_drm_menu_active = 0;
    tf_drm_menu_mapped_address = -1;
    tf_drm_menu_mapped_size = 0;

    tf_drm_menu_width = 0;
    tf_drm_menu_height = 0;
    tf_drm_menu_pitch = 0;

    tf_drm_menu_framebuffer_id = 0;
    tf_drm_menu_dumb_handle = 0;
    tf_drm_menu_blob_id = 0;

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-menu-cleanup"
    );
}


static void tf_probe_drm_kms_state(
    long drm_fd
) {
    /*
     * Read-only KMS interrogation.
     *
     * No modeset, framebuffer creation, master acquisition,
     * property mutation, or atomic commit occurs here.
     */

    static struct tf_drm_mode_card_res resources;

    static u32 crtc_ids[
        TF_DRM_RESOURCE_LIMIT
    ];

    static u32 connector_ids[
        TF_DRM_RESOURCE_LIMIT
    ];

    resources.fb_id_ptr = 0;
    resources.crtc_id_ptr = 0;
    resources.connector_id_ptr = 0;
    resources.encoder_id_ptr = 0;

    resources.count_fbs = 0;
    resources.count_crtcs = 0;
    resources.count_connectors = 0;
    resources.count_encoders = 0;

    long result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (result < 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-resources-failed"
        );

        return;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-resources-ok"
    );

    u32 crtc_count = (
        resources.count_crtcs
    );

    u32 connector_count = (
        resources.count_connectors
    );

    if (resources.count_fbs > 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-framebuffers-present"
        );
    }

    if (crtc_count > 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-crtcs-present"
        );
    }

    if (connector_count > 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-connectors-present"
        );
    }

    if (
        crtc_count > TF_DRM_RESOURCE_LIMIT
        || connector_count > TF_DRM_RESOURCE_LIMIT
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-resource-overflow"
        );

        return;
    }

    resources.fb_id_ptr = 0;

    resources.crtc_id_ptr = (
        crtc_count > 0
        ? (u64) (usize) crtc_ids
        : 0
    );

    resources.connector_id_ptr = (
        connector_count > 0
        ? (u64) (usize) connector_ids
        : 0
    );

    resources.encoder_id_ptr = 0;

    resources.count_fbs = 0;
    resources.count_crtcs = crtc_count;
    resources.count_connectors = connector_count;
    resources.count_encoders = 0;

    result = tf_recovery_ui_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (result < 0) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-resource-ids-failed"
        );

        return;
    }

    /*
     * A hotplug race could increase the population between the two
     * GETRESOURCES calls. Do not inspect a partial identifier array.
     */
    if (
        resources.count_crtcs > crtc_count
        || resources.count_connectors > connector_count
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-resource-race"
        );

        return;
    }

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-drm-resource-ids-ok"
    );

    int queried_crtc = 0;
    int active_crtc = 0;
    int active_framebuffer = 0;

    static struct tf_drm_mode_crtc crtc;

    for (
        u32 index = 0;
        index < crtc_count;
        index++
    ) {
        crtc.set_connectors_ptr = 0;
        crtc.count_connectors = 0;
        crtc.crtc_id = crtc_ids[index];

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETCRTC,
            &crtc
        );

        if (result < 0) {
            continue;
        }

        queried_crtc = 1;

        if (crtc.mode_valid) {
            active_crtc = 1;
        }

        if (crtc.fb_id != 0) {
            active_framebuffer = 1;
        }
    }

    if (queried_crtc) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-crtc-query-ok"
        );
    }

    if (active_crtc) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-crtc-active"
        );
    }

    if (active_framebuffer) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-crtc-framebuffer"
        );
    }

    int queried_connector = 0;
    int connected_connector = 0;
    int connector_modes = 0;
    int connector_encoder = 0;

    static struct tf_drm_mode_get_connector connector;
    static struct tf_drm_mode_modeinfo temporary_mode;

    for (
        u32 index = 0;
        index < connector_count;
        index++
    ) {
        connector.encoders_ptr = 0;

        /*
         * Keep count_modes nonzero so this GETCONNECTOR does not
         * request a forced connector probe.
         */
        connector.modes_ptr = (
            (u64) (usize) &temporary_mode
        );

        connector.props_ptr = 0;
        connector.prop_values_ptr = 0;

        connector.count_modes = 1;
        connector.count_props = 0;
        connector.count_encoders = 0;

        connector.encoder_id = 0;
        connector.connector_id = (
            connector_ids[index]
        );

        connector.connector_type = 0;
        connector.connector_type_id = 0;
        connector.connection = 0;
        connector.mm_width = 0;
        connector.mm_height = 0;
        connector.subpixel = 0;
        connector.pad = 0;

        result = tf_recovery_ui_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_GETCONNECTOR,
            &connector
        );

        if (result < 0) {
            continue;
        }

        queried_connector = 1;

        if (
            connector.connection
            == TF_DRM_CONNECTOR_CONNECTED
        ) {
            connected_connector = 1;
        }

        if (connector.count_modes > 0) {
            connector_modes = 1;
        }

        if (connector.encoder_id != 0) {
            connector_encoder = 1;
        }
    }

    if (queried_connector) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-connector-query-ok"
        );
    }

    if (connected_connector) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-connector-connected"
        );
    }

    if (connector_modes) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-connector-modes"
        );
    }

    if (connector_encoder) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-connector-encoder"
        );
    }
}


static void tf_probe_display_surfaces(void) {
    /*
     * Presence-only display discovery at TreeForge's exact
     * post-FirstStageMain / pre-selinux_setup boundary.
     *
     * These probes deliberately use only generic Linux display
     * interfaces. They do not infer a device, GPU, panel, DRM
     * driver, connector name, or framebuffer implementation.
     */

    tf_recovery_ui_create_presence_marker(
        "/dev/treeforge-display-probe-v1"
    );

    if (
        tf_recovery_ui_probe_readable_path(
            "/sys/class/graphics/fb0/dev"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-fb0-sysfs"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/dev/fb0"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-fb0-node"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/dev/graphics/fb0"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-graphics-fb0-node"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/sys/class/drm/card0/dev"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card0-sysfs"
        );
    }

    int created_dri_directory = 0;
    int created_drm_card0 = 0;

    if (
        tf_realize_drm_card0(
            &created_dri_directory,
            &created_drm_card0
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card0-opened"
        );

        if (created_drm_card0) {
            tf_recovery_ui_create_presence_marker(
                "/dev/treeforge-display-drm-card0-created"
            );
        }

        long drm_fd = tf_open(
            "/dev/dri/card0",
            O_RDWR
            | O_NONBLOCK
        );

        if (drm_fd >= 0) {
            tf_probe_drm_kms_state(
                drm_fd
            );

            tf_probe_drm_plane_state(
                drm_fd
            );

            tf_probe_drm_scanout_requirements(
                drm_fd
            );

            if (
                tf_drm_menu_begin(
                    drm_fd
                )
            ) {
                tf_drm_menu_created_dri_directory = (
                    created_dri_directory
                );

                tf_drm_menu_created_card0 = (
                    created_drm_card0
                );

                /*
                 * Ownership moved into the retained menu session.
                 */
                drm_fd = -1;
            }

            if (drm_fd >= 0) {
                tf_close(
                    drm_fd
                );
            }
        }
    }

    if (!tf_drm_menu_active) {
        tf_cleanup_drm_card0(
            created_dri_directory,
            created_drm_card0
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/sys/class/drm/card1/dev"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card1-sysfs"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/sys/class/drm/card2/dev"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card2-sysfs"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/sys/class/drm/card3/dev"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card3-sysfs"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/dev/dri/card0"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card0-node"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/dev/dri/card1"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card1-node"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/dev/dri/card2"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card2-node"
        );
    }

    if (
        tf_recovery_ui_probe_readable_path(
            "/dev/dri/card3"
        )
    ) {
        tf_recovery_ui_create_presence_marker(
            "/dev/treeforge-display-drm-card3-node"
        );
    }
}






static long tf_recovery_ui_tty = -1;
static long tf_recovery_ui_console = -1;
static long tf_recovery_ui_kmsg = -1;


static void tf_recovery_ui_output(
    const char *value
) {
    if (!value) {
        return;
    }

    usize length = tf_strlen(
        value
    );

    tf_write_buffer(
        tf_recovery_ui_tty,
        value,
        length
    );

    tf_write_buffer(
        tf_recovery_ui_console,
        value,
        length
    );
}


static void tf_recovery_ui_log(
    const char *value
) {
    if (
        tf_recovery_ui_kmsg < 0
        || !value
    ) {
        return;
    }

    static const char prefix[] =
        "<6>treeforge-recovery: ";

    tf_write_buffer(
        tf_recovery_ui_kmsg,
        prefix,
        sizeof(prefix) - 1
    );

    tf_write_buffer(
        tf_recovery_ui_kmsg,
        value,
        tf_strlen(value)
    );

    static const char newline[] =
        "\n";

    tf_write_buffer(
        tf_recovery_ui_kmsg,
        newline,
        1
    );
}


static u32 tf_recovery_ui_scale(void) {
    u32 scale = (
        tf_drm_menu_width
        / 160U
    );

    u32 height_scale = (
        tf_drm_menu_height
        / 220U
    );

    if (height_scale < scale) {
        scale = height_scale;
    }

    if (scale < 2U) {
        scale = 2U;
    }

    if (scale > 8U) {
        scale = 8U;
    }

    return scale;
}


static void tf_recovery_ui_draw_menu(
    const char *title,
    const char *subtitle,
    const char *const *items,
    int count,
    int selected
) {
    tf_recovery_ui_output(
        "\033[2J\033[H"
    );

    tf_recovery_ui_output(
        title
    );

    tf_recovery_ui_output(
        "\n"
    );

    if (
        subtitle
        && subtitle[0]
    ) {
        tf_recovery_ui_output(
            subtitle
        );

        tf_recovery_ui_output(
            "\n"
        );
    }

    tf_recovery_ui_output(
        "\n"
    );

    for (
        int index = 0;
        index < count;
        index++
    ) {
        tf_recovery_ui_output(
            index == selected
            ? "> "
            : "  "
        );

        tf_recovery_ui_output(
            items[index]
        );

        tf_recovery_ui_output(
            "\n"
        );
    }

    tf_recovery_ui_output(
        "\n"
        "Volume Up/Down: navigate\n"
        "Power: select\n"
    );

    if (
        !tf_drm_menu_active
        || tf_drm_menu_mapped_address < 0
    ) {
        return;
    }

    const u32 background = 0x00000000U;
    const u32 foreground = 0x00ffffffU;
    const u32 inactive = 0x00282828U;

    tf_drm_fill_rect(
        0,
        0,
        tf_drm_menu_width,
        tf_drm_menu_height,
        background
    );

    u32 scale = (
        tf_recovery_ui_scale()
    );

    tf_drm_draw_management_line(
        title,
        18U * scale,
        scale,
        foreground
    );

    if (
        subtitle
        && subtitle[0]
    ) {
        tf_drm_draw_management_line(
            subtitle,
            32U * scale,
            scale,
            foreground
        );
    }

    u32 row_height = (
        13U * scale
    );

    u32 row_gap = (
        4U * scale
    );

    u32 box_x = (
        tf_drm_menu_width
        / 10U
    );

    u32 box_width = (
        tf_drm_menu_width
        - box_x * 2U
    );

    u32 rows_y = (
        52U * scale
    );

    for (
        int index = 0;
        index < count;
        index++
    ) {
        u32 row_y = (
            rows_y
            + (
                (u32) index
                * (
                    row_height
                    + row_gap
                )
            )
        );

        int active = (
            index == selected
        );

        tf_drm_fill_rect(
            box_x,
            row_y,
            box_width,
            row_height,
            active
            ? foreground
            : inactive
        );

        u32 item_scale = scale;

        while (
            item_scale > 2U
            && tf_drm_text_width(
                items[index],
                item_scale
            )
            > (
                box_width
                - 8U * scale
            )
        ) {
            item_scale--;
        }

        u32 width = (
            tf_drm_text_width(
                items[index],
                item_scale
            )
        );

        u32 x = (
            tf_drm_menu_width > width
            ? (
                tf_drm_menu_width
                - width
            ) / 2U
            : box_x
        );

        u32 glyph_height = (
            7U * item_scale
        );

        u32 y = (
            row_y
            + (
                row_height > glyph_height
                ? (
                    row_height
                    - glyph_height
                ) / 2U
                : 0
            )
        );

        tf_drm_draw_text(
            x,
            y,
            items[index],
            item_scale,
            active
            ? background
            : foreground
        );
    }

    tf_drm_draw_management_line(
        "VOL +/-: NAVIGATE   POWER: SELECT",
        190U * scale,
        scale,
        foreground
    );
}


static void tf_recovery_ui_draw_info(
    const char *title,
    const char *const *lines,
    int count,
    const char *footer
) {
    tf_recovery_ui_output(
        "\033[2J\033[H"
    );

    tf_recovery_ui_output(
        title
    );

    tf_recovery_ui_output(
        "\n\n"
    );

    for (
        int index = 0;
        index < count;
        index++
    ) {
        tf_recovery_ui_output(
            lines[index]
        );

        tf_recovery_ui_output(
            "\n"
        );
    }

    if (footer) {
        tf_recovery_ui_output(
            "\n"
        );

        tf_recovery_ui_output(
            footer
        );

        tf_recovery_ui_output(
            "\n"
        );
    }

    if (
        !tf_drm_menu_active
        || tf_drm_menu_mapped_address < 0
    ) {
        return;
    }

    const u32 background = 0x00000000U;
    const u32 foreground = 0x00ffffffU;

    tf_drm_fill_rect(
        0,
        0,
        tf_drm_menu_width,
        tf_drm_menu_height,
        background
    );

    u32 scale = (
        tf_recovery_ui_scale()
    );

    tf_drm_draw_management_line(
        title,
        18U * scale,
        scale,
        foreground
    );

    for (
        int index = 0;
        index < count;
        index++
    ) {
        tf_drm_draw_management_line(
            lines[index],
            (
                48U
                + (u32) index * 13U
            ) * scale,
            scale,
            foreground
        );
    }

    if (footer) {
        tf_drm_draw_management_line(
            footer,
            204U * scale,
            scale,
            foreground
        );
    }
}



static void tf_recovery_ui_highlight_info_line(
    const char *value,
    int line_index
) {
    if (
        !value
        || line_index < 0
        || !tf_drm_menu_active
        || tf_drm_menu_mapped_address < 0
    ) {
        return;
    }

    const u32 background = 0x00000000U;
    const u32 foreground = 0x00ffffffU;

    u32 scale = tf_recovery_ui_scale();

    u32 box_x = (
        tf_drm_menu_width
        / 10U
    );

    u32 box_width = (
        tf_drm_menu_width
        - box_x * 2U
    );

    u32 text_y = (
        (
            48U
            + (u32) line_index * 13U
        )
        * scale
    );

    u32 box_y = (
        text_y > scale
        ? text_y - scale
        : text_y
    );

    u32 box_height = (
        9U * scale
    );

    tf_drm_fill_rect(
        box_x,
        box_y,
        box_width,
        box_height,
        foreground
    );

    u32 item_scale = scale;

    while (
        item_scale > 2U
        && tf_drm_text_width(
            value,
            item_scale
        ) > (
            box_width
            - 8U * scale
        )
    ) {
        item_scale--;
    }

    u32 width = tf_drm_text_width(
        value,
        item_scale
    );

    u32 x = (
        tf_drm_menu_width > width
        ? (
            tf_drm_menu_width
            - width
        ) / 2U
        : box_x
    );

    tf_drm_draw_text(
        x,
        text_y,
        value,
        item_scale,
        background
    );
}



static void tf_recovery_ui_active_slot_line(
    char *line,
    usize capacity
) {
    if (
        !line
        || capacity == 0
    ) {
        return;
    }

    line[0] = '\0';

    usize position = 0;

    position = tf_append_text(
        line,
        capacity,
        position,
        "ACTIVE SLOT: "
    );

    if (
        tf_recovery_inventory
        .active_slot_resolved
    ) {
        char slot[2];

        slot[0] = (
            tf_recovery_inventory
            .active_slot
            == 'a'
            ? 'A'
            : 'B'
        );

        slot[1] = '\0';

        tf_append_text(
            line,
            capacity,
            position,
            slot
        );
    } else {
        tf_append_text(
            line,
            capacity,
            position,
            "UNKNOWN"
        );
    }
}


static void tf_recovery_ui_open_inputs(
    long *inputs
) {
    for (
        int index = 0;
        index
            < TREEFORGE_RECOVERY_UI_INPUT_COUNT;
        index++
    ) {
        inputs[index] = -1;

        char path[32];

        tf_recovery_ui_event_path(
            index,
            path
        );

        inputs[index] = tf_open(
            path,
            O_RDONLY
            | O_NONBLOCK
        );

        if (inputs[index] < 0) {
            continue;
        }

        for (;;) {
            struct tf_recovery_ui_input_event event;

            long amount = tf_syscall3(
                SYS_READ,
                inputs[index],
                (long) &event,
                sizeof(event)
            );

            if (
                amount
                != (long) sizeof(event)
            ) {
                break;
            }
        }
    }
}


static int tf_recovery_ui_poll_key_once(
    long *inputs
) {
    if (!inputs) {
        return 0;
    }

    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_UI_INPUT_COUNT;
        index++
    ) {
        if (inputs[index] < 0) {
            char path[32];

            tf_recovery_ui_event_path(
                index,
                path
            );

            inputs[index] = tf_open(
                path,
                O_RDONLY
                | O_NONBLOCK
            );

            if (inputs[index] >= 0) {
                /*
                 * Drain events queued before rediscovery.
                 */
                for (;;) {
                    struct tf_recovery_ui_input_event queued;

                    long amount = tf_syscall3(
                        SYS_READ,
                        inputs[index],
                        (long) &queued,
                        sizeof(queued)
                    );

                    if (
                        amount
                        != (long) sizeof(queued)
                    ) {
                        break;
                    }
                }

                continue;
            }
        }

        if (inputs[index] < 0) {
            continue;
        }

        for (;;) {
            struct tf_recovery_ui_input_event event;

            long amount = tf_syscall3(
                SYS_READ,
                inputs[index],
                (long) &event,
                sizeof(event)
            );

            if (
                amount
                != (long) sizeof(event)
            ) {
                if (
                    amount < 0
                    && amount != -11
                ) {
                    tf_close(
                        inputs[index]
                    );

                    inputs[index] = -1;
                }

                break;
            }

            if (
                event.type == EV_KEY
                && event.value == 1
                && (
                    event.code == KEY_VOLUMEUP
                    || event.code == KEY_VOLUMEDOWN
                    || event.code == KEY_POWER
                )
            ) {
                return event.code;
            }
        }
    }

    return 0;
}


static int tf_recovery_ui_wait_key(
    long *inputs
) {
    for (;;) {
        for (
            int index = 0;
            index
                < TREEFORGE_RECOVERY_UI_INPUT_COUNT;
            index++
        ) {
            if (inputs[index] < 0) {
                char path[32];

                tf_recovery_ui_event_path(
                    index,
                    path
                );

                inputs[index] = tf_open(
                    path,
                    O_RDONLY
                    | O_NONBLOCK
                );

                if (inputs[index] >= 0) {
                    for (;;) {
                        struct tf_recovery_ui_input_event
                            queued;

                        long amount = tf_syscall3(
                            SYS_READ,
                            inputs[index],
                            (long) &queued,
                            sizeof(queued)
                        );

                        if (
                            amount
                            != (long) sizeof(queued)
                        ) {
                            break;
                        }
                    }

                    continue;
                }
            }

            if (inputs[index] < 0) {
                continue;
            }

            for (;;) {
                struct tf_recovery_ui_input_event event;

                long amount = tf_syscall3(
                    SYS_READ,
                    inputs[index],
                    (long) &event,
                    sizeof(event)
                );

                if (
                    amount
                    != (long) sizeof(event)
                ) {
                    if (
                        amount < 0
                        && amount != -11
                    ) {
                        tf_close(
                            inputs[index]
                        );

                        inputs[index] = -1;
                    }

                    break;
                }

                if (
                    event.type == EV_KEY
                    && event.value == 1
                    && (
                        event.code == KEY_VOLUMEUP
                        || event.code
                            == KEY_VOLUMEDOWN
                        || event.code == KEY_POWER
                    )
                ) {
                    return event.code;
                }
            }
        }

        tf_recovery_adbd_maintain();

        tf_recovery_ui_sleep_ms(
            TREEFORGE_RECOVERY_UI_POLL_MS
        );
    }
}


static int tf_recovery_ui_collect_targets(
    int *indices,
    int capacity,
    char install_slot
) {
    int count = 0;

    for (
        int index = 0;
        index
            < tf_recovery_inventory.partition_count;
        index++
    ) {
        struct tf_runtime_partition *record = (
            &tf_recovery_inventory
            .partitions[index]
        );

        if (
            !record->read_probe_eligible
            || !record->slot_pair
            || record->active
            || record->slot != install_slot
        ) {
            continue;
        }

        if (count >= capacity) {
            break;
        }

        indices[count++] = index;
    }

    return count;
}


static void tf_recovery_ui_display_text(
    const char *source,
    char *output,
    usize capacity
) {
    if (
        !output
        || capacity == 0
    ) {
        return;
    }

    output[0] = '\0';

    if (!source) {
        return;
    }

    usize index = 0;

    while (
        source[index] != '\0'
        && index + 1 < capacity
    ) {
        char value = source[index];

        if (
            value >= 'a'
            && value <= 'z'
        ) {
            value = (
                value
                - 'a'
                + 'A'
            );
        } else if (value == '_') {
            /*
             * Preserve identity internally, but make partition
             * separators readable in the minimal DRM font.
             */
            value = ' ';
        }

        output[index] = value;
        index++;
    }

    output[index] = '\0';
}


static usize tf_recovery_ui_append_padded(
    char *line,
    usize capacity,
    usize position,
    const char *value,
    usize width
) {
    usize used = 0;

    if (!line || capacity == 0) {
        return position;
    }

    while (
        value
        && value[used] != '\0'
        && used < width
        && position + 1 < capacity
    ) {
        line[position++] = value[used++];
    }

    while (
        used < width
        && position + 1 < capacity
    ) {
        line[position++] = ' ';
        used++;
    }

    line[position] = '\0';

    return position;
}


static void tf_recovery_ui_capacity_text(
    u64 capacity_bytes,
    char *output,
    usize capacity
) {
    if (
        !output
        || capacity == 0
    ) {
        return;
    }

    output[0] = '\0';

    usize position = 0;

    if (capacity_bytes == 0) {
        position = tf_append_text(
            output,
            capacity,
            position,
            "0 MIB"
        );

        return;
    }

    if (capacity_bytes < 1048576ULL) {
        u64 kib = (
            capacity_bytes
            / 1024ULL
        );

        if (kib == 0) {
            kib = 1;
        }

        position = tf_append_u64(
            output,
            capacity,
            position,
            kib
        );

        tf_append_text(
            output,
            capacity,
            position,
            " KIB"
        );

        return;
    }

    position = tf_append_u64(
        output,
        capacity,
        position,
        (
            capacity_bytes
            / 1048576ULL
        )
    );

    tf_append_text(
        output,
        capacity,
        position,
        " MIB"
    );
}


static const char *
tf_recovery_ui_flash_status(
    const struct tf_recovery_flash_target *target
) {
    if (!target) {
        return "N/A";
    }

    if (
        target->flash_policy
        == TREEFORGE_RECOVERY_FLASH_POLICY_BLOCKED_BOOTLOADER
    ) {
        return "BLOCKED";
    }

    if (target->active) {
        return "ACTIVE";
    }

    if (target->selectable) {
        return "AVAILABLE";
    }

    return "N/A";
}


static int tf_recovery_ui_flash_target_group(
    const struct tf_recovery_flash_target *target
) {
    if (!target) {
        return 3;
    }

    /*
     * Human-facing order:
     *
     *   0. ordinary physical partitions
     *   1. logical partitions
     *   2. blocked bootloader-package partitions
     *
     * This keeps useful Android image targets together while still
     * preserving blocked firmware identities for inspection.
     */
    if (
        target->flash_policy
        == TREEFORGE_RECOVERY_FLASH_POLICY_BLOCKED_BOOTLOADER
    ) {
        return 2;
    }

    if (
        target->target_type
        == TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
    ) {
        return 1;
    }

    return 0;
}


static int tf_recovery_ui_slot_target_count(
    char slot
) {
    int count = 0;

    for (
        int index = 0;
        index < tf_recovery_flash_targets.target_count;
        index++
    ) {
        const struct tf_recovery_flash_target *target = (
            &tf_recovery_flash_targets.targets[index]
        );

        if (target->slot == slot) {
            count++;
        }
    }

    return count;
}


static const struct tf_recovery_flash_target *
tf_recovery_ui_slot_target_at(
    char slot,
    int ordinal
) {
    if (ordinal < 0) {
        return 0;
    }

    int seen = 0;

    for (
        int group = 0;
        group < 3;
        group++
    ) {
        for (
            int index = 0;
            index < tf_recovery_flash_targets.target_count;
            index++
        ) {
            const struct tf_recovery_flash_target *target = (
                &tf_recovery_flash_targets.targets[index]
            );

            if (
                target->slot != slot
                || tf_recovery_ui_flash_target_group(
                    target
                ) != group
            ) {
                continue;
            }

            if (seen == ordinal) {
                return target;
            }

            seen++;
        }
    }

    return 0;
}


static int tf_recovery_ui_unslotted_partition_count(void) {
    int count = 0;

    for (
        int index = 0;
        index < tf_recovery_inventory.partition_count;
        index++
    ) {
        const struct tf_runtime_partition *record = (
            &tf_recovery_inventory.partitions[index]
        );

        if (!record->slot_pair) {
            count++;
        }
    }

    return count;
}


static const struct tf_runtime_partition *
tf_recovery_ui_unslotted_partition_at(
    int ordinal
) {
    if (ordinal < 0) {
        return 0;
    }

    int seen = 0;

    for (
        int index = 0;
        index < tf_recovery_inventory.partition_count;
        index++
    ) {
        const struct tf_runtime_partition *record = (
            &tf_recovery_inventory.partitions[index]
        );

        if (record->slot_pair) {
            continue;
        }

        if (seen == ordinal) {
            return record;
        }

        seen++;
    }

    return 0;
}


static void tf_recovery_ui_flash_target_line(
    const struct tf_recovery_flash_target *target,
    char *line,
    usize capacity
) {
    if (
        !target
        || !line
        || capacity == 0
    ) {
        return;
    }

    line[0] = '\0';

    char display_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char size[32];

    tf_recovery_ui_display_text(
        target->canonical_name,
        display_name,
        sizeof(display_name)
    );

    tf_recovery_ui_capacity_text(
        target->capacity_bytes,
        size,
        sizeof(size)
    );

    const char *type = (
        target->target_type
            == TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        ? "LOGICAL"
        : "PHYSICAL"
    );

    const char *status = (
        tf_recovery_ui_flash_status(
            target
        )
    );

    usize position = 0;

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        display_name,
        18
    );

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        type,
        10
    );

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        size,
        11
    );

    tf_append_text(
        line,
        capacity,
        position,
        status
    );
}


static void tf_recovery_ui_unslotted_line(
    const struct tf_runtime_partition *record,
    char *line,
    usize capacity
) {
    if (
        !record
        || !line
        || capacity == 0
    ) {
        return;
    }

    line[0] = '\0';

    char display_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char size[32];

    tf_recovery_ui_display_text(
        record->canonical_name,
        display_name,
        sizeof(display_name)
    );

    tf_recovery_ui_capacity_text(
        record->capacity_bytes,
        size,
        sizeof(size)
    );

    usize position = 0;

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        display_name,
        18
    );

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        "PHYSICAL",
        10
    );

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        size,
        11
    );

    tf_append_text(
        line,
        capacity,
        position,
        "N/A"
    );
}


static void tf_recovery_ui_page_line(
    int page,
    int pages,
    char *line,
    usize capacity
) {
    if (
        !line
        || capacity == 0
    ) {
        return;
    }

    line[0] = '\0';

    usize position = 0;

    position = tf_append_text(
        line,
        capacity,
        position,
        "PAGE "
    );

    position = tf_append_u64(
        line,
        capacity,
        position,
        (u64) page + 1ULL
    );

    position = tf_append_text(
        line,
        capacity,
        position,
        " / "
    );

    tf_append_u64(
        line,
        capacity,
        position,
        (u64) pages
    );
}


static void tf_recovery_ui_show_slot_partitions(
    long *inputs,
    char slot
) {
    /*
     * The old screen displayed six data rows plus PAGE. Reserve one
     * of those rows for a fixed column header so total density remains
     * unchanged.
     */
    const int rows_per_page = (
        TREEFORGE_RECOVERY_UI_PARTITIONS_PER_PAGE
        - 1
    );

    int count = (
        tf_recovery_ui_slot_target_count(
            slot
        )
    );

    int pages = (
        count
        + rows_per_page
        - 1
    ) / rows_per_page;

    if (pages < 1) {
        pages = 1;
    }

    int page = 0;

    for (;;) {
        char buffers[
            TREEFORGE_RECOVERY_UI_PARTITIONS_PER_PAGE
        ][160];

        const char *lines[
            TREEFORGE_RECOVERY_UI_PARTITIONS_PER_PAGE
            + 1
        ];

        int line_count = 0;

        lines[line_count++] = (
            "PARTITION         TYPE      SIZE       FLASH"
        );

        int start = (
            page
            * rows_per_page
        );

        int end = (
            start
            + rows_per_page
        );

        if (end > count) {
            end = count;
        }

        for (
            int ordinal = start;
            ordinal < end;
            ordinal++
        ) {
            const struct tf_recovery_flash_target *target = (
                tf_recovery_ui_slot_target_at(
                    slot,
                    ordinal
                )
            );

            if (!target) {
                continue;
            }

            tf_recovery_ui_flash_target_line(
                target,
                buffers[line_count - 1],
                sizeof(buffers[line_count - 1])
            );

            lines[line_count] = (
                buffers[line_count - 1]
            );

            line_count++;
        }

        char page_line[64];

        tf_recovery_ui_page_line(
            page,
            pages,
            page_line,
            sizeof(page_line)
        );

        lines[line_count++] = page_line;

        char title[64];

        title[0] = '\0';

        usize position = 0;

        position = tf_append_text(
            title,
            sizeof(title),
            position,
            slot == 'a'
            ? "SLOT A PARTITIONS - "
            : "SLOT B PARTITIONS - "
        );

        tf_append_text(
            title,
            sizeof(title),
            position,
            (
                tf_recovery_flash_targets
                    .active_slot_resolved
                && tf_recovery_flash_targets
                    .active_slot == slot
            )
            ? "ACTIVE"
            : "INACTIVE"
        );

        tf_recovery_ui_draw_info(
            title,
            lines,
            line_count,
            "VOL +/-: PAGE   POWER: BACK"
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_POWER) {
            return;
        }

        if (key == KEY_VOLUMEUP) {
            page = (
                page
                + pages
                - 1
            ) % pages;
        }

        if (key == KEY_VOLUMEDOWN) {
            page = (
                page
                + 1
            ) % pages;
        }
    }
}


static void tf_recovery_ui_show_unslotted_partitions(
    long *inputs
) {
    const int rows_per_page = (
        TREEFORGE_RECOVERY_UI_PARTITIONS_PER_PAGE
        - 1
    );

    int count = (
        tf_recovery_ui_unslotted_partition_count()
    );

    int pages = (
        count
        + rows_per_page
        - 1
    ) / rows_per_page;

    if (pages < 1) {
        pages = 1;
    }

    int page = 0;

    for (;;) {
        char buffers[
            TREEFORGE_RECOVERY_UI_PARTITIONS_PER_PAGE
        ][160];

        const char *lines[
            TREEFORGE_RECOVERY_UI_PARTITIONS_PER_PAGE
            + 1
        ];

        int line_count = 0;

        lines[line_count++] = (
            "PARTITION         TYPE      SIZE       FLASH"
        );

        int start = (
            page
            * rows_per_page
        );

        int end = (
            start
            + rows_per_page
        );

        if (end > count) {
            end = count;
        }

        for (
            int ordinal = start;
            ordinal < end;
            ordinal++
        ) {
            const struct tf_runtime_partition *record = (
                tf_recovery_ui_unslotted_partition_at(
                    ordinal
                )
            );

            if (!record) {
                continue;
            }

            tf_recovery_ui_unslotted_line(
                record,
                buffers[line_count - 1],
                sizeof(buffers[line_count - 1])
            );

            lines[line_count] = (
                buffers[line_count - 1]
            );

            line_count++;
        }

        char page_line[64];

        tf_recovery_ui_page_line(
            page,
            pages,
            page_line,
            sizeof(page_line)
        );

        lines[line_count++] = page_line;

        tf_recovery_ui_draw_info(
            "UNSLOTTED PARTITIONS",
            lines,
            line_count,
            "VOL +/-: PAGE   POWER: BACK"
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_POWER) {
            return;
        }

        if (key == KEY_VOLUMEUP) {
            page = (
                page
                + pages
                - 1
            ) % pages;
        }

        if (key == KEY_VOLUMEDOWN) {
            page = (
                page
                + 1
            ) % pages;
        }
    }
}


static void tf_recovery_ui_show_partitions(
    long *inputs
) {
    static const char *items[] = {
        "SLOT A PARTITIONS",
        "SLOT B PARTITIONS",
        "UNSLOTTED PARTITIONS",
        "BACK",
    };

    int selected = 0;

    for (;;) {
        char active_slot[64];

        tf_recovery_ui_active_slot_line(
            active_slot,
            sizeof(active_slot)
        );

        tf_recovery_ui_draw_menu(
            "PARTITION INFORMATION",
            active_slot,
            items,
            4,
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_VOLUMEUP) {
            selected = (
                selected
                + 3
            ) % 4;

            continue;
        }

        if (key == KEY_VOLUMEDOWN) {
            selected = (
                selected
                + 1
            ) % 4;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        if (selected == 0) {
            tf_recovery_ui_show_slot_partitions(
                inputs,
                'a'
            );

            continue;
        }

        if (selected == 1) {
            tf_recovery_ui_show_slot_partitions(
                inputs,
                'b'
            );

            continue;
        }

        if (selected == 2) {
            tf_recovery_ui_show_unslotted_partitions(
                inputs
            );

            continue;
        }

        return;
    }
}


static void tf_recovery_ui_diagnostic_text_line(
    char *line,
    usize capacity,
    const char *label,
    const char *value
) {
    if (
        !line
        || capacity == 0
    ) {
        return;
    }

    line[0] = '\0';

    usize position = 0;

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        label,
        24
    );

    tf_append_text(
        line,
        capacity,
        position,
        value ? value : "-"
    );
}


static void tf_recovery_ui_diagnostic_u64_line(
    char *line,
    usize capacity,
    const char *label,
    u64 value
) {
    if (
        !line
        || capacity == 0
    ) {
        return;
    }

    line[0] = '\0';

    usize position = 0;

    position = tf_recovery_ui_append_padded(
        line,
        capacity,
        position,
        label,
        24
    );

    tf_append_u64(
        line,
        capacity,
        position,
        value
    );
}


static void tf_recovery_ui_diagnostic_optional_u64_line(
    char *line,
    usize capacity,
    const char *label,
    u64 value
) {
    if (value == 0) {
        tf_recovery_ui_diagnostic_text_line(
            line,
            capacity,
            label,
            "NONE"
        );

        return;
    }

    tf_recovery_ui_diagnostic_u64_line(
        line,
        capacity,
        label,
        value
    );
}


static void tf_recovery_ui_show_diagnostics(
    long *inputs
) {
    /*
     * Temporary hardware-validation seam for the new read-only
     * planner. Final target selection will invoke it directly.
     */
    tf_run_requested_unified_image_plan(
        &tf_recovery_unified_image_plan
    );

    int page = 0;

    for (;;) {
        char buffers[8][128];
        const char *lines[8];

        for (
            int index = 0;
            index < 8;
            index++
        ) {
            lines[index] = buffers[index];
            buffers[index][0] = '\0';
        }

        const char *title = 0;

        if (page == 0) {
            title = "DIAGNOSTICS - DEVICE";

            char active_slot[16];

            if (
                tf_recovery_flash_targets
                    .active_slot_resolved
            ) {
                active_slot[0] = (
                    tf_recovery_flash_targets
                        .active_slot == 'a'
                    ? 'A'
                    : 'B'
                );

                active_slot[1] = '\0';
            } else {
                tf_copy_string(
                    active_slot,
                    sizeof(active_slot),
                    "UNKNOWN"
                );
            }

            tf_recovery_ui_diagnostic_text_line(
                buffers[0],
                sizeof(buffers[0]),
                "ACTIVE SLOT",
                active_slot
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[1],
                sizeof(buffers[1]),
                "PHYSICAL PARTITIONS",
                (u64)
                    tf_recovery_inventory
                        .partition_count
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[2],
                sizeof(buffers[2]),
                "LOGICAL PARTITIONS",
                (u64)
                    tf_recovery_lp_inventory
                        .partition_count
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[3],
                sizeof(buffers[3]),
                "FLASH TARGETS",
                (u64)
                    tf_recovery_flash_targets
                        .target_count
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[4],
                sizeof(buffers[4]),
                "FLASH AVAILABLE",
                (u64)
                    tf_recovery_flash_targets
                        .inactive_selectable_count
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[5],
                sizeof(buffers[5]),
                "BOOTLOADER BLOCKED",
                (u64)
                    tf_recovery_flash_targets
                        .bootloader_blocked_count
            );

            int topology_partial = (
                tf_recovery_inventory
                    .enumeration_error
                || tf_recovery_inventory
                    .partitions_omitted
                || tf_recovery_flash_targets
                    .targets_omitted
                || tf_recovery_lp_inventory
                    .partitions_omitted
                || tf_recovery_lp_inventory
                    .extents_omitted
                || tf_recovery_lp_inventory
                    .metadata_slots_omitted
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[6],
                sizeof(buffers[6]),
                "TOPOLOGY INVENTORY",
                topology_partial
                ? "PARTIAL / ERROR"
                : "OK"
            );

            char lp_metadata[64];

            lp_metadata[0] = '\0';

            if (
                tf_recovery_lp_inventory
                    .authoritative_metadata_valid
            ) {
                usize position = 0;

                position = tf_append_text(
                    lp_metadata,
                    sizeof(lp_metadata),
                    position,
                    "OK / SLOT "
                );

                tf_append_u64(
                    lp_metadata,
                    sizeof(lp_metadata),
                    position,
                    (u64)
                        tf_recovery_lp_inventory
                            .authoritative_metadata_slot
                );
            } else if (
                tf_recovery_lp_inventory
                    .geometry_resolved
            ) {
                tf_copy_string(
                    lp_metadata,
                    sizeof(lp_metadata),
                    "ERROR"
                );
            } else {
                tf_copy_string(
                    lp_metadata,
                    sizeof(lp_metadata),
                    "UNAVAILABLE"
                );
            }

            tf_recovery_ui_diagnostic_text_line(
                buffers[7],
                sizeof(buffers[7]),
                "LP METADATA",
                lp_metadata
            );
        } else if (page == 1) {
            title = "DIAGNOSTICS - INSTALL";

            const char *source = "ABSENT";

            if (
                tf_recovery_ui_probe_readable_path(
                    TREEFORGE_RECOVERY_STREAM_MANIFEST_PATH
                )
            ) {
                source = "STREAM";
            } else if (
                tf_recovery_ui_probe_readable_path(
                    TREEFORGE_RECOVERY_FLASH_SOURCE_PATH
                )
            ) {
                source = "FILE";
            }

            tf_recovery_ui_diagnostic_text_line(
                buffers[0],
                sizeof(buffers[0]),
                "IMAGE SOURCE",
                source
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[1],
                sizeof(buffers[1]),
                "FLASH PLAN",
                tf_recovery_flash_plan.plan_ready
                ? "READY"
                : "NOT READY"
            );

            char target_display[
                TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
            ];

            tf_recovery_ui_display_text(
                (
                    tf_recovery_flash_plan
                        .target_resolved
                    && tf_recovery_flash_plan
                        .target_partition_name[0]
                )
                ? tf_recovery_flash_plan
                    .target_partition_name
                : "-",
                target_display,
                sizeof(target_display)
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[2],
                sizeof(buffers[2]),
                "TARGET",
                target_display
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[3],
                sizeof(buffers[3]),
                "USER CONFIRMED",
                tf_recovery_flash_plan.authorized
                ? "YES"
                : "NO"
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[4],
                sizeof(buffers[4]),
                "WRITE COMPLETE",
                tf_recovery_flash_plan.written
                ? "YES"
                : "NO"
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[5],
                sizeof(buffers[5]),
                "READBACK VERIFIED",
                (
                    tf_recovery_flash_plan
                        .verification_match
                )
                ? "YES"
                : "NO"
            );

            tf_recovery_ui_diagnostic_optional_u64_line(
                buffers[6],
                sizeof(buffers[6]),
                "ERROR STAGE",
                (u64)
                    tf_recovery_flash_plan
                        .error_stage
            );

            tf_recovery_ui_diagnostic_optional_u64_line(
                buffers[7],
                sizeof(buffers[7]),
                "SYSTEM ERROR",
                tf_recovery_flash_plan
                    .error_errno
            );
        } else {
            title = "DIAGNOSTICS - IMAGE PLAN";

            const struct tf_recovery_unified_image_plan_result *plan = (
                &tf_recovery_unified_image_plan
            );

            char plan_target_display[
                TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
            ];

            tf_recovery_ui_display_text(
                (
                    plan->target_resolved
                    && plan->target_partition_name[0]
                )
                ? plan->target_partition_name
                : "-",
                plan_target_display,
                sizeof(plan_target_display)
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[0],
                sizeof(buffers[0]),
                "TARGET",
                plan_target_display
            );

            const char *target_type = "-";

            if (plan->target_resolved) {
                target_type = (
                    plan->target_type
                        == TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
                    ? "LOGICAL"
                    : "PHYSICAL"
                );
            }

            tf_recovery_ui_diagnostic_text_line(
                buffers[1],
                sizeof(buffers[1]),
                "TARGET TYPE",
                target_type
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[2],
                sizeof(buffers[2]),
                "IMAGE FORMAT",
                tf_recovery_image_format_name(
                    plan->source_format
                )
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[3],
                sizeof(buffers[3]),
                "SOURCE BYTES",
                plan->source_bytes
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[4],
                sizeof(buffers[4]),
                "EXPANDED BYTES",
                plan->expanded_bytes
            );

            tf_recovery_ui_diagnostic_u64_line(
                buffers[5],
                sizeof(buffers[5]),
                "CURRENT CAPACITY",
                plan->target_capacity_bytes
            );

            const char *allocation = "-";

            if (
                plan->plan_resolved
                && plan->target_type
                    == TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
            ) {
                allocation = (
                    plan->physical_capacity_sufficient
                    ? "FITS"
                    : "TOO LARGE"
                );
            } else if (
                plan->plan_resolved
                && plan->target_type
                    == TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
            ) {
                if (plan->allocation_required) {
                    allocation = "ALLOCATE";
                } else if (plan->resize_required) {
                    allocation = "RESIZE";
                } else {
                    allocation = "NONE";
                }
            }

            tf_recovery_ui_diagnostic_text_line(
                buffers[6],
                sizeof(buffers[6]),
                "ALLOCATION CHANGE",
                allocation
            );

            const char *plan_status = (
                !plan->requested
                ? "NOT REQUESTED"
                : (
                    plan->plan_resolved
                    ? "RESOLVED / READ ONLY"
                    : "ERROR"
                )
            );

            tf_recovery_ui_diagnostic_text_line(
                buffers[7],
                sizeof(buffers[7]),
                "PLAN STATUS",
                plan_status
            );
        }

        tf_recovery_ui_draw_info(
            title,
            lines,
            8,
            "VOL +/-: PAGE   POWER: BACK"
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_POWER) {
            return;
        }

        if (key == KEY_VOLUMEUP) {
            page = (
                page
                + 2
            ) % 3;
        }

        if (key == KEY_VOLUMEDOWN) {
            page = (
                page
                + 1
            ) % 3;
        }
    }
}


static int tf_recovery_ui_write_plan_request(
    const char *canonical_name
) {
    if (
        !canonical_name
        || !canonical_name[0]
    ) {
        return 0;
    }

    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_FLASH_PLAN_REQUEST_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return 0;
    }

    int result = tf_write_buffer(
        fd,
        canonical_name,
        tf_strlen(canonical_name)
    );

    tf_close(
        fd
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );

    return result;
}


static void tf_recovery_ui_sha_prefix(
    const char *sha256,
    char *output,
    usize capacity
) {
    if (
        !output
        || capacity == 0
    ) {
        return;
    }

    output[0] = '\0';

    if (
        !sha256
        || !sha256[0]
    ) {
        tf_copy_string(
            output,
            capacity,
            "-"
        );

        return;
    }

    usize limit = 16;

    if (
        limit + 4
        > capacity
    ) {
        limit = (
            capacity > 4
            ? capacity - 4
            : 0
        );
    }

    usize index = 0;

    while (
        index < limit
        && sha256[index]
    ) {
        char value = sha256[index];

        if (
            value >= 'a'
            && value <= 'f'
        ) {
            value = (
                value
                - 'a'
                + 'A'
            );
        }

        output[index] = value;
        index++;
    }

    if (
        index + 3
        < capacity
    ) {
        output[index++] = '.';
        output[index++] = '.';
        output[index++] = '.';
    }

    output[index] = '\0';
}


static void tf_recovery_ui_render_plan(
    int selected
) {
    char target[160];
    char slot[64];
    char source_size[64];
    char hash[64];

    char target_display[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char hash_prefix[32];

    tf_recovery_ui_sha_prefix(
        tf_recovery_flash_plan.source_sha256,
        hash_prefix,
        sizeof(hash_prefix)
    );

    tf_recovery_ui_display_text(
        tf_recovery_flash_plan.target_resolved
        ? tf_recovery_flash_plan.target_partition_name
        : "-",
        target_display,
        sizeof(target_display)
    );

    target[0] = '\0';

    usize position = 0;

    position = tf_append_text(
        target,
        sizeof(target),
        position,
        "TARGET: "
    );

    tf_append_text(
        target,
        sizeof(target),
        position,
        target_display
    );

    slot[0] = '\0';

    position = tf_append_text(
        slot,
        sizeof(slot),
        0,
        "SLOT: "
    );

    if (tf_recovery_flash_plan.target_slot) {
        char slot_name[2];

        slot_name[0] = (
            tf_recovery_flash_plan.target_slot
            == 'a'
            ? 'A'
            : 'B'
        );

        slot_name[1] = '\0';

        position = tf_append_text(
            slot,
            sizeof(slot),
            position,
            slot_name
        );

        tf_append_text(
            slot,
            sizeof(slot),
            position,
            tf_recovery_flash_plan.target_active
            ? " ACTIVE"
            : " INACTIVE"
        );
    } else {
        tf_append_text(
            slot,
            sizeof(slot),
            position,
            "UNKNOWN"
        );
    }

    source_size[0] = '\0';

    position = tf_append_text(
        source_size,
        sizeof(source_size),
        0,
        "SOURCE SIZE: "
    );

    position = tf_append_u64(
        source_size,
        sizeof(source_size),
        position,
        (
            tf_recovery_flash_plan.source_bytes
            / 1048576ULL
        )
    );

    tf_append_text(
        source_size,
        sizeof(source_size),
        position,
        " MIB"
    );

    hash[0] = '\0';

    position = tf_append_text(
        hash,
        sizeof(hash),
        0,
        "SHA256: "
    );

    tf_append_text(
        hash,
        sizeof(hash),
        position,
        hash_prefix
    );

    const char *resolved = (
        tf_recovery_flash_plan.target_resolved
        ? "TARGET RESOLVED: YES"
        : "TARGET RESOLVED: NO"
    );

    const char *inactive = (
        tf_recovery_flash_plan.target_resolved
        && !tf_recovery_flash_plan.target_active
        ? "INACTIVE TARGET: YES"
        : "INACTIVE TARGET: NO"
    );

    const char *hashed = (
        tf_recovery_flash_plan.source_streaming
        ? (
            tf_recovery_flash_plan.source_manifest_valid
            ? "STREAM MANIFEST: VALID"
            : "STREAM MANIFEST: INVALID"
        )
        : (
            tf_recovery_flash_plan.source_hash_succeeded
            ? "SOURCE HASHED: YES"
            : "SOURCE HASHED: NO"
        )
    );

    const char *fits = (
        tf_recovery_flash_plan.source_fits_target
        ? "IMAGE FITS: YES"
        : "IMAGE FITS: NO"
    );

    const char *ready = (
        tf_recovery_flash_plan.plan_ready
        ? "FLASH PLAN READY: YES"
        : "FLASH PLAN READY: NO"
    );

    const char *authorize = (
        selected == 0
        ? "> INSTALL IMAGE"
        : "  INSTALL IMAGE"
    );

    const char *cancel = (
        selected == 1
        ? "> CANCEL"
        : "  CANCEL"
    );

    const char *lines[] = {
        target,
        slot,
        source_size,
        hash,
        resolved,
        inactive,
        hashed,
        fits,
        ready,
        authorize,
        cancel,
    };

    tf_recovery_ui_draw_info(
        "INSTALL IMAGE",
        lines,
        11,
        "VOL +/-: CHOOSE   POWER: SELECT"
    );

    tf_recovery_ui_highlight_info_line(
        selected == 0
        ? authorize
        : cancel,
        selected == 0
        ? 9
        : 10
    );
}


static int tf_recovery_ui_confirm_current_write(
    long *inputs
) {
    int selected = 1;

    for (;;) {
        char target[
            TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
        ];

        tf_recovery_ui_display_text(
            tf_recovery_flash_plan.target_partition_name,
            target,
            sizeof(target)
        );

        const char *confirm = (
            selected == 0
            ? "> CONFIRM WRITE"
            : "  CONFIRM WRITE"
        );

        const char *cancel = (
            selected == 1
            ? "> CANCEL"
            : "  CANCEL"
        );

        const char *source_guard = (
            tf_recovery_flash_plan.source_streaming
            ? "STREAM HASH MUST MATCH MANIFEST"
            : "SOURCE HASH WILL BE REVALIDATED"
        );

        const char *lines[] = {
            "THIS WILL MODIFY A PARTITION",
            target,
            "TARGET IS THE INACTIVE SLOT",
            source_guard,
            "WRITE WILL BE VERIFIED AFTERWARD",
            "SLOT WILL NOT BE ACTIVATED",
            confirm,
            cancel,
        };

        tf_recovery_ui_draw_info(
            "CONFIRM INSTALL",
            lines,
            8,
            "VOL +/-: CHOOSE   POWER: SELECT"
        );

        tf_recovery_ui_highlight_info_line(
            selected == 0
            ? confirm
            : cancel,
            selected == 0
            ? 6
            : 7
        );

        int key = tf_recovery_ui_wait_key(
            inputs
        );

        if (
            key == KEY_VOLUMEUP
            || key == KEY_VOLUMEDOWN
        ) {
            selected = (
                selected == 0
                ? 1
                : 0
            );

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        return selected == 0;
    }
}


static int tf_recovery_ui_authorize_current_plan(void) {
    struct tf_recovery_flash_plan_result previous = (
        tf_recovery_flash_plan
    );

    if (!previous.plan_ready) {
        tf_recovery_flash_plan
            .authorization_requested = 1;

        tf_recovery_flash_plan
            .authorization_match = 0;

        tf_recovery_flash_plan
            .authorized = 0;

        tf_recovery_flash_plan
            .written = 0;

        tf_recovery_flash_plan
            .activation_eligible = 0;

        return 0;
    }

    if (
        !tf_recovery_ui_write_plan_request(
            previous.requested_canonical_name
        )
    ) {
        tf_recovery_flash_plan
            .authorization_requested = 1;

        tf_recovery_flash_plan
            .authorization_match = 0;

        tf_recovery_flash_plan
            .authorized = 0;

        tf_recovery_flash_plan
            .written = 0;

        tf_recovery_flash_plan
            .activation_eligible = 0;

        return 0;
    }

    tf_run_requested_flash_plan(
        &tf_recovery_inventory,
        &tf_recovery_flash_plan
    );

    tf_recovery_flash_plan
        .authorization_requested = 1;

    int match = (
        tf_recovery_flash_plan.plan_ready
        && tf_string_equal(
            previous.requested_canonical_name,
            tf_recovery_flash_plan
                .requested_canonical_name
        )
        && tf_string_equal(
            previous.target_partition_name,
            tf_recovery_flash_plan
                .target_partition_name
        )
        && previous.target_slot
            == tf_recovery_flash_plan.target_slot
        && previous.target_major
            == tf_recovery_flash_plan.target_major
        && previous.target_minor
            == tf_recovery_flash_plan.target_minor
        && previous.source_streaming
            == tf_recovery_flash_plan.source_streaming
        && previous.source_manifest_valid
            == tf_recovery_flash_plan.source_manifest_valid
        && previous.source_bytes
            == tf_recovery_flash_plan.source_bytes
        && tf_string_equal(
            previous.source_sha256,
            tf_recovery_flash_plan.source_sha256
        )
    );

    tf_recovery_flash_plan
        .authorization_match = match;

    tf_recovery_flash_plan
        .authorized = match;

    if (
        match
        && tf_recovery_flash_plan.source_streaming
    ) {
        /*
         * The image descriptor is a companion to the stream manifest.
         *
         * Consume it first so TreeForge can never deliberately leave
         * descriptor metadata behind after consuming the authoritative
         * stream identity.
         *
         * ENOENT remains valid because the hardware-accepted legacy
         * streaming path does not require an image descriptor.
         */
        long descriptor_cleanup = tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_IMAGE_DESCRIPTOR_PATH,
            0
        );

        if (
            descriptor_cleanup != 0
            && descriptor_cleanup != -2
        ) {
            match = 0;

            tf_recovery_flash_plan
                .authorization_match = 0;

            tf_recovery_flash_plan
                .authorized = 0;

            tf_recovery_flash_plan
                .error_stage = 51;

            tf_recovery_flash_plan
                .error_errno = (
                    (u64) (-descriptor_cleanup)
                );
        } else {
            long manifest_cleanup = tf_syscall3(
                SYS_UNLINKAT,
                AT_FDCWD,
                (long)
                    TREEFORGE_RECOVERY_STREAM_MANIFEST_PATH,
                0
            );

            if (
                manifest_cleanup != 0
                && manifest_cleanup != -2
            ) {
                match = 0;

                tf_recovery_flash_plan
                    .authorization_match = 0;

                tf_recovery_flash_plan
                    .authorized = 0;

                tf_recovery_flash_plan
                    .error_stage = 52;

                tf_recovery_flash_plan
                    .error_errno = (
                        (u64) (-manifest_cleanup)
                    );
            }
        }

        tf_syscall1(
            SYS_SYNC,
            0
        );
    }

    /*
     * Authorization still cannot write or activate anything.
     */
    tf_recovery_flash_plan
        .written = 0;

    tf_recovery_flash_plan
        .activation_eligible = 0;

    return match;
}


static int tf_recovery_ui_show_authorization_result(
    long *inputs
) {
    char bytes_written[64];
    char stage[64];
    char error[64];

    usize position = tf_append_text(
        bytes_written,
        sizeof(bytes_written),
        0,
        "BYTES WRITTEN: "
    );

    tf_append_u64(
        bytes_written,
        sizeof(bytes_written),
        position,
        tf_recovery_flash_plan.bytes_written
    );

    position = tf_append_text(
        stage,
        sizeof(stage),
        0,
        "ERROR STAGE: "
    );

    tf_append_u64(
        stage,
        sizeof(stage),
        position,
        (u64) tf_recovery_flash_plan.error_stage
    );

    position = tf_append_text(
        error,
        sizeof(error),
        0,
        "ERRNO: "
    );

    tf_append_u64(
        error,
        sizeof(error),
        position,
        tf_recovery_flash_plan.error_errno
    );

    const char *lines[] = {
        tf_recovery_flash_plan.authorization_match
        ? "PLAN REVALIDATION: MATCH"
        : "PLAN REVALIDATION: FAILED",

        tf_recovery_flash_plan.authorized
        ? "AUTHORIZED: YES"
        : "AUTHORIZED: NO",

        tf_recovery_flash_plan.source_revalidated
        ? "SOURCE REVALIDATED: YES"
        : "SOURCE REVALIDATED: NO",

        bytes_written,

        tf_recovery_flash_plan.write_synced
        ? "WRITE SYNC: OK"
        : "WRITE SYNC: NO",

        tf_recovery_flash_plan.verification_hash_succeeded
        ? "READ-BACK HASH: OK"
        : "READ-BACK HASH: NO",

        tf_recovery_flash_plan.verification_match
        ? "READ-BACK MATCH: YES"
        : "READ-BACK MATCH: NO",

        tf_recovery_flash_plan.written
        ? "INSTALL VERIFIED: YES"
        : "INSTALL VERIFIED: NO",

        "SLOT ACTIVATED: NO",
        stage,
        error,
    };

    tf_recovery_ui_draw_info(
        "INSTALL RESULT",
        lines,
        11,
        "POWER: BACK"
    );

    for (;;) {
        if (
            tf_recovery_ui_wait_key(
                inputs
            )
            == KEY_POWER
        ) {
            /*
             * Failed or incomplete writes return directly to Recovery.
             * A reboot choice is offered only after the writer has
             * reached its final hardware-verification acceptance state.
             */
            if (!tf_recovery_flash_plan.written) {
                return 0;
            }

            break;
        }
    }

    /*
     * Successful-install reboot policy:
     *
     *   - explicitly ask;
     *   - default YES;
     *   - NO returns to TreeForge Recovery;
     *   - this choice never changes slot activation state.
     */
    int selected = 0;

    for (;;) {
        const char *yes = (
            selected == 0
            ? "> YES"
            : "  YES"
        );

        const char *no = (
            selected == 1
            ? "> NO"
            : "  NO"
        );

        const char *lines[] = {
            "INSTALL VERIFIED",
            "REBOOT DEVICE?",
            yes,
            no,
            "SLOT ACTIVATED: NO",
        };

        tf_recovery_ui_draw_info(
            "INSTALL COMPLETE",
            lines,
            5,
            "VOL +/-: CHOOSE   POWER: SELECT"
        );

        tf_recovery_ui_highlight_info_line(
            selected == 0
            ? yes
            : no,
            selected == 0
            ? 2
            : 3
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (
            key == KEY_VOLUMEUP
            || key == KEY_VOLUMEDOWN
        ) {
            selected = (
                selected == 0
                ? 1
                : 0
            );

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        return (
            selected == 0
            ? 1
            : 0
        );
    }
}


/*
 * Return contract:
 *
 *   0 = return to target picker
 *   1 = verified install requested normal reboot
 *   2 = completed install attempt, return to main Recovery menu
 */
static int tf_recovery_ui_show_plan(
    long *inputs
) {
    if (!tf_recovery_flash_plan.plan_ready) {
        char stage[64];
        char error[64];

        stage[0] = '\0';
        error[0] = '\0';

        usize position = 0;

        position = tf_append_text(
            stage,
            sizeof(stage),
            position,
            "ERROR STAGE: "
        );

        tf_append_u64(
            stage,
            sizeof(stage),
            position,
            (u64) tf_recovery_flash_plan.error_stage
        );

        position = tf_append_text(
            error,
            sizeof(error),
            0,
            "ERRNO: "
        );

        tf_append_u64(
            error,
            sizeof(error),
            position,
            tf_recovery_flash_plan.error_errno
        );

        const char *lines[] = {
            "FLASH PLAN NOT READY",
            stage,
            error,
            "NO PARTITION WAS WRITTEN",
        };

        tf_recovery_ui_draw_info(
            "INSTALL IMAGE",
            lines,
            4,
            "POWER: BACK"
        );

        for (;;) {
            if (
                tf_recovery_ui_wait_key(
                    inputs
                )
                == KEY_POWER
            ) {
                return 0;
            }
        }
    }

    /*
     * A destructive operation must never be the default selection.
     */
    int selected = 1;

    for (;;) {
        tf_recovery_ui_render_plan(
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (
            key == KEY_VOLUMEUP
            || key == KEY_VOLUMEDOWN
        ) {
            selected = (
                selected == 0
                ? 1
                : 0
            );

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        if (selected == 1) {
            return 0;
        }

        if (
            !tf_recovery_ui_confirm_current_write(
                inputs
            )
        ) {
            return 0;
        }

        if (
            tf_recovery_ui_authorize_current_plan()
        ) {
            if (
                tf_recovery_flash_plan.source_streaming
            ) {
                const char *stream_lines[] = {
                    "ADB PUSH IMAGE NOW",
                    "STREAM ENDPOINT READY",
                    "DO NOT DISCONNECT USB",
                };

                tf_recovery_ui_draw_info(
                    "WAITING FOR IMAGE",
                    stream_lines,
                    3,
                    0
                );
            }

            tf_recovery_write_authorized_plan(
                &tf_recovery_flash_plan
            );
        }

        tf_emit_inventory(
            &tf_recovery_inventory
        );

        int reboot_requested = (
            tf_recovery_ui_show_authorization_result(
                inputs
            )
        );

        if (reboot_requested) {
            return 1;
        }

        /*
         * An actual install attempt has completed. NO on the reboot
         * prompt, or any failed attempt, returns to the Recovery main
         * menu rather than immediately reopening the target picker.
         */
        return 2;
    }
}



static void tf_recovery_ui_install_slot_line(
    char install_slot,
    char *line,
    usize capacity
) {
    if (
        !line
        || capacity == 0
    ) {
        return;
    }

    line[0] = '\0';

    usize position = 0;

    position = tf_append_text(
        line,
        capacity,
        position,
        "ACTIVE SLOT: "
    );

    if (
        tf_recovery_inventory
        .active_slot_resolved
    ) {
        char active[2];

        active[0] = (
            tf_recovery_inventory
            .active_slot
            == 'a'
            ? 'A'
            : 'B'
        );

        active[1] = '\0';

        position = tf_append_text(
            line,
            capacity,
            position,
            active
        );
    } else {
        position = tf_append_text(
            line,
            capacity,
            position,
            "UNKNOWN"
        );
    }

    position = tf_append_text(
        line,
        capacity,
        position,
        " / INSTALL SLOT: "
    );

    char selected[2];

    selected[0] = (
        install_slot == 'a'
        ? 'A'
        : 'B'
    );

    selected[1] = '\0';

    tf_append_text(
        line,
        capacity,
        position,
        selected
    );
}


static char tf_recovery_ui_select_install_slot(
    long *inputs
) {
    /*
     * TreeForge never guesses a destructive slot if the runtime
     * active-slot identity is unresolved.
     */
    if (
        !tf_recovery_inventory
        .active_slot_resolved
    ) {
        const char *lines[] = {
            "ACTIVE SLOT UNKNOWN",
            "INSTALL TARGET DISABLED",
            "NO PARTITION WAS WRITTEN",
        };

        tf_recovery_ui_draw_info(
            "SELECT INSTALL SLOT",
            lines,
            3,
            "POWER: BACK"
        );

        for (;;) {
            if (
                tf_recovery_ui_wait_key(
                    inputs
                )
                == KEY_POWER
            ) {
                return 0;
            }
        }
    }

    char active = (
        tf_recovery_inventory
        .active_slot
    );

    /*
     * Default to the inactive slot.
     */
    int selected = (
        active == 'a'
        ? 1
        : 0
    );

    for (;;) {
        const char *slot_a = (
            active == 'a'
            ? "SLOT A - ACTIVE BLOCKED"
            : "SLOT A - INACTIVE"
        );

        const char *slot_b = (
            active == 'b'
            ? "SLOT B - ACTIVE BLOCKED"
            : "SLOT B - INACTIVE"
        );

        const char *items[] = {
            slot_a,
            slot_b,
            "CANCEL",
        };

        char active_line[64];

        tf_recovery_ui_active_slot_line(
            active_line,
            sizeof(active_line)
        );

        tf_recovery_ui_draw_menu(
            "SELECT INSTALL SLOT",
            active_line,
            items,
            3,
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_VOLUMEUP) {
            selected = (
                selected + 2
            ) % 3;

            continue;
        }

        if (key == KEY_VOLUMEDOWN) {
            selected = (
                selected + 1
            ) % 3;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        if (selected == 2) {
            return 0;
        }

        char requested_slot = (
            selected == 0
            ? 'a'
            : 'b'
        );

        /*
         * The slot selector is not an active-slot override.
         *
         * Selecting the active row is allowed for visibility, but the
         * destructive workflow remains blocked. This is independent of
         * the later target-plan active-slot revalidation.
         */
        if (requested_slot == active) {
            const char *lines[] = {
                "ACTIVE SLOT FLASH BLOCKED",
                "SELECT THE INACTIVE SLOT",
                "NO PARTITION WAS WRITTEN",
            };

            tf_recovery_ui_draw_info(
                "SELECT INSTALL SLOT",
                lines,
                3,
                "POWER: BACK"
            );

            for (;;) {
                if (
                    tf_recovery_ui_wait_key(
                        inputs
                    )
                    == KEY_POWER
                ) {
                    break;
                }
            }

            continue;
        }

        return requested_slot;
    }
}


static void tf_recovery_ui_render_targets(
    int *candidate_indices,
    int candidate_count,
    int selected,
    char install_slot
) {
    const char *items[6];

    char display_names[5][
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    int start = 0;

    if (
        candidate_count > 5
        && selected < candidate_count
        && selected >= 5
    ) {
        start = (
            selected - 4
        );
    }

    if (
        candidate_count > 5
        && selected == candidate_count
    ) {
        start = (
            candidate_count - 5
        );
    }

    int visible = (
        candidate_count - start
    );

    if (visible > 5) {
        visible = 5;
    }

    for (
        int index = 0;
        index < visible;
        index++
    ) {
        struct tf_runtime_partition *record = (
            &tf_recovery_inventory
            .partitions[
                candidate_indices[
                    start + index
                ]
            ]
        );

        tf_recovery_ui_display_text(
            record->partition_name,
            display_names[index],
            sizeof(display_names[index])
        );

        items[index] = (
            display_names[index]
        );
    }

    items[visible] = "CANCEL";

    int local_selected = (
        selected == candidate_count
        ? visible
        : selected - start
    );

    char slot_line[96];

    tf_recovery_ui_install_slot_line(
        install_slot,
        slot_line,
        sizeof(slot_line)
    );

    tf_recovery_ui_draw_menu(
        "INSTALL STAGED IMAGE",
        slot_line,
        items,
        visible + 1,
        local_selected
    );
}


static int tf_recovery_ui_install_image(
    long *inputs
) {
    char install_slot = (
        tf_recovery_ui_select_install_slot(
            inputs
        )
    );

    if (!install_slot) {
        return 0;
    }

    int candidates[
        TREEFORGE_RECOVERY_UI_MAX_TARGETS
    ];

    int count = (
        tf_recovery_ui_collect_targets(
            candidates,
            TREEFORGE_RECOVERY_UI_MAX_TARGETS,
            install_slot
        )
    );

    if (count <= 0) {
        const char *lines[] = {
            "NO ELIGIBLE INACTIVE TARGETS",
            "NO PARTITION WAS WRITTEN",
        };

        tf_recovery_ui_draw_info(
            "INSTALL STAGED IMAGE",
            lines,
            2,
            "POWER: BACK"
        );

        for (;;) {
            if (
                tf_recovery_ui_wait_key(
                    inputs
                )
                == KEY_POWER
            ) {
                return 0;
            }
        }
    }

    int selected = 0;

    for (;;) {
        tf_recovery_ui_render_targets(
            candidates,
            count,
            selected,
            install_slot
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_VOLUMEUP) {
            selected = (
                selected
                + count
            ) % (
                count + 1
            );

            continue;
        }

        if (key == KEY_VOLUMEDOWN) {
            selected = (
                selected
                + 1
            ) % (
                count + 1
            );

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        if (selected == count) {
            return 0;
        }

        struct tf_runtime_partition *target = (
            &tf_recovery_inventory
            .partitions[
                candidates[selected]
            ]
        );

        if (
            !tf_recovery_ui_write_plan_request(
                target->canonical_name
            )
        ) {
            continue;
        }

        tf_run_requested_flash_plan(
            &tf_recovery_inventory,
            &tf_recovery_flash_plan
        );

        tf_emit_inventory(
            &tf_recovery_inventory
        );

        int plan_result = (
            tf_recovery_ui_show_plan(
                inputs
            )
        );

        if (plan_result == 1) {
            return 1;
        }

        if (plan_result == 2) {
            return 0;
        }
    }
}


/*
 * Recovery Install Set receive authorization.
 *
 * This state is deliberately boot-local and non-destructive. It exists
 * only so a future host-side `treeforge recovery stage` command can prove
 * that the user explicitly armed this Recovery session to receive an
 * install set.
 *
 * Receive authorization is NOT flash authorization.
 */
static int tf_recovery_set_install_set_receive_ready(
    int enabled
) {
    if (!enabled) {
        long result = tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_INSTALL_SET_RECEIVE_READY_PATH,
            0
        );

        return (
            result == 0
            || result == -2
        );
    }

    /*
     * A newly armed receive session owns a fresh payload-transaction
     * lifecycle. Never let a previous boot-local READY/COMPLETE state
     * satisfy the new host command.
     */
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_INSTALL_SET_TRANSFER_STATE_PATH,
        0
    );

    char state[160];

    state[0] = '\0';

    usize position = 0;

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "treeforge-recovery-install-set-receive-v1\n"
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "ready=1\n"
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "active_slot="
    );

    if (
        tf_recovery_flash_targets
            .active_slot_resolved
        && (
            tf_recovery_flash_targets
                .active_slot == 'a'
            || tf_recovery_flash_targets
                .active_slot == 'b'
        )
    ) {
        char slot[2];

        slot[0] = (
            tf_recovery_flash_targets
                .active_slot
        );

        slot[1] = '\0';

        position = tf_append_text(
            state,
            sizeof(state),
            position,
            slot
        );
    } else {
        position = tf_append_text(
            state,
            sizeof(state),
            position,
            "unknown"
        );
    }

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\nflashing=0\n"
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_INSTALL_SET_RECEIVE_READY_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return 0;
    }

    int wrote = tf_write_buffer(
        fd,
        state,
        position
    );

    tf_close(fd);

    return wrote;
}


#define TREEFORGE_RECOVERY_PROGRESS_REDRAW_BYTES \
    (1024ULL * 1024ULL)


struct tf_recovery_transaction_progress {
    int active;

    int image_index;
    int image_count;
    int completed_images;

    char partition_name[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    char phase[48];

    u64 bytes_completed;
    u64 bytes_total;

    u64 last_render_bytes;

    int destructive;
};


static struct tf_recovery_transaction_progress
    tf_recovery_transaction_progress;


static u64 tf_recovery_progress_percent(
    u64 completed,
    u64 total
) {
    if (total == 0) {
        return 0;
    }

    if (completed >= total) {
        return 100;
    }

    return (
        completed
        * 100ULL
        / total
    );
}


static void tf_recovery_ui_render_transaction_progress(
    void
) {
    const struct tf_recovery_transaction_progress *progress = (
        &tf_recovery_transaction_progress
    );

    if (!progress->active) {
        return;
    }

    char image_line[80];
    char partition_line[128];
    char phase_line[96];
    char bytes_line[128];
    char percent_line[80];
    char complete_line[80];

    usize position = 0;

    image_line[0] = '\0';

    position = tf_append_text(
        image_line,
        sizeof(image_line),
        0,
        "IMAGE                    "
    );

    position = tf_append_u64(
        image_line,
        sizeof(image_line),
        position,
        (u64) (
            progress->image_index
            + 1
        )
    );

    position = tf_append_text(
        image_line,
        sizeof(image_line),
        position,
        " / "
    );

    tf_append_u64(
        image_line,
        sizeof(image_line),
        position,
        (u64) progress->image_count
    );

    char partition_display[
        TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
    ];

    tf_recovery_ui_display_text(
        progress->partition_name,
        partition_display,
        sizeof(partition_display)
    );

    partition_line[0] = '\0';

    position = tf_append_text(
        partition_line,
        sizeof(partition_line),
        0,
        "PARTITION                "
    );

    tf_append_text(
        partition_line,
        sizeof(partition_line),
        position,
        (
            partition_display[0]
            ? partition_display
            : "-"
        )
    );

    phase_line[0] = '\0';

    position = tf_append_text(
        phase_line,
        sizeof(phase_line),
        0,
        "PHASE                    "
    );

    tf_append_text(
        phase_line,
        sizeof(phase_line),
        position,
        (
            progress->phase[0]
            ? progress->phase
            : "-"
        )
    );

    bytes_line[0] = '\0';

    position = tf_append_text(
        bytes_line,
        sizeof(bytes_line),
        0,
        "BYTES                    "
    );

    position = tf_append_u64(
        bytes_line,
        sizeof(bytes_line),
        position,
        progress->bytes_completed
    );

    position = tf_append_text(
        bytes_line,
        sizeof(bytes_line),
        position,
        " / "
    );

    tf_append_u64(
        bytes_line,
        sizeof(bytes_line),
        position,
        progress->bytes_total
    );

    percent_line[0] = '\0';

    position = tf_append_text(
        percent_line,
        sizeof(percent_line),
        0,
        "IMAGE PROGRESS           "
    );

    position = tf_append_u64(
        percent_line,
        sizeof(percent_line),
        position,
        tf_recovery_progress_percent(
            progress->bytes_completed,
            progress->bytes_total
        )
    );

    tf_append_text(
        percent_line,
        sizeof(percent_line),
        position,
        "%"
    );

    complete_line[0] = '\0';

    position = tf_append_text(
        complete_line,
        sizeof(complete_line),
        0,
        (
            progress->destructive
            ? "OVERALL INSTALLED        "
            : "OVERALL VERIFIED         "
        )
    );

    position = tf_append_u64(
        complete_line,
        sizeof(complete_line),
        position,
        (u64) progress->completed_images
    );

    position = tf_append_text(
        complete_line,
        sizeof(complete_line),
        position,
        " / "
    );

    tf_append_u64(
        complete_line,
        sizeof(complete_line),
        position,
        (u64) progress->image_count
    );

    const char *lines[] = {
        image_line,
        partition_line,
        phase_line,
        bytes_line,
        percent_line,
        complete_line,
        (
            progress->destructive
            && progress->completed_images == 0
            && progress->image_index == 0
            && tf_string_equal(
                progress->phase,
                "WAITING FOR HOST"
            )
            ? "PARTITION WRITE          NOT STARTED"
            : (
                progress->destructive
                ? "PARTITION WRITE          ACTIVE"
                : "FLASHING                 DISABLED"
            )
        ),
        (
            tf_string_equal(
                progress->phase,
                "WAITING FOR HOST"
            )
            && (
                !progress->destructive
                || (
                    progress->completed_images == 0
                    && progress->image_index == 0
                )
            )
            ? "POWER TO CANCEL"
            : (
                progress->destructive
                ? "DO NOT POWER OFF"
                : "NO PARTITIONS WILL BE WRITTEN"
            )
        ),
    };

    tf_recovery_ui_draw_info(
        "INSTALL SET PROGRESS",
        lines,
        8,
        (
            tf_string_equal(
                progress->phase,
                "WAITING FOR HOST"
            )
            && (
                !progress->destructive
                || (
                    progress->completed_images == 0
                    && progress->image_index == 0
                )
            )
            ? "POWER: CANCEL"
            : (
                progress->destructive
                ? "TRANSACTION IN PROGRESS"
                : "STREAM VERIFICATION IN PROGRESS"
            )
        )
    );
}



static u64 tf_recovery_install_set_transport_bytes(
    const struct tf_recovery_install_set_result *set,
    const struct tf_recovery_install_set_image *image
) {
    if (!set || !image) {
        return 0;
    }

    if (
        set->wire_version
        == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
    ) {
        return image->manifest_payload_bytes;
    }

    return image->source_bytes;
}


static const char *tf_recovery_install_set_transport_sha256(
    const struct tf_recovery_install_set_result *set,
    const struct tf_recovery_install_set_image *image
) {
    if (!set || !image) {
        return "";
    }

    if (
        set->wire_version
        == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
    ) {
        return image->manifest_payload_sha256;
    }

    return image->sha256;
}


static void tf_recovery_transaction_progress_begin(
    const struct tf_recovery_install_set_result *set,
    int image_index,
    const char *phase,
    int destructive
) {
    if (
        !set
        || image_index < 0
        || image_index >= set->image_count
    ) {
        return;
    }

    struct tf_recovery_transaction_progress *progress = (
        &tf_recovery_transaction_progress
    );

    memset(
        progress,
        0,
        sizeof(*progress)
    );

    progress->active = 1;
    progress->image_index = image_index;
    progress->image_count = set->image_count;

    progress->completed_images = (
        destructive
        ? image_index
        : set->payload_verified_count
    );

    progress->bytes_total = (
        tf_recovery_install_set_transport_bytes(
            set,
            &set->images[image_index]
        )
    );

    progress->destructive = destructive;

    tf_copy_string(
        progress->partition_name,
        sizeof(progress->partition_name),
        set->images[
            image_index
        ].canonical_name
    );

    tf_copy_string(
        progress->phase,
        sizeof(progress->phase),
        phase
    );

    tf_recovery_ui_render_transaction_progress();
}


static void tf_recovery_transaction_progress_phase(
    const char *phase
) {
    struct tf_recovery_transaction_progress *progress = (
        &tf_recovery_transaction_progress
    );

    if (!progress->active) {
        return;
    }

    tf_copy_string(
        progress->phase,
        sizeof(progress->phase),
        phase
    );

    tf_recovery_ui_render_transaction_progress();
}


static void tf_recovery_transaction_progress_reset_bytes(
    const char *phase,
    u64 total
) {
    struct tf_recovery_transaction_progress *progress = (
        &tf_recovery_transaction_progress
    );

    if (!progress->active) {
        return;
    }

    tf_copy_string(
        progress->phase,
        sizeof(progress->phase),
        phase
    );

    progress->bytes_completed = 0;
    progress->bytes_total = total;
    progress->last_render_bytes = 0;

    tf_recovery_ui_render_transaction_progress();
}


static void tf_recovery_transaction_progress_bytes(
    u64 completed
) {
    struct tf_recovery_transaction_progress *progress = (
        &tf_recovery_transaction_progress
    );

    if (!progress->active) {
        return;
    }

    if (
        completed
        > progress->bytes_total
    ) {
        completed = progress->bytes_total;
    }

    progress->bytes_completed = completed;

    int redraw = 0;

    if (
        completed
        == progress->bytes_total
    ) {
        redraw = 1;
    } else if (
        completed
        >= progress->last_render_bytes
        + TREEFORGE_RECOVERY_PROGRESS_REDRAW_BYTES
    ) {
        redraw = 1;
    }

    if (!redraw) {
        return;
    }

    progress->last_render_bytes = completed;

    tf_recovery_ui_render_transaction_progress();
}


static void tf_recovery_transaction_progress_verified(
    const struct tf_recovery_install_set_result *set,
    int image_index
) {
    struct tf_recovery_transaction_progress *progress = (
        &tf_recovery_transaction_progress
    );

    if (
        !set
        || !progress->active
    ) {
        return;
    }

    progress->image_index = image_index;
    progress->completed_images = (
        set->payload_verified_count
    );

    progress->bytes_completed = (
        progress->bytes_total
    );

    tf_copy_string(
        progress->phase,
        sizeof(progress->phase),
        "VERIFIED"
    );

    tf_recovery_ui_render_transaction_progress();
}


static void tf_recovery_transaction_progress_install_verified(
    void
) {
    struct tf_recovery_transaction_progress *progress = (
        &tf_recovery_transaction_progress
    );

    if (
        !progress->active
        || !progress->destructive
    ) {
        return;
    }

    progress->bytes_completed = (
        progress->bytes_total
    );

    progress->completed_images = (
        progress->image_index
        + 1
    );

    tf_copy_string(
        progress->phase,
        sizeof(progress->phase),
        "VERIFIED"
    );

    tf_recovery_ui_render_transaction_progress();
}


static void tf_recovery_transaction_progress_clear(
    void
) {
    memset(
        &tf_recovery_transaction_progress,
        0,
        sizeof(tf_recovery_transaction_progress)
    );
}


static u64 tf_recovery_install_set_transfer_generation = 0;


static void tf_recovery_install_set_begin_transfer_generation(
    void
) {
    tf_recovery_install_set_transfer_generation++;

    /*
     * Zero is reserved as "no observed generation" by the host.
     * Realistically this cannot wrap during one Recovery boot, but
     * keep the protocol fail-safe if it ever does.
     */
    if (
        tf_recovery_install_set_transfer_generation
        == 0
    ) {
        tf_recovery_install_set_transfer_generation = 1;
    }
}


struct tf_recovery_install_set_stream_reader {
    long fd;

    u64 expected_bytes;
    u64 remaining;
    u64 bytes_read;

    /*
     * Verification keeps the FIFO nonblocking while waiting for the
     * host. The first received byte establishes that rendezvous and is
     * then consumed through the normal authenticated stream reader.
     */
    unsigned char prefetched_byte;
    int prefetched_available;

    /*
     * Verification reports source bytes. Sparse destructive expansion
     * reports expanded destination bytes instead.
     */
    int suppress_progress;

    struct tf_sha256_context sha256;

    int error_stage;
    u64 error_errno;
};


static int tf_recovery_install_set_stream_read_exact(
    struct tf_recovery_install_set_stream_reader *reader,
    unsigned char *buffer,
    usize requested
) {
    if (
        !reader
        || reader->fd < 0
        || !buffer
        || requested == 0
        || (u64) requested > reader->remaining
    ) {
        return 0;
    }

    usize complete = 0;

    if (
        reader->prefetched_available
        && complete < requested
    ) {
        buffer[complete] = (
            reader->prefetched_byte
        );

        reader->prefetched_available = 0;

        tf_sha256_update(
            &reader->sha256,
            buffer + complete,
            1
        );

        complete++;
        reader->bytes_read++;
        reader->remaining--;

        if (!reader->suppress_progress) {
            tf_recovery_transaction_progress_bytes(
                reader->bytes_read
            );
        }
    }

    while (complete < requested) {
        long amount = tf_syscall3(
            SYS_READ,
            reader->fd,
            (long) (
                buffer
                + complete
            ),
            (long) (
                requested
                - complete
            )
        );

        if (amount == -11) {
            /*
             * The ADB writer exists but has not supplied the next
             * portion of the stream yet.
             */
            tf_recovery_adbd_maintain();

            tf_recovery_ui_sleep_ms(
                TREEFORGE_RECOVERY_UI_POLL_MS
            );

            continue;
        }

        if (amount < 0) {
            reader->error_stage = 2;
            reader->error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount == 0) {
            reader->error_stage = 3;
            return 0;
        }

            tf_sha256_update(
            &reader->sha256,
            buffer + complete,
            (usize) amount
        );

        complete += (
            (usize) amount
        );

        reader->bytes_read += (
            (u64) amount
        );

        reader->remaining -= (
            (u64) amount
        );

        if (!reader->suppress_progress) {
            tf_recovery_transaction_progress_bytes(
                reader->bytes_read
            );
        }
    }

    return 1;
}


static int tf_recovery_install_set_stream_skip(
    struct tf_recovery_install_set_stream_reader *reader,
    u64 bytes
) {
    unsigned char buffer[4096];

    while (bytes > 0) {
        usize amount = (
            bytes
                < (u64) sizeof(buffer)
            ? (usize) bytes
            : sizeof(buffer)
        );

        if (
            !tf_recovery_install_set_stream_read_exact(
                reader,
                buffer,
                amount
            )
        ) {
            return 0;
        }

        bytes -= (
            (u64) amount
        );
    }

    return 1;
}


static int tf_recovery_install_set_stream_finish(
    struct tf_recovery_install_set_stream_reader *reader,
    char sha256[65]
) {
    if (
        !reader
        || !sha256
        || reader->remaining != 0
    ) {
        return 0;
    }

    /*
     * The ADB sync writer must now close the FIFO. Because the source
     * descriptor is nonblocking, EAGAIN means the writer still exists
     * but has not closed yet. Only actual EOF proves exact framing.
     */
    unsigned char extra = 0;

    for (;;) {
        long amount = tf_syscall3(
            SYS_READ,
            reader->fd,
            (long) &extra,
            1
        );

        if (amount == -11) {
            tf_recovery_adbd_maintain();

            tf_recovery_ui_sleep_ms(
                TREEFORGE_RECOVERY_UI_POLL_MS
            );

            continue;
        }

        if (amount < 0) {
            reader->error_stage = 4;
            reader->error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount != 0) {
            reader->error_stage = 5;
            return 0;
        }

        break;
    }

    unsigned char digest[32];

    tf_sha256_final(
        &reader->sha256,
        digest
    );

    tf_sha256_hex(
        digest,
        sha256
    );

    return 1;
}


static int tf_recovery_verify_install_set_sparse_stream(
    struct tf_recovery_install_set_stream_reader *reader,
    const struct tf_recovery_install_set_image *image
) {
    unsigned char header[
        TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    ];

    if (
        !tf_recovery_install_set_stream_read_exact(
            reader,
            header,
            sizeof(header)
        )
    ) {
        return 0;
    }

    if (
        tf_lp_load_le32(header)
            != TREEFORGE_RECOVERY_SPARSE_MAGIC
    ) {
        reader->error_stage = 10;
        return 0;
    }

    u16 major_version = (
        tf_lp_load_le16(
            header + 4
        )
    );

    u16 file_header_size = (
        tf_lp_load_le16(
            header + 8
        )
    );

    u16 chunk_header_size = (
        tf_lp_load_le16(
            header + 10
        )
    );

    u32 block_size = (
        tf_lp_load_le32(
            header + 12
        )
    );

    u32 total_blocks = (
        tf_lp_load_le32(
            header + 16
        )
    );

    u32 total_chunks = (
        tf_lp_load_le32(
            header + 20
        )
    );

    if (
        major_version
            != TREEFORGE_RECOVERY_SPARSE_MAJOR_VERSION
        || file_header_size
            < TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
        || chunk_header_size
            < TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        || block_size == 0
        || (
            block_size % 4U
        ) != 0
        || total_blocks == 0
        || total_chunks == 0
    ) {
        reader->error_stage = 11;
        return 0;
    }

    if (
        block_size
            != image->sparse_block_size
        || total_blocks
            != image->sparse_total_blocks
        || total_chunks
            != image->sparse_total_chunks
    ) {
        reader->error_stage = 12;
        return 0;
    }

    if (
        file_header_size
        > TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    ) {
        if (
            !tf_recovery_install_set_stream_skip(
                reader,
                (u64) (
                    file_header_size
                    - TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
                )
            )
        ) {
            return 0;
        }
    }

    u64 output_blocks = 0;

    u32 raw_chunks = 0;
    u32 fill_chunks = 0;
    u32 dont_care_chunks = 0;
    u32 crc32_chunks = 0;

    for (
        u32 index = 0;
        index < total_chunks;
        index++
    ) {
        unsigned char chunk_header[
            TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        ];

        if (
            !tf_recovery_install_set_stream_read_exact(
                reader,
                chunk_header,
                sizeof(chunk_header)
            )
        ) {
            return 0;
        }

        u16 chunk_type = (
            tf_lp_load_le16(
                chunk_header
            )
        );

        u32 chunk_blocks = (
            tf_lp_load_le32(
                chunk_header + 4
            )
        );

        u32 total_size = (
            tf_lp_load_le32(
                chunk_header + 8
            )
        );

        if (
            total_size
            < chunk_header_size
        ) {
            reader->error_stage = 13;
            return 0;
        }

        if (
            chunk_header_size
            > TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        ) {
            if (
                !tf_recovery_install_set_stream_skip(
                    reader,
                    (u64) (
                        chunk_header_size
                        - TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
                    )
                )
            ) {
                return 0;
            }
        }

        u64 payload_bytes = (
            (u64) total_size
            - (u64) chunk_header_size
        );

        if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_RAW
        ) {
            u64 expected_payload = (
                (u64) chunk_blocks
                * (u64) block_size
            );

            if (
                payload_bytes
                != expected_payload
            ) {
                reader->error_stage = 14;
                return 0;
            }

            raw_chunks++;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_FILL
        ) {
            if (payload_bytes != 4) {
                reader->error_stage = 15;
                return 0;
            }

            fill_chunks++;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_DONT_CARE
        ) {
            if (payload_bytes != 0) {
                reader->error_stage = 16;
                return 0;
            }

            dont_care_chunks++;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_CRC32
        ) {
            if (
                payload_bytes != 4
                || chunk_blocks != 0
            ) {
                reader->error_stage = 17;
                return 0;
            }

            crc32_chunks++;
        } else {
            reader->error_stage = 18;
            return 0;
        }

        if (
            chunk_type
                != TREEFORGE_RECOVERY_SPARSE_CHUNK_CRC32
        ) {
            if (
                output_blocks
                > (
                    0xffffffffffffffffULL
                    - (u64) chunk_blocks
                )
            ) {
                reader->error_stage = 19;
                return 0;
            }

            output_blocks += (
                (u64) chunk_blocks
            );
        }

        if (
            payload_bytes > 0
            && !tf_recovery_install_set_stream_skip(
                reader,
                payload_bytes
            )
        ) {
            return 0;
        }
    }

    if (
        output_blocks
            != (u64) total_blocks
        || raw_chunks
            != image->sparse_raw_chunks
        || fill_chunks
            != image->sparse_fill_chunks
        || dont_care_chunks
            != image->sparse_dont_care_chunks
        || crc32_chunks
            != image->sparse_crc32_chunks
    ) {
        reader->error_stage = 20;
        return 0;
    }

    return 1;
}


static int tf_recovery_verify_install_set_stream_image(
    long *inputs,
    struct tf_recovery_install_set_result *set,
    int image_index,
    u64 *error_errno,
    int *error_stage
) {
    if (
        !inputs
        || !set
        || image_index < 0
        || image_index >= set->image_count
        || !error_errno
        || !error_stage
    ) {
        return 0;
    }

    struct tf_recovery_install_set_image *image = (
        &set->images[image_index]
    );

    u64 expected_payload_bytes = (
        tf_recovery_install_set_transport_bytes(
            set,
            image
        )
    );

    const char *expected_payload_sha256 = (
        tf_recovery_install_set_transport_sha256(
            set,
            image
        )
    );

    if (
        expected_payload_bytes == 0
        || !expected_payload_sha256[0]
    ) {
        return 0;
    }

    *error_errno = 0;
    *error_stage = 0;

    image->payload_verification_attempted = 1;
    image->payload_structure_valid = 0;
    image->payload_hash_succeeded = 0;
    image->payload_verified = 0;
    image->payload_bytes_received = 0;
    image->payload_sha256[0] = '\0';

    tf_recovery_transaction_progress_begin(
        set,
        image_index,
        "WAITING FOR HOST",
        0
    );

    /*
     * Cancellable verification rendezvous.
     *
     * Verification never creates a writable partition descriptor.
     * Keep the source FIFO nonblocking until the first payload byte
     * arrives so Recovery can continue servicing Power while no host
     * transfer is active.
     */
    long source = tf_open(
        TREEFORGE_RECOVERY_STREAM_FIFO_PATH,
        O_RDONLY
        | O_NONBLOCK
    );

    if (source < 0) {
        *error_stage = 1;
        *error_errno = (
            (u64) (-source)
        );

        return 0;
    }

    unsigned char first_stream_byte = 0;

    for (;;) {
        long amount = tf_syscall3(
            SYS_READ,
            source,
            (long) &first_stream_byte,
            1
        );

        if (amount == 1) {
            break;
        }

        /*
         * With a nonblocking FIFO:
         *
         *   0    = no host writer exists yet
         *  -11   = writer exists but no payload byte is ready yet
         *
         * Both remain safely cancellable because this verification
         * path has no partition destination.
         */
        if (
            amount < 0
            && amount != -11
        ) {
            *error_stage = 1;
            *error_errno = (
                (u64) (-amount)
            );

            tf_close(source);

            return 0;
        }

        int key = (
            tf_recovery_ui_poll_key_once(
                inputs
            )
        );

        if (key == KEY_POWER) {
            tf_close(source);

            image->payload_verification_attempted = 0;
            image->payload_structure_valid = 0;
            image->payload_hash_succeeded = 0;
            image->payload_verified = 0;
            image->payload_bytes_received = 0;
            image->payload_sha256[0] = '\0';

            *error_stage = 0;
            *error_errno = 0;

            return -1;
        }

        tf_recovery_adbd_maintain();

        tf_recovery_ui_sleep_ms(
            TREEFORGE_RECOVERY_UI_POLL_MS
        );
    }

    tf_recovery_transaction_progress_phase(
        "VERIFYING STREAM"
    );

    struct tf_recovery_install_set_stream_reader reader;

    memset(
        &reader,
        0,
        sizeof(reader)
    );

    reader.fd = source;
    reader.expected_bytes = (
        expected_payload_bytes
    );
    reader.remaining = (
        expected_payload_bytes
    );

    reader.prefetched_byte = (
        first_stream_byte
    );

    reader.prefetched_available = 1;

    tf_sha256_init(
        &reader.sha256
    );

    int structure_valid = 0;

    if (
        set->wire_version
            == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
        && image->manifest_payload_kind
            == TREEFORGE_RECOVERY_PAYLOAD_KIND_COW
    ) {
        /*
         * Read-only v2 COW transport milestone.
         *
         * Recovery proves:
         *   - exact payload length;
         *   - no trailing bytes;
         *   - exact SHA-256.
         *
         * It intentionally does not claim independent COW-format
         * parsing yet. That belongs to the AOSP COW/libsnapshot
         * runtime integration.
         */
        structure_valid = (
            tf_recovery_install_set_stream_skip(
                &reader,
                expected_payload_bytes
            )
        );
    } else if (
        image->image_format
        == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
    ) {
        structure_valid = (
            tf_recovery_install_set_stream_skip(
                &reader,
                expected_payload_bytes
            )
        );
    } else if (
        image->image_format
        == TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
    ) {
        structure_valid = (
            tf_recovery_verify_install_set_sparse_stream(
                &reader,
                image
            )
        );
    } else {
        reader.error_stage = 21;
    }

    if (!structure_valid) {
        *error_stage = (
            reader.error_stage
            ? reader.error_stage
            : 22
        );

        *error_errno = (
            reader.error_errno
        );

        tf_close(source);
        return 0;
    }

    image->payload_structure_valid = 1;

    char actual_sha256[65];

    if (
        !tf_recovery_install_set_stream_finish(
            &reader,
            actual_sha256
        )
    ) {
        *error_stage = (
            reader.error_stage
            ? reader.error_stage
            : 23
        );

        *error_errno = (
            reader.error_errno
        );

        tf_close(source);
        return 0;
    }

    tf_close(source);

    image->payload_bytes_received = (
        reader.bytes_read
    );

    image->payload_hash_succeeded = 1;

    tf_copy_string(
        image->payload_sha256,
        sizeof(image->payload_sha256),
        actual_sha256
    );

    if (
        image->payload_bytes_received
            != expected_payload_bytes
        || !tf_string_equal(
            image->payload_sha256,
            expected_payload_sha256
        )
    ) {
        *error_stage = 24;
        return 0;
    }

    image->payload_verified = 1;

    return 1;
}


static int tf_recovery_install_set_transfer_state(
    const struct tf_recovery_install_set_result *set,
    const char *state_name,
    int image_index,
    int stage,
    u64 error_errno
) {
    if (
        !set
        || !state_name
    ) {
        return 0;
    }

    char state[640];

    state[0] = '\0';

    usize position = 0;

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "treeforge-recovery-install-set-transfer-v1\n"
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "generation="
    );

    position = tf_append_u64(
        state,
        sizeof(state),
        position,
        tf_recovery_install_set_transfer_generation
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\nstate="
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        state_name
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\nindex="
    );

    position = tf_append_u64(
        state,
        sizeof(state),
        position,
        (
            image_index >= 0
            ? (u64) image_index
            : (u64) set->image_count
        )
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\nimage_count="
    );

    position = tf_append_u64(
        state,
        sizeof(state),
        position,
        (u64) set->image_count
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\nverified="
    );

    position = tf_append_u64(
        state,
        sizeof(state),
        position,
        (u64) set->payload_verified_count
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\ninstalled="
    );

    position = tf_append_u64(
        state,
        sizeof(state),
        position,
        (u64) set->install_written_count
    );

    if (
        image_index >= 0
        && image_index < set->image_count
    ) {
        const struct tf_recovery_install_set_image *image = (
            &set->images[image_index]
        );

        position = tf_append_text(
            state,
            sizeof(state),
            position,
            "\npartition="
        );

        position = tf_append_text(
            state,
            sizeof(state),
            position,
            image->canonical_name
        );

        position = tf_append_text(
            state,
            sizeof(state),
            position,
            "\nbytes="
        );

        position = tf_append_u64(
            state,
            sizeof(state),
            position,
            tf_recovery_install_set_transport_bytes(
                set,
                image
            )
        );

        position = tf_append_text(
            state,
            sizeof(state),
            position,
            "\nsha256="
        );

        position = tf_append_text(
            state,
            sizeof(state),
            position,
            tf_recovery_install_set_transport_sha256(
                set,
                image
            )
        );
    }

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\nstage="
    );

    position = tf_append_u64(
        state,
        sizeof(state),
        position,
        (u64) (
            stage >= 0
            ? stage
            : 0
        )
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\nerrno="
    );

    position = tf_append_u64(
        state,
        sizeof(state),
        position,
        error_errno
    );

    position = tf_append_text(
        state,
        sizeof(state),
        position,
        "\n"
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_INSTALL_SET_TRANSFER_STATE_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return 0;
    }

    int wrote = tf_write_buffer(
        fd,
        state,
        position
    );

    tf_close(fd);

    return wrote;
}


static int tf_recovery_verify_install_set_payloads(
    long *inputs,
    struct tf_recovery_install_set_result *set
) {
    if (
        !inputs
        || !set
        || !set->plan_resolved
        || !set->target_slot_safe
        || set->image_count <= 0
        || !tf_recovery_stream_fifo_ready
    ) {
        return 0;
    }

    tf_recovery_install_set_begin_transfer_generation();

    set->payload_verification_started = 1;
    set->payload_verified_count = 0;
    set->payload_verification_complete = 0;
    set->payload_error_stage = 0;
    set->payload_error_image_index = -1;
    set->payload_error_errno = 0;

    for (
        int index = 0;
        index < set->image_count;
        index++
    ) {
        char active_slot = (
            tf_resolve_active_slot()
        );

        if (
            active_slot != 'a'
            && active_slot != 'b'
        ) {
            set->payload_error_stage = 30;
            set->payload_error_image_index = index;

            tf_recovery_install_set_transfer_state(
                set,
                "error",
                index,
                set->payload_error_stage,
                0
            );

            return 0;
        }

        if (
            active_slot
            == set->target_slot
        ) {
            set->payload_error_stage = 31;
            set->payload_error_image_index = index;

            tf_recovery_install_set_transfer_state(
                set,
                "error",
                index,
                set->payload_error_stage,
                0
            );

            return 0;
        }

        if (
            !tf_recovery_install_set_transfer_state(
                set,
                "ready",
                index,
                0,
                0
            )
        ) {
            set->payload_error_stage = 32;
            set->payload_error_image_index = index;

            return 0;
        }

        u64 error_errno = 0;
        int error_stage = 0;

        int verification_result = (
            tf_recovery_verify_install_set_stream_image(
                inputs,
                set,
                index,
                &error_errno,
                &error_stage
            )
        );

        if (verification_result < 0) {
            /*
             * Verification is wholly non-destructive. Discard any
             * partial verification progress so a later attempt starts
             * again from image zero with a fresh host sequence.
             */
            set->payload_verification_started = 0;
            set->payload_verified_count = 0;
            set->payload_verification_complete = 0;
            set->payload_error_stage = 0;
            set->payload_error_image_index = -1;
            set->payload_error_errno = 0;

            for (
                int reset_index = 0;
                reset_index < set->image_count;
                reset_index++
            ) {
                struct tf_recovery_install_set_image *reset_image = (
                    &set->images[reset_index]
                );

                reset_image->payload_verification_attempted = 0;
                reset_image->payload_structure_valid = 0;
                reset_image->payload_hash_succeeded = 0;
                reset_image->payload_verified = 0;
                reset_image->payload_bytes_received = 0;
                reset_image->payload_sha256[0] = '\0';
            }

            tf_recovery_install_set_transfer_state(
                set,
                "cancelled",
                index,
                0,
                0
            );

            tf_recovery_transaction_progress_phase(
                "CANCELLED"
            );

            return -1;
        }

        if (!verification_result) {
            set->payload_error_stage = (
                100
                + error_stage
            );

            set->payload_error_image_index = (
                index
            );

            set->payload_error_errno = (
                error_errno
            );

            tf_recovery_install_set_transfer_state(
                set,
                "error",
                index,
                set->payload_error_stage,
                set->payload_error_errno
            );

            tf_recovery_transaction_progress_phase(
                "FAILED"
            );

            return 0;
        }

        set->payload_verified_count++;

        tf_recovery_transaction_progress_verified(
            set,
            index
        );
    }

    set->payload_verification_complete = 1;

    tf_recovery_install_set_transfer_state(
        set,
        "complete",
        -1,
        0,
        0
    );

    return 1;
}


static const struct tf_recovery_logical_partition *
tf_recovery_find_logical_partition_exact(
    const struct tf_recovery_lp_inventory *inventory,
    const char *partition_name,
    int *matches
) {
    if (
        !inventory
        || !partition_name
        || !matches
    ) {
        return 0;
    }

    *matches = 0;

    const struct tf_recovery_logical_partition *found = 0;

    for (
        int index = 0;
        index < inventory->partition_count;
        index++
    ) {
        const struct tf_recovery_logical_partition *record = (
            &inventory->partitions[index]
        );

        if (
            !tf_string_equal(
                record->partition_name,
                partition_name
            )
        ) {
            continue;
        }

        found = record;
        (*matches)++;
    }

    return found;
}


static int tf_recovery_lp_linear_extent_bounds(
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_extent *extent,
    u64 *offset_bytes,
    u64 *length_bytes
) {
    if (
        !inventory
        || !extent
        || !offset_bytes
        || !length_bytes
        || !inventory->super_data_region_resolved
        || inventory->super_first_logical_sector == 0
        || inventory->super_device_size_bytes == 0
        || extent->target_type
            != TREEFORGE_RECOVERY_LP_TARGET_LINEAR
        || extent->target_source != 0
        || !tf_string_equal(
            extent->block_device_name,
            "super"
        )
        || extent->num_sectors == 0
        || extent->target_data
            < inventory->super_first_logical_sector
    ) {
        return 0;
    }

    if (
        extent->target_data
            > (
                0xffffffffffffffffULL
                / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            )
        || extent->num_sectors
            > (
                0xffffffffffffffffULL
                / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            )
        || inventory->super_first_logical_sector
            > (
                0xffffffffffffffffULL
                / TREEFORGE_RECOVERY_LP_SECTOR_SIZE
            )
    ) {
        return 0;
    }

    u64 offset = (
        extent->target_data
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    u64 length = (
        extent->num_sectors
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    u64 first_logical_byte = (
        inventory->super_first_logical_sector
        * TREEFORGE_RECOVERY_LP_SECTOR_SIZE
    );

    if (
        offset < first_logical_byte
        || offset > inventory->super_device_size_bytes
        || length
            > (
                inventory->super_device_size_bytes
                - offset
            )
        || offset > inventory->super_capacity_bytes
        || length
            > (
                inventory->super_capacity_bytes
                - offset
            )
        || offset > 0x7fffffffffffffffULL
    ) {
        return 0;
    }

    *offset_bytes = offset;
    *length_bytes = length;

    return 1;
}


static int tf_recovery_lp_target_extents_nonoverlapping(
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_partition *partition
) {
    if (
        !inventory
        || !partition
    ) {
        return 0;
    }

    for (
        u32 local_extent = 0;
        local_extent < partition->num_extents;
        local_extent++
    ) {
        int matches = 0;

        const struct tf_recovery_logical_extent *target_extent = (
            tf_lp_find_partition_extent(
                inventory,
                partition,
                local_extent,
                &matches
            )
        );

        if (
            matches != 1
            || !target_extent
        ) {
            return 0;
        }

        u64 target_offset = 0;
        u64 target_length = 0;

        if (
            !tf_recovery_lp_linear_extent_bounds(
                inventory,
                target_extent,
                &target_offset,
                &target_length
            )
        ) {
            return 0;
        }

        u64 target_end = (
            target_offset
            + target_length
        );

        for (
            int index = 0;
            index < inventory->extent_count;
            index++
        ) {
            const struct tf_recovery_logical_extent *other = (
                &inventory->extents[index]
            );

            if (other == target_extent) {
                continue;
            }

            /*
             * ZERO extents do not own physical storage.
             *
             * Other block devices do not alias this single-super
             * milestone. The target itself already requires source 0.
             */
            if (
                other->target_type
                    != TREEFORGE_RECOVERY_LP_TARGET_LINEAR
                || other->target_source != 0
                || !tf_string_equal(
                    other->block_device_name,
                    "super"
                )
            ) {
                continue;
            }

            u64 other_offset = 0;
            u64 other_length = 0;

            if (
                !tf_recovery_lp_linear_extent_bounds(
                    inventory,
                    other,
                    &other_offset,
                    &other_length
                )
            ) {
                /*
                 * A malformed physical extent elsewhere in the same
                 * authoritative map makes destructive LP use unsafe.
                 */
                return 0;
            }

            u64 other_end = (
                other_offset
                + other_length
            );

            if (
                target_offset < other_end
                && other_offset < target_end
            ) {
                return 0;
            }
        }
    }

    return 1;
}


static int tf_recovery_logical_raw_target_ready(
    const struct tf_recovery_install_set_result *set,
    const struct tf_recovery_install_set_image *image,
    const struct tf_recovery_flash_target *target,
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_partition **partition_out
) {
    if (
        !set
        || !image
        || !target
        || !inventory
        || !inventory->geometry_resolved
        || !inventory->authoritative_slot_resolved
        || !inventory->authoritative_metadata_valid
        || !inventory->super_data_region_resolved
        || inventory->partitions_omitted
        || inventory->extents_omitted
        || inventory->authoritative_metadata_slot
            >= TREEFORGE_RECOVERY_LP_MAX_METADATA_SLOTS
    ) {
        return 0;
    }

    const struct tf_recovery_lp_slot_result *slot = (
        &inventory->slots[
            inventory->authoritative_metadata_slot
        ]
    );

    /*
     * First destructive LP milestone supports exactly one serialized
     * LP block device: canonical "super".
     */
    if (
        !slot->valid
        || slot->block_device_count != 1
    ) {
        return 0;
    }

    if (
        image->image_format
            != TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        || image->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        || image->target_flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || image->target_active
        || !image->target_selectable
        || !image->target_allocation_present
        || image->install_action
            != TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
        || image->source_bytes == 0
        || image->expanded_bytes
            != image->source_bytes
        || !image->sha256[0]
    ) {
        return 0;
    }

    if (
        target->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        || target->flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || target->slot != set->target_slot
        || target->active
        || !target->selectable
        || !target->allocation_present
        || target->num_extents == 0
        || target->capacity_bytes == 0
        || !tf_string_equal(
            target->partition_name,
            image->target_partition_name
        )
        || !tf_string_equal(
            target->canonical_name,
            image->canonical_name
        )
    ) {
        return 0;
    }

    /*
     * Deliberately exact for the first logical writer.
     *
     * We are not defining "short raw image" tail semantics yet.
     */
    if (
        image->source_bytes
            != target->capacity_bytes
        || image->target_capacity_bytes
            != target->capacity_bytes
    ) {
        return 0;
    }

    int partition_matches = 0;

    const struct tf_recovery_logical_partition *partition = (
        tf_recovery_find_logical_partition_exact(
            inventory,
            image->target_partition_name,
            &partition_matches
        )
    );

    if (
        partition_matches != 1
        || !partition
        || partition->metadata_slot
            != inventory->authoritative_metadata_slot
        || partition->slot != set->target_slot
        || partition->active
        || !partition->slot_pair
        || partition->num_extents == 0
        || partition->capacity_bytes == 0
        || partition->capacity_bytes
            != target->capacity_bytes
        || partition->first_extent_index
            != target->first_extent_index
        || partition->num_extents
            != target->num_extents
        || partition->attributes
            != target->attributes
        || !tf_string_equal(
            partition->partition_name,
            target->partition_name
        )
        || !tf_string_equal(
            partition->canonical_name,
            target->canonical_name
        )
    ) {
        return 0;
    }

    u64 total_extent_bytes = 0;

    for (
        u32 local_extent = 0;
        local_extent < partition->num_extents;
        local_extent++
    ) {
        int extent_matches = 0;

        const struct tf_recovery_logical_extent *extent = (
            tf_lp_find_partition_extent(
                inventory,
                partition,
                local_extent,
                &extent_matches
            )
        );

        if (
            extent_matches != 1
            || !extent
        ) {
            return 0;
        }

        u64 offset = 0;
        u64 length = 0;

        if (
            !tf_recovery_lp_linear_extent_bounds(
                inventory,
                extent,
                &offset,
                &length
            )
            || length
                > (
                    0xffffffffffffffffULL
                    - total_extent_bytes
                )
        ) {
            return 0;
        }

        total_extent_bytes += length;
    }

    if (
        total_extent_bytes
            != partition->capacity_bytes
        || total_extent_bytes
            != image->source_bytes
        || !tf_recovery_lp_target_extents_nonoverlapping(
            inventory,
            partition
        )
    ) {
        return 0;
    }

    if (partition_out) {
        *partition_out = partition;
    }

    return 1;
}


/*
 * Shared exact logical-allocation readback helper.
 *
 * The sparse writer is intentionally defined before the existing RAW
 * readback implementation, so declare the helper here rather than
 * relying on an implicit function declaration.
 */
static int tf_recovery_hash_logical_raw_exact_progress(
    long fd,
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_partition *partition,
    u64 bytes,
    char sha256[65],
    u64 *error_errno
);


static int tf_recovery_logical_sparse_target_ready(
    const struct tf_recovery_install_set_result *set,
    const struct tf_recovery_install_set_image *image,
    const struct tf_recovery_flash_target *target,
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_partition **partition_out
) {
    if (
        !set
        || !image
        || !target
        || !inventory
        || !inventory->geometry_resolved
        || !inventory->authoritative_slot_resolved
        || !inventory->authoritative_metadata_valid
        || !inventory->super_data_region_resolved
        || inventory->partitions_omitted
        || inventory->extents_omitted
        || inventory->authoritative_metadata_slot
            >= TREEFORGE_RECOVERY_LP_MAX_METADATA_SLOTS
    ) {
        return 0;
    }

    const struct tf_recovery_lp_slot_result *slot = (
        &inventory->slots[
            inventory->authoritative_metadata_slot
        ]
    );

    if (
        !slot->valid
        || slot->block_device_count != 1
    ) {
        return 0;
    }

    u64 described_chunks = (
        (u64) image->sparse_raw_chunks
        + (u64) image->sparse_fill_chunks
        + (u64) image->sparse_dont_care_chunks
        + (u64) image->sparse_crc32_chunks
    );

    u64 expected_expanded = (
        (u64) image->sparse_block_size
        * (u64) image->sparse_total_blocks
    );

    if (
        image->image_format
            != TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
        || image->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        || image->target_flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || image->target_active
        || !image->target_selectable
        || !image->target_allocation_present
        || image->install_action
            != TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
        || image->source_bytes == 0
        || image->expanded_bytes == 0
        || !image->sha256[0]
        || image->sparse_block_size == 0
        || (
            image->sparse_block_size % 4U
        ) != 0
        || image->sparse_total_blocks == 0
        || image->sparse_total_chunks == 0
        || described_chunks
            != (u64) image->sparse_total_chunks
        || expected_expanded
            != image->expanded_bytes
    ) {
        return 0;
    }

    if (
        target->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        || target->flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || target->slot != set->target_slot
        || target->active
        || !target->selectable
        || !target->allocation_present
        || target->num_extents == 0
        || target->capacity_bytes == 0
        || image->expanded_bytes
            != target->capacity_bytes
        || image->target_capacity_bytes
            != target->capacity_bytes
        || !tf_string_equal(
            target->partition_name,
            image->target_partition_name
        )
        || !tf_string_equal(
            target->canonical_name,
            image->canonical_name
        )
    ) {
        return 0;
    }

    int partition_matches = 0;

    const struct tf_recovery_logical_partition *partition = (
        tf_recovery_find_logical_partition_exact(
            inventory,
            image->target_partition_name,
            &partition_matches
        )
    );

    if (
        partition_matches != 1
        || !partition
        || partition->metadata_slot
            != inventory->authoritative_metadata_slot
        || partition->slot != set->target_slot
        || partition->active
        || !partition->slot_pair
        || partition->num_extents == 0
        || partition->capacity_bytes
            != target->capacity_bytes
        || partition->first_extent_index
            != target->first_extent_index
        || partition->num_extents
            != target->num_extents
        || partition->attributes
            != target->attributes
        || !tf_string_equal(
            partition->partition_name,
            target->partition_name
        )
        || !tf_string_equal(
            partition->canonical_name,
            target->canonical_name
        )
    ) {
        return 0;
    }

    u64 extent_bytes = 0;

    for (
        u32 local_extent = 0;
        local_extent < partition->num_extents;
        local_extent++
    ) {
        int matches = 0;

        const struct tf_recovery_logical_extent *extent = (
            tf_lp_find_partition_extent(
                inventory,
                partition,
                local_extent,
                &matches
            )
        );

        u64 offset = 0;
        u64 length = 0;

        if (
            matches != 1
            || !extent
            || !tf_recovery_lp_linear_extent_bounds(
                inventory,
                extent,
                &offset,
                &length
            )
            || length
                > (
                    0xffffffffffffffffULL
                    - extent_bytes
                )
        ) {
            return 0;
        }

        extent_bytes += length;
    }

    if (
        extent_bytes
            != partition->capacity_bytes
        || extent_bytes
            != image->expanded_bytes
        || !tf_recovery_lp_target_extents_nonoverlapping(
            inventory,
            partition
        )
    ) {
        return 0;
    }

    if (partition_out) {
        *partition_out = partition;
    }

    return 1;
}


struct tf_recovery_logical_extent_writer {
    long fd;

    const struct tf_recovery_lp_inventory *inventory;
    const struct tf_recovery_logical_partition *partition;

    u32 local_extent;
    u64 extent_remaining;

    u64 bytes_written;

    struct tf_sha256_context expanded_sha256;

    int error_stage;
    u64 error_errno;
};


static int tf_recovery_logical_extent_writer_seek(
    struct tf_recovery_logical_extent_writer *writer
) {
    if (
        !writer
        || writer->fd < 0
        || !writer->inventory
        || !writer->partition
        || writer->local_extent
            >= writer->partition->num_extents
    ) {
        return 0;
    }

    int matches = 0;

    const struct tf_recovery_logical_extent *extent = (
        tf_lp_find_partition_extent(
            writer->inventory,
            writer->partition,
            writer->local_extent,
            &matches
        )
    );

    u64 offset = 0;
    u64 length = 0;

    if (
        matches != 1
        || !extent
        || !tf_recovery_lp_linear_extent_bounds(
            writer->inventory,
            extent,
            &offset,
            &length
        )
    ) {
        writer->error_stage = 1;
        return 0;
    }

    long seek_result = tf_syscall3(
        SYS_LSEEK,
        writer->fd,
        (long) offset,
        SEEK_SET
    );

    if (
        seek_result < 0
        || (u64) seek_result != offset
    ) {
        writer->error_stage = 2;

        if (seek_result < 0) {
            writer->error_errno = (
                (u64) (-seek_result)
            );
        }

        return 0;
    }

    writer->extent_remaining = length;

    return 1;
}


static int tf_recovery_logical_extent_writer_init(
    struct tf_recovery_logical_extent_writer *writer,
    long fd,
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_partition *partition
) {
    if (
        !writer
        || fd < 0
        || !inventory
        || !partition
        || partition->num_extents == 0
    ) {
        return 0;
    }

    memset(
        writer,
        0,
        sizeof(*writer)
    );

    writer->fd = fd;
    writer->inventory = inventory;
    writer->partition = partition;
    writer->local_extent = 0;

    tf_sha256_init(
        &writer->expanded_sha256
    );

    return (
        tf_recovery_logical_extent_writer_seek(
            writer
        )
    );
}


static int tf_recovery_logical_extent_writer_write(
    struct tf_recovery_logical_extent_writer *writer,
    const unsigned char *buffer,
    u64 bytes
) {
    if (
        !writer
        || writer->fd < 0
        || !buffer
        || bytes == 0
    ) {
        return 0;
    }

    u64 consumed = 0;

    while (consumed < bytes) {
        if (writer->extent_remaining == 0) {
            writer->local_extent++;

            if (
                writer->local_extent
                >= writer->partition->num_extents
            ) {
                writer->error_stage = 3;
                return 0;
            }

            if (
                !tf_recovery_logical_extent_writer_seek(
                    writer
                )
            ) {
                return 0;
            }
        }

        u64 remaining = (
            bytes - consumed
        );

        usize requested = (
            remaining
                < writer->extent_remaining
            ? (usize) remaining
            : (
                writer->extent_remaining
                    < (u64) 0x7fffffffU
                ? (usize) writer->extent_remaining
                : (usize) 0x7fffffffU
            )
        );

        usize complete = 0;

        while (complete < requested) {
            long amount = tf_syscall3(
                SYS_WRITE,
                writer->fd,
                (long) (
                    buffer
                    + (usize) consumed
                    + complete
                ),
                (long) (
                    requested - complete
                )
            );

            if (amount < 0) {
                writer->error_stage = 4;
                writer->error_errno = (
                    (u64) (-amount)
                );

                return 0;
            }

            if (amount == 0) {
                writer->error_stage = 5;
                return 0;
            }

            tf_sha256_update(
                &writer->expanded_sha256,
                buffer
                    + (usize) consumed
                    + complete,
                (usize) amount
            );

            complete += (
                (usize) amount
            );

            writer->bytes_written += (
                (u64) amount
            );

            writer->extent_remaining -= (
                (u64) amount
            );

            tf_recovery_transaction_progress_bytes(
                writer->bytes_written
            );
        }

        consumed += (
            (u64) requested
        );
    }

    return 1;
}


static int tf_recovery_logical_extent_writer_zero(
    struct tf_recovery_logical_extent_writer *writer,
    u64 bytes
) {
    unsigned char zeros[4096];

    memset(
        zeros,
        0,
        sizeof(zeros)
    );

    while (bytes > 0) {
        usize amount = (
            bytes < (u64) sizeof(zeros)
            ? (usize) bytes
            : sizeof(zeros)
        );

        if (
            !tf_recovery_logical_extent_writer_write(
                writer,
                zeros,
                amount
            )
        ) {
            return 0;
        }

        bytes -= (
            (u64) amount
        );
    }

    return 1;
}


static int tf_recovery_logical_extent_writer_fill(
    struct tf_recovery_logical_extent_writer *writer,
    const unsigned char pattern[4],
    u64 bytes
) {
    if (
        !writer
        || !pattern
        || (
            bytes % 4ULL
        ) != 0
    ) {
        return 0;
    }

    unsigned char buffer[4096];

    for (
        usize index = 0;
        index < sizeof(buffer);
        index += 4
    ) {
        buffer[index] = pattern[0];
        buffer[index + 1] = pattern[1];
        buffer[index + 2] = pattern[2];
        buffer[index + 3] = pattern[3];
    }

    while (bytes > 0) {
        usize amount = (
            bytes < (u64) sizeof(buffer)
            ? (usize) bytes
            : sizeof(buffer)
        );

        if (
            !tf_recovery_logical_extent_writer_write(
                writer,
                buffer,
                amount
            )
        ) {
            return 0;
        }

        bytes -= (
            (u64) amount
        );
    }

    return 1;
}


/*
 * Expand one already-authorized Android sparse stream directly into
 * the existing logical extent map.
 *
 * TreeForge deliberately defines DONT_CARE as deterministic zero
 * output. This avoids retaining stale bytes from the previous slot
 * contents and gives the readback verifier one exact expanded image
 * identity.
 *
 * CRC32 chunks are validated structurally and consumed from the exact
 * authenticated source stream, but contribute no output bytes.
 */
static int tf_recovery_expand_sparse_stream_to_logical(
    struct tf_recovery_install_set_stream_reader *reader,
    const struct tf_recovery_install_set_image *image,
    struct tf_recovery_logical_extent_writer *writer
) {
    if (
        !reader
        || !image
        || !writer
    ) {
        return 0;
    }

    unsigned char header[
        TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    ];

    if (
        !tf_recovery_install_set_stream_read_exact(
            reader,
            header,
            sizeof(header)
        )
    ) {
        return 0;
    }

    if (
        tf_lp_load_le32(header)
            != TREEFORGE_RECOVERY_SPARSE_MAGIC
    ) {
        reader->error_stage = 30;
        return 0;
    }

    u16 major_version = (
        tf_lp_load_le16(
            header + 4
        )
    );

    u16 file_header_size = (
        tf_lp_load_le16(
            header + 8
        )
    );

    u16 chunk_header_size = (
        tf_lp_load_le16(
            header + 10
        )
    );

    u32 block_size = (
        tf_lp_load_le32(
            header + 12
        )
    );

    u32 total_blocks = (
        tf_lp_load_le32(
            header + 16
        )
    );

    u32 total_chunks = (
        tf_lp_load_le32(
            header + 20
        )
    );

    if (
        major_version
            != TREEFORGE_RECOVERY_SPARSE_MAJOR_VERSION
        || file_header_size
            < TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
        || chunk_header_size
            < TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        || block_size == 0
        || (
            block_size % 4U
        ) != 0
        || total_blocks == 0
        || total_chunks == 0
        || block_size
            != image->sparse_block_size
        || total_blocks
            != image->sparse_total_blocks
        || total_chunks
            != image->sparse_total_chunks
    ) {
        reader->error_stage = 31;
        return 0;
    }

    if (
        file_header_size
        > TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
    ) {
        if (
            !tf_recovery_install_set_stream_skip(
                reader,
                (u64) (
                    file_header_size
                    - TREEFORGE_RECOVERY_SPARSE_HEADER_SIZE
                )
            )
        ) {
            return 0;
        }
    }

    u64 output_blocks = 0;

    u32 raw_chunks = 0;
    u32 fill_chunks = 0;
    u32 dont_care_chunks = 0;
    u32 crc32_chunks = 0;

    unsigned char payload[4096];

    for (
        u32 chunk_index = 0;
        chunk_index < total_chunks;
        chunk_index++
    ) {
        unsigned char chunk_header[
            TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        ];

        if (
            !tf_recovery_install_set_stream_read_exact(
                reader,
                chunk_header,
                sizeof(chunk_header)
            )
        ) {
            return 0;
        }

        u16 chunk_type = (
            tf_lp_load_le16(
                chunk_header
            )
        );

        u32 chunk_blocks = (
            tf_lp_load_le32(
                chunk_header + 4
            )
        );

        u32 total_size = (
            tf_lp_load_le32(
                chunk_header + 8
            )
        );

        if (
            total_size < chunk_header_size
        ) {
            reader->error_stage = 32;
            return 0;
        }

        if (
            chunk_header_size
            > TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
        ) {
            if (
                !tf_recovery_install_set_stream_skip(
                    reader,
                    (u64) (
                        chunk_header_size
                        - TREEFORGE_RECOVERY_SPARSE_CHUNK_HEADER_SIZE
                    )
                )
            ) {
                return 0;
            }
        }

        u64 payload_bytes = (
            (u64) total_size
            - (u64) chunk_header_size
        );

        u64 output_bytes = (
            (u64) chunk_blocks
            * (u64) block_size
        );

        if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_RAW
        ) {
            if (
                payload_bytes != output_bytes
            ) {
                reader->error_stage = 33;
                return 0;
            }

            raw_chunks++;

            u64 remaining = payload_bytes;

            while (remaining > 0) {
                usize amount = (
                    remaining < (u64) sizeof(payload)
                    ? (usize) remaining
                    : sizeof(payload)
                );

                if (
                    !tf_recovery_install_set_stream_read_exact(
                        reader,
                        payload,
                        amount
                    )
                    || !tf_recovery_logical_extent_writer_write(
                        writer,
                        payload,
                        amount
                    )
                ) {
                    return 0;
                }

                remaining -= (
                    (u64) amount
                );
            }
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_FILL
        ) {
            if (
                payload_bytes != 4ULL
            ) {
                reader->error_stage = 34;
                return 0;
            }

            unsigned char fill[4];

            if (
                !tf_recovery_install_set_stream_read_exact(
                    reader,
                    fill,
                    sizeof(fill)
                )
                || !tf_recovery_logical_extent_writer_fill(
                    writer,
                    fill,
                    output_bytes
                )
            ) {
                return 0;
            }

            fill_chunks++;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_DONT_CARE
        ) {
            if (payload_bytes != 0) {
                reader->error_stage = 35;
                return 0;
            }

            if (
                !tf_recovery_logical_extent_writer_zero(
                    writer,
                    output_bytes
                )
            ) {
                return 0;
            }

            dont_care_chunks++;
        } else if (
            chunk_type
            == TREEFORGE_RECOVERY_SPARSE_CHUNK_CRC32
        ) {
            if (
                payload_bytes != 4ULL
                || chunk_blocks != 0
            ) {
                reader->error_stage = 36;
                return 0;
            }

            unsigned char crc32_payload[4];

            if (
                !tf_recovery_install_set_stream_read_exact(
                    reader,
                    crc32_payload,
                    sizeof(crc32_payload)
                )
            ) {
                return 0;
            }

            crc32_chunks++;
        } else {
            reader->error_stage = 37;
            return 0;
        }

        if (
            chunk_type
                != TREEFORGE_RECOVERY_SPARSE_CHUNK_CRC32
        ) {
            if (
                output_blocks
                    > (
                        0xffffffffffffffffULL
                        - (u64) chunk_blocks
                    )
            ) {
                reader->error_stage = 38;
                return 0;
            }

            output_blocks += (
                (u64) chunk_blocks
            );

            if (
                output_blocks
                > (u64) total_blocks
            ) {
                reader->error_stage = 39;
                return 0;
            }
        }
    }

    if (
        output_blocks != (u64) total_blocks
        || raw_chunks
            != image->sparse_raw_chunks
        || fill_chunks
            != image->sparse_fill_chunks
        || dont_care_chunks
            != image->sparse_dont_care_chunks
        || crc32_chunks
            != image->sparse_crc32_chunks
        || writer->bytes_written
            != image->expanded_bytes
    ) {
        reader->error_stage = 40;
        return 0;
    }

    return 1;
}


static int tf_recovery_write_install_set_logical_sparse_image(
    long *inputs,
    struct tf_recovery_install_set_result *set,
    int image_index
) {
    if (
        !inputs
        || !set
        || image_index < 0
        || image_index >= set->image_count
    ) {
        return 0;
    }

    struct tf_recovery_install_set_image *image = (
        &set->images[image_index]
    );

    image->install_error_stage = 0;
    image->install_error_errno = 0;

    if (
        !set->install_transaction_started
        || set->install_transaction_complete
        || set->install_transaction_failed
        || image_index
            != set->install_written_count
        || image->install_write_attempted
        || image->install_written
        || !image->payload_verified
        || image->image_format
            != TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
        || image->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        || image->target_flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || image->target_active
        || !image->target_selectable
        || !image->target_allocation_present
        || image->install_action
            != TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
    ) {
        image->install_error_stage = 80;
        return 0;
    }

    const struct tf_recovery_flash_target *target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    const struct tf_recovery_logical_partition *partition = 0;

    if (
        !tf_recovery_logical_sparse_target_ready(
            set,
            image,
            target,
            &tf_recovery_lp_inventory,
            &partition
        )
    ) {
        image->install_error_stage = 81;
        return 0;
    }

    image->install_write_attempted = 1;
    image->install_written = 0;
    image->install_readback_verified = 0;
    image->install_bytes_written = 0;
    image->install_stream_sha256[0] = '\0';
    image->install_expanded_sha256[0] = '\0';
    image->install_readback_sha256[0] = '\0';

    char active_slot = (
        tf_resolve_active_slot()
    );

    if (
        (
            active_slot != 'a'
            && active_slot != 'b'
        )
        || active_slot == set->target_slot
    ) {
        image->install_error_stage = 82;
        return 0;
    }

    /*
     * First complete LP revalidation before host authorization.
     */
    if (
        !tf_collect_inventory(
            &tf_recovery_inventory
        )
    ) {
        image->install_error_stage = 83;
        return 0;
    }

    target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    partition = 0;

    if (
        !tf_recovery_logical_sparse_target_ready(
            set,
            image,
            target,
            &tf_recovery_lp_inventory,
            &partition
        )
    ) {
        image->install_error_stage = 84;
        return 0;
    }

    tf_recovery_transaction_progress_begin(
        set,
        image_index,
        "WAITING FOR HOST",
        1
    );

    if (
        !tf_recovery_install_set_transfer_state(
            set,
            "write-ready",
            image_index,
            0,
            0
        )
    ) {
        image->install_error_stage = 85;
        return 0;
    }

    long source = tf_open(
        TREEFORGE_RECOVERY_STREAM_FIFO_PATH,
        O_RDONLY
        | O_NONBLOCK
    );

    if (source < 0) {
        image->install_error_stage = 86;
        image->install_error_errno = (
            (u64) (-source)
        );

        return 0;
    }

    unsigned char first_stream_byte = 0;

    for (;;) {
        long amount = tf_syscall3(
            SYS_READ,
            source,
            (long) &first_stream_byte,
            1
        );

        if (amount == 1) {
            break;
        }

        if (
            amount < 0
            && amount != -11
        ) {
            image->install_error_stage = 87;
            image->install_error_errno = (
                (u64) (-amount)
            );

            tf_close(source);

            return 0;
        }

        int key = (
            tf_recovery_ui_poll_key_once(
                inputs
            )
        );

        if (
            key == KEY_POWER
            && image_index == 0
            && set->install_written_count == 0
        ) {
            tf_close(source);

            image->install_write_attempted = 0;
            image->install_error_stage = 0;
            image->install_error_errno = 0;

            tf_recovery_install_set_transfer_state(
                set,
                "write-cancelled",
                image_index,
                0,
                0
            );

            tf_recovery_transaction_progress_phase(
                "CANCELLED"
            );

            return -1;
        }

        tf_recovery_adbd_maintain();

        tf_recovery_ui_sleep_ms(
            TREEFORGE_RECOVERY_UI_POLL_MS
        );
    }

    tf_recovery_transaction_progress_phase(
        "REVALIDATING TARGET"
    );

    /*
     * First source byte commits the transaction, but still does not
     * authorize a writable super descriptor.
     */
    active_slot = tf_resolve_active_slot();

    if (
        (
            active_slot != 'a'
            && active_slot != 'b'
        )
        || active_slot == set->target_slot
    ) {
        tf_close(source);

        image->install_error_stage = 88;
        return 0;
    }

    if (
        !tf_collect_inventory(
            &tf_recovery_inventory
        )
    ) {
        tf_close(source);

        image->install_error_stage = 89;
        return 0;
    }

    target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    partition = 0;

    if (
        !tf_recovery_logical_sparse_target_ready(
            set,
            image,
            target,
            &tf_recovery_lp_inventory,
            &partition
        )
    ) {
        tf_close(source);

        image->install_error_stage = 90;
        return 0;
    }

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            tf_recovery_lp_inventory.super_major,
            tf_recovery_lp_inventory.super_minor,
            &encoded_device
        )
    ) {
        tf_close(source);

        image->install_error_stage = 91;
        return 0;
    }

    /*
     * Same destructive boundary as the accepted RAW logical writer:
     * only after the second slot + LP + extent-map revalidation may
     * super become writable.
     */
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        S_IFBLK | 0600,
        (long) encoded_device
    );

    if (node_result < 0) {
        tf_close(source);

        image->install_error_stage = 92;
        image->install_error_errno = (
            (u64) (-node_result)
        );

        return 0;
    }

    long destination = tf_open(
        TREEFORGE_RECOVERY_LP_NODE_PATH,
        O_WRONLY
    );

    if (destination < 0) {
        tf_close(source);

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            0
        );

        image->install_error_stage = 93;
        image->install_error_errno = (
            (u64) (-destination)
        );

        return 0;
    }

    tf_recovery_transaction_progress_reset_bytes(
        "FLASHING",
        image->expanded_bytes
    );

    struct tf_recovery_install_set_stream_reader reader;

    memset(
        &reader,
        0,
        sizeof(reader)
    );

    reader.fd = source;
    reader.expected_bytes = image->source_bytes;
    reader.remaining = image->source_bytes;
    reader.prefetched_byte = first_stream_byte;
    reader.prefetched_available = 1;
    reader.suppress_progress = 1;

    tf_sha256_init(
        &reader.sha256
    );

    struct tf_recovery_logical_extent_writer writer;

    int write_failed = 0;

    if (
        !tf_recovery_logical_extent_writer_init(
            &writer,
            destination,
            &tf_recovery_lp_inventory,
            partition
        )
    ) {
        image->install_error_stage = 94;
        write_failed = 1;
    }

    if (
        !write_failed
        && !tf_recovery_expand_sparse_stream_to_logical(
            &reader,
            image,
            &writer
        )
    ) {
        if (writer.error_stage) {
            image->install_error_stage = (
                120 + writer.error_stage
            );

            image->install_error_errno = (
                writer.error_errno
            );
        } else {
            image->install_error_stage = (
                100
                + (
                    reader.error_stage
                    ? reader.error_stage
                    : 1
                )
            );

            image->install_error_errno = (
                reader.error_errno
            );
        }

        write_failed = 1;
    }

    image->install_bytes_written = (
        writer.bytes_written
    );

    if (!write_failed) {
        if (
            !tf_recovery_install_set_stream_finish(
                &reader,
                image->install_stream_sha256
            )
        ) {
            image->install_error_stage = 150;
            image->install_error_errno = (
                reader.error_errno
            );

            write_failed = 1;
        }
    }

    if (
        !write_failed
        && !tf_string_equal(
            image->install_stream_sha256,
            image->sha256
        )
    ) {
        /*
         * The second destructive transfer must be the same sparse
         * source that passed the non-destructive payload verifier.
         */
        image->install_error_stage = 151;
        write_failed = 1;
    }

    if (!write_failed) {
        if (
            writer.bytes_written
                != image->expanded_bytes
            || writer.local_extent
                != (
                    partition->num_extents - 1
                )
            || writer.extent_remaining != 0
        ) {
            image->install_error_stage = 152;
            write_failed = 1;
        }
    }

    if (!write_failed) {
        unsigned char digest[32];

        tf_sha256_final(
            &writer.expanded_sha256,
            digest
        );

        tf_sha256_hex(
            digest,
            image->install_expanded_sha256
        );
    }

    /*
     * Once super was writable, always flush even a failed partial
     * sparse expansion.
     */
    tf_recovery_transaction_progress_phase(
        "SYNCING"
    );

    long fsync_result = tf_syscall1(
        SYS_FSYNC,
        destination
    );

    if (
        fsync_result != 0
        && !write_failed
    ) {
        image->install_error_stage = 153;
        image->install_error_errno = (
            (u64) (-fsync_result)
        );

        write_failed = 1;
    }

    tf_close(destination);
    tf_close(source);

    destination = -1;
    source = -1;

    tf_syscall1(
        SYS_SYNC,
        0
    );

    long cleanup_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    if (
        cleanup_result < 0
        && cleanup_result != -2
        && !write_failed
    ) {
        image->install_error_stage = 154;
        image->install_error_errno = (
            (u64) (-cleanup_result)
        );

        write_failed = 1;
    }

    /*
     * Fresh authoritative LP parse before independent readback.
     */
    if (
        !write_failed
        && !tf_collect_inventory(
            &tf_recovery_inventory
        )
    ) {
        image->install_error_stage = 155;
        write_failed = 1;
    }

    if (!write_failed) {
        target = (
            tf_recovery_find_unified_flash_target(
                image->target_partition_name
            )
        );

        partition = 0;

        if (
            !tf_recovery_logical_sparse_target_ready(
                set,
                image,
                target,
                &tf_recovery_lp_inventory,
                &partition
            )
        ) {
            image->install_error_stage = 156;
            write_failed = 1;
        }
    }

    if (!write_failed) {
        encoded_device = 0;

        if (
            !tf_encode_device_number(
                tf_recovery_lp_inventory.super_major,
                tf_recovery_lp_inventory.super_minor,
                &encoded_device
            )
        ) {
            image->install_error_stage = 157;
            write_failed = 1;
        }
    }

    if (!write_failed) {
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            0
        );

        node_result = tf_syscall4(
            SYS_MKNODAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            S_IFBLK | 0400,
            (long) encoded_device
        );

        if (node_result < 0) {
            image->install_error_stage = 158;
            image->install_error_errno = (
                (u64) (-node_result)
            );

            write_failed = 1;
        }
    }

    if (!write_failed) {
        tf_recovery_transaction_progress_reset_bytes(
            "READBACK VERIFY",
            image->expanded_bytes
        );

        long verify = tf_open(
            TREEFORGE_RECOVERY_LP_NODE_PATH,
            O_RDONLY
        );

        if (verify < 0) {
            image->install_error_stage = 159;
            image->install_error_errno = (
                (u64) (-verify)
            );

            write_failed = 1;
        } else {
            u64 verify_errno = 0;

            if (
                !tf_recovery_hash_logical_raw_exact_progress(
                    verify,
                    &tf_recovery_lp_inventory,
                    partition,
                    image->expanded_bytes,
                    image->install_readback_sha256,
                    &verify_errno
                )
            ) {
                image->install_error_stage = 160;
                image->install_error_errno = (
                    verify_errno
                );

                write_failed = 1;
            }

            tf_close(verify);
        }
    }

    cleanup_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    if (
        cleanup_result < 0
        && cleanup_result != -2
        && !write_failed
    ) {
        image->install_error_stage = 161;
        image->install_error_errno = (
            (u64) (-cleanup_result)
        );

        write_failed = 1;
    }

    /*
     * Sparse source SHA and expanded partition SHA are intentionally
     * different identities. Successful installation requires:
     *
     *   exact sparse transfer == authorized package SHA
     *
     * and independently:
     *
     *   expanded writer SHA == reopened logical readback SHA
     */
    if (
        !write_failed
        && image->install_expanded_sha256[0]
        && tf_string_equal(
            image->install_expanded_sha256,
            image->install_readback_sha256
        )
    ) {
        image->install_readback_verified = 1;
        image->install_written = 1;
    } else if (!write_failed) {
        image->install_error_stage = 162;
        write_failed = 1;
    }

    if (
        write_failed
        || !image->install_written
    ) {
        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    tf_recovery_transaction_progress_install_verified();

    return 1;
}


static int tf_recovery_hash_logical_raw_exact_progress(
    long fd,
    const struct tf_recovery_lp_inventory *inventory,
    const struct tf_recovery_logical_partition *partition,
    u64 bytes,
    char sha256[65],
    u64 *error_errno
) {
    if (
        fd < 0
        || !inventory
        || !partition
        || bytes == 0
        || bytes != partition->capacity_bytes
        || !sha256
        || !error_errno
    ) {
        return 0;
    }

    *error_errno = 0;

    struct tf_sha256_context context;

    tf_sha256_init(
        &context
    );

    unsigned char buffer[4096];

    u64 completed = 0;

    for (
        u32 local_extent = 0;
        local_extent < partition->num_extents;
        local_extent++
    ) {
        int extent_matches = 0;

        const struct tf_recovery_logical_extent *extent = (
            tf_lp_find_partition_extent(
                inventory,
                partition,
                local_extent,
                &extent_matches
            )
        );

        if (
            extent_matches != 1
            || !extent
        ) {
            return 0;
        }

        u64 offset = 0;
        u64 length = 0;

        if (
            !tf_recovery_lp_linear_extent_bounds(
                inventory,
                extent,
                &offset,
                &length
            )
        ) {
            return 0;
        }

        long seek_result = tf_syscall3(
            SYS_LSEEK,
            fd,
            (long) offset,
            SEEK_SET
        );

        if (seek_result < 0) {
            *error_errno = (
                (u64) (-seek_result)
            );

            return 0;
        }

        if (
            (u64) seek_result
            != offset
        ) {
            return 0;
        }

        u64 remaining = length;

        while (remaining > 0) {
            usize requested = (
                remaining
                    < (u64) sizeof(buffer)
                ? (usize) remaining
                : sizeof(buffer)
            );

            long amount = tf_syscall3(
                SYS_READ,
                fd,
                (long) buffer,
                (long) requested
            );

            if (amount < 0) {
                *error_errno = (
                    (u64) (-amount)
                );

                return 0;
            }

            if (amount == 0) {
                return 0;
            }

            tf_sha256_update(
                &context,
                buffer,
                (usize) amount
            );

            completed += (
                (u64) amount
            );

            remaining -= (
                (u64) amount
            );

            tf_recovery_transaction_progress_bytes(
                completed
            );
        }
    }

    if (completed != bytes) {
        return 0;
    }

    unsigned char digest[32];

    tf_sha256_final(
        &context,
        digest
    );

    tf_sha256_hex(
        digest,
        sha256
    );

    return 1;
}


static int tf_recovery_install_set_existing_allocation_transaction_ready(
    const struct tf_recovery_install_set_result *set
) {
    if (
        !set
        || set->wire_version
            != TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V1
        || !set->plan_resolved
        || !set->target_slot_safe
        || !set->payload_verification_complete
        || set->payload_verified_count
            != set->image_count
        || set->image_count <= 0
        || set->install_transaction_started
    ) {
        return 0;
    }

    for (
        int index = 0;
        index < set->image_count;
        index++
    ) {
        const struct tf_recovery_install_set_image *image = (
            &set->images[index]
        );

        /*
         * Whole-set invariant:
         *
         * Every member must be destructively supported against the
         * current live topology before image zero may begin.
         */
        if (
            !image->payload_verified
            || image->target_flash_policy
                != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
            || image->target_active
            || !image->target_selectable
            || image->install_action
                != TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
            || image->source_bytes == 0
            || image->expanded_bytes == 0
            || !image->sha256[0]
            || image->install_write_attempted
            || image->install_written
        ) {
            return 0;
        }

        const struct tf_recovery_flash_target *target = (
            tf_recovery_find_unified_flash_target(
                image->target_partition_name
            )
        );

        if (!target) {
            return 0;
        }

        if (
            image->target_type
                == TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        ) {
            /*
             * Physical sparse writes remain deliberately unsupported.
             */
            if (
                image->image_format
                    != TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
                || image->expanded_bytes
                    != image->source_bytes
                || target->target_type
                    != TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
                || target->flash_policy
                    != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
                || target->slot
                    != set->target_slot
                || target->active
                || !target->selectable
                || image->source_bytes
                    > target->capacity_bytes
                || !tf_string_equal(
                    target->partition_name,
                    image->target_partition_name
                )
                || !tf_string_equal(
                    target->canonical_name,
                    image->canonical_name
                )
            ) {
                return 0;
            }

            continue;
        }

        if (
            image->target_type
                == TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        ) {
            if (
                image->image_format
                == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
            ) {
                if (
                    !tf_recovery_logical_raw_target_ready(
                        set,
                        image,
                        target,
                        &tf_recovery_lp_inventory,
                        0
                    )
                ) {
                    return 0;
                }

                continue;
            }

            if (
                image->image_format
                == TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
            ) {
                if (
                    !tf_recovery_logical_sparse_target_ready(
                        set,
                        image,
                        target,
                        &tf_recovery_lp_inventory,
                        0
                    )
                ) {
                    return 0;
                }

                continue;
            }

            return 0;
        }

        return 0;
    }

    return 1;
}


static int tf_recovery_hash_fd_exact_progress(
    long fd,
    u64 bytes,
    char sha256[65],
    u64 *error_errno
) {
    if (
        fd < 0
        || bytes == 0
        || !sha256
        || !error_errno
    ) {
        return 0;
    }

    *error_errno = 0;

    struct tf_sha256_context context;

    tf_sha256_init(
        &context
    );

    unsigned char buffer[4096];

    u64 remaining = bytes;
    u64 completed = 0;

    while (remaining > 0) {
        usize requested = (
            remaining < (u64) sizeof(buffer)
            ? (usize) remaining
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) buffer,
            (long) requested
        );

        if (amount < 0) {
            *error_errno = (
                (u64) (-amount)
            );

            return 0;
        }

        if (amount == 0) {
            return 0;
        }

        tf_sha256_update(
            &context,
            buffer,
            (usize) amount
        );

        completed += (
            (u64) amount
        );

        remaining -= (
            (u64) amount
        );

        tf_recovery_transaction_progress_bytes(
            completed
        );
    }

    unsigned char digest[32];

    tf_sha256_final(
        &context,
        digest
    );

    tf_sha256_hex(
        digest,
        sha256
    );

    return 1;
}


static int tf_recovery_write_install_set_physical_raw_image(
    long *inputs,
    struct tf_recovery_install_set_result *set,
    int image_index
) {
    if (
        !set
        || image_index < 0
        || image_index >= set->image_count
    ) {
        return 0;
    }

    struct tf_recovery_install_set_image *image = (
        &set->images[image_index]
    );


    /*
     * Validate before marking the image attempted.
     *
     * The previous generalized writer inherited the old single-image
     * initialization order and set install_write_attempted=1 before
     * checking install_write_attempted, causing every transaction to
     * reject image zero at stage 1.
     */
    image->install_error_stage = 0;
    image->install_error_errno = 0;

    if (
        !set->install_transaction_started
        || set->install_transaction_complete
        || set->install_transaction_failed
        || image_index
            != set->install_written_count
        || image->install_write_attempted
        || image->install_written
        || !image->payload_verified
        || image->image_format
            != TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        || image->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        || image->target_flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || image->target_active
        || !image->target_selectable
        || image->install_action
            != TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
        || image->source_bytes == 0
        || image->expanded_bytes
            != image->source_bytes
        || !image->sha256[0]
    ) {
        image->install_error_stage = 1;
        return 0;
    }

    /*
     * The image becomes an attempted destructive member only after
     * the complete per-image gate has passed.
     */
    image->install_write_attempted = 1;
    image->install_written = 0;
    image->install_readback_verified = 0;
    image->install_bytes_written = 0;
    image->install_stream_sha256[0] = '\0';
    image->install_readback_sha256[0] = '\0';

    char active_slot = (
        tf_resolve_active_slot()
    );

    if (
        active_slot != 'a'
        && active_slot != 'b'
    ) {
        image->install_error_stage = 2;
        return 0;
    }

    if (
        active_slot
        == set->target_slot
    ) {
        image->install_error_stage = 3;
        return 0;
    }

    /*
     * Refresh physical + unified runtime topology immediately before
     * destructive authorization. Do not trust device numbers captured
     * during earlier package planning.
     */
    if (
        !tf_collect_inventory(
            &tf_recovery_inventory
        )
    ) {
        image->install_error_stage = 4;
        return 0;
    }

    const struct tf_recovery_flash_target *target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    if (
        !target
        || target->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        || target->flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || target->slot
            != set->target_slot
        || target->active
        || !target->selectable
        || !tf_string_equal(
            target->canonical_name,
            image->canonical_name
        )
        || !tf_string_equal(
            target->partition_name,
            image->target_partition_name
        )
        || image->source_bytes
            > target->capacity_bytes
    ) {
        image->install_error_stage = 5;
        return 0;
    }

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            target->physical_major,
            target->physical_minor,
            &encoded_device
        )
    ) {
        image->install_error_stage = 6;
        return 0;
    }

    tf_recovery_transaction_progress_begin(
        set,
        image_index,
        "WAITING FOR HOST",
        1
    );

    if (
        !tf_recovery_install_set_transfer_state(
            set,
            "write-ready",
            image_index,
            0,
            0
        )
    ) {
        image->install_error_stage = 7;

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    /*
     * Cancellable host rendezvous.
     *
     * The FIFO is nonblocking while no partition descriptor exists.
     * Power may cancel until the first payload byte is received.
     *
     * Once that first byte arrives the transaction is committed and
     * proceeds through target revalidation before any writable block
     * node can be created.
     */
    long source = tf_open(
        TREEFORGE_RECOVERY_STREAM_FIFO_PATH,
        O_RDONLY
        | O_NONBLOCK
    );

    if (source < 0) {
        image->install_error_stage = 8;
        image->install_error_errno = (
            (u64) (-source)
        );

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    unsigned char first_stream_byte = 0;
    int first_stream_byte_ready = 0;

    while (!first_stream_byte_ready) {
        long amount = tf_syscall3(
            SYS_READ,
            source,
            (long) &first_stream_byte,
            1
        );

        if (amount == 1) {
            first_stream_byte_ready = 1;
            break;
        }

        if (
            amount < 0
            && amount != -11
        ) {
            tf_close(source);

            image->install_error_stage = 8;
            image->install_error_errno = (
                (u64) (-amount)
            );

            tf_recovery_install_set_transfer_state(
                set,
                "write-error",
                image_index,
                image->install_error_stage,
                image->install_error_errno
            );

            tf_recovery_transaction_progress_phase(
                "FAILED"
            );

            return 0;
        }

        int key = tf_recovery_ui_poll_key_once(
            inputs
        );

        if (
            key == KEY_POWER
            && image_index == 0
            && set->install_written_count == 0
        ) {
            tf_close(source);

            /*
             * Cancellation exists only before the first transaction
             * member commits. No partition descriptor has existed and
             * no partition byte has been written.
             *
             * Once any image has completed, later host rendezvous waits
             * are part of an already-destructive transaction and cannot
             * be cancelled.
             */
            image->install_write_attempted = 0;
            image->install_error_stage = 0;
            image->install_error_errno = 0;

            tf_recovery_install_set_transfer_state(
                set,
                "write-cancelled",
                image_index,
                0,
                0
            );

            tf_recovery_transaction_progress_phase(
                "CANCELLED"
            );

            return -1;
        }

        tf_recovery_adbd_maintain();

        tf_recovery_ui_sleep_ms(
            TREEFORGE_RECOVERY_UI_POLL_MS
        );
    }

    tf_recovery_transaction_progress_phase(
        "REVALIDATING TARGET"
    );

    /*
     * Re-resolve the active slot again after the host rendezvous.
     * The writable target still does not exist if this check fails.
     */
    active_slot = tf_resolve_active_slot();

    if (
        (
            active_slot != 'a'
            && active_slot != 'b'
        )
        || active_slot
            == set->target_slot
    ) {
        tf_close(source);

        image->install_error_stage = 9;

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            0
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    /*
     * Rebuild physical, LP, and unified target topology again after
     * the host rendezvous and before creating any writable block node.
     *
     * This closes the authorization-to-write topology window. The
     * block device identity used below comes only from this second
     * live resolution.
     */
    if (
        !tf_collect_inventory(
            &tf_recovery_inventory
        )
    ) {
        tf_close(source);

        image->install_error_stage = 23;

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            0
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    if (
        !target
        || target->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        || target->flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || target->slot
            != set->target_slot
        || target->active
        || !target->selectable
        || !tf_string_equal(
            target->canonical_name,
            image->canonical_name
        )
        || !tf_string_equal(
            target->partition_name,
            image->target_partition_name
        )
        || image->source_bytes
            > target->capacity_bytes
    ) {
        tf_close(source);

        image->install_error_stage = 24;

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            0
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    /*
     * Replace the pre-rendezvous encoded device identity with the
     * major/minor numbers from the second live topology resolution.
     */
    encoded_device = 0;

    if (
        !tf_encode_device_number(
            target->physical_major,
            target->physical_minor,
            &encoded_device
        )
    ) {
        tf_close(source);

        image->install_error_stage = 25;

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            0
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        S_IFBLK | 0600,
        (long) encoded_device
    );

    if (node_result < 0) {
        tf_close(source);

        image->install_error_stage = 10;
        image->install_error_errno = (
            (u64) (-node_result)
        );

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    long destination = tf_open(
        TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        O_WRONLY
    );

    if (destination < 0) {
        tf_close(source);

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_FLASH_NODE_PATH,
            0
        );

        image->install_error_stage = 11;
        image->install_error_errno = (
            (u64) (-destination)
        );

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    tf_recovery_transaction_progress_reset_bytes(
        "FLASHING",
        image->source_bytes
    );

    struct tf_sha256_context streamed_context;

    tf_sha256_init(
        &streamed_context
    );

    unsigned char buffer[4096];

    u64 remaining = (
        image->source_bytes
        - 1
    );

    int write_failed = 0;

    /*
     * The first byte was consumed solely to establish the host
     * rendezvous before creating the writable partition descriptor.
     * It is still part of the exact authenticated image stream.
     */
    tf_sha256_update(
        &streamed_context,
        &first_stream_byte,
        1
    );

    long first_write = tf_syscall3(
        SYS_WRITE,
        destination,
        (long) &first_stream_byte,
        1
    );

    if (first_write != 1) {
        image->install_error_stage = (
            first_write < 0
            ? 14
            : 15
        );

        if (first_write < 0) {
            image->install_error_errno = (
                (u64) (-first_write)
            );
        }

        write_failed = 1;
    } else {
        image->install_bytes_written = 1;

        tf_recovery_transaction_progress_bytes(
            image->install_bytes_written
        );
    }

    while (
        remaining > 0
        && !write_failed
    ) {
        usize requested = (
            remaining
                < (u64) sizeof(buffer)
            ? (usize) remaining
            : sizeof(buffer)
        );

        long amount = tf_syscall3(
            SYS_READ,
            source,
            (long) buffer,
            (long) requested
        );

        if (amount == -11) {
            tf_recovery_adbd_maintain();

            tf_recovery_ui_sleep_ms(
                TREEFORGE_RECOVERY_UI_POLL_MS
            );

            continue;
        }

        if (amount < 0) {
            image->install_error_stage = 12;
            image->install_error_errno = (
                (u64) (-amount)
            );
            write_failed = 1;
            break;
        }

        if (amount == 0) {
            image->install_error_stage = 13;
            write_failed = 1;
            break;
        }

        tf_sha256_update(
            &streamed_context,
            buffer,
            (usize) amount
        );

        usize written = 0;

        while (
            written
            < (usize) amount
        ) {
            long write_amount = tf_syscall3(
                SYS_WRITE,
                destination,
                (long) (
                    buffer
                    + written
                ),
                (long) (
                    (usize) amount
                    - written
                )
            );

            if (write_amount < 0) {
                image->install_error_stage = 14;
                image->install_error_errno = (
                    (u64) (-write_amount)
                );
                write_failed = 1;
                break;
            }

            if (write_amount == 0) {
                image->install_error_stage = 15;
                write_failed = 1;
                break;
            }

            written += (
                (usize) write_amount
            );

            image->install_bytes_written += (
                (u64) write_amount
            );

            tf_recovery_transaction_progress_bytes(
                image->install_bytes_written
            );
        }

        if (write_failed) {
            break;
        }

        remaining -= (
            (u64) amount
        );
    }

    /*
     * Exact stream framing.
     *
     * Because the source descriptor remains nonblocking, EAGAIN means
     * adb still owns the writer but has not closed it yet. Wait for
     * actual EOF; reject any additional byte.
     */
    if (!write_failed) {
        for (;;) {
            unsigned char extra = 0;

            long extra_amount = tf_syscall3(
                SYS_READ,
                source,
                (long) &extra,
                1
            );

            if (extra_amount == -11) {
                tf_recovery_adbd_maintain();

                tf_recovery_ui_sleep_ms(
                    TREEFORGE_RECOVERY_UI_POLL_MS
                );

                continue;
            }

            if (extra_amount < 0) {
                image->install_error_stage = 16;
                image->install_error_errno = (
                    (u64) (-extra_amount)
                );
                write_failed = 1;
            } else if (extra_amount != 0) {
                image->install_error_stage = 17;
                write_failed = 1;
            }

            break;
        }
    }

    if (!write_failed) {
        unsigned char digest[32];

        tf_sha256_final(
            &streamed_context,
            digest
        );

        tf_sha256_hex(
            digest,
            image->install_stream_sha256
        );

        if (
            image->install_bytes_written
                != image->source_bytes
            || !tf_string_equal(
                image->install_stream_sha256,
                image->sha256
            )
        ) {
            image->install_error_stage = 18;
            write_failed = 1;
        }
    }

    /*
     * Once a writable descriptor existed, always flush the resulting
     * inactive-slot state, including partial/failing writes.
     */
    tf_recovery_transaction_progress_phase(
        "SYNCING"
    );

    long fsync_result = tf_syscall1(
        SYS_FSYNC,
        destination
    );

    if (
        fsync_result != 0
        && !write_failed
    ) {
        image->install_error_stage = 19;
        image->install_error_errno = (
            (u64) (-fsync_result)
        );
        write_failed = 1;
    }

    tf_close(destination);
    tf_close(source);

    destination = -1;
    source = -1;

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (!write_failed) {
        tf_recovery_transaction_progress_reset_bytes(
            "READBACK VERIFY",
            image->source_bytes
        );

        long verify = tf_open(
            TREEFORGE_RECOVERY_FLASH_NODE_PATH,
            O_RDONLY
        );

        if (verify < 0) {
            image->install_error_stage = 20;
            image->install_error_errno = (
                (u64) (-verify)
            );
            write_failed = 1;
        } else {
            u64 verify_errno = 0;

            if (
                !tf_recovery_hash_fd_exact_progress(
                    verify,
                    image->source_bytes,
                    image->install_readback_sha256,
                    &verify_errno
                )
            ) {
                image->install_error_stage = 21;
                image->install_error_errno = (
                    verify_errno
                );
                write_failed = 1;
            }

            tf_close(verify);
        }
    }

    if (
        !write_failed
        && tf_string_equal(
            image->install_readback_sha256,
            image->sha256
        )
        && tf_string_equal(
            image->install_readback_sha256,
            image->install_stream_sha256
        )
    ) {
        image->install_readback_verified = 1;
        image->install_written = 1;
    } else if (
        !write_failed
    ) {
        image->install_error_stage = 22;
        write_failed = 1;
    }

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_FLASH_NODE_PATH,
        0
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        write_failed
        || !image->install_written
    ) {
        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    tf_recovery_transaction_progress_install_verified();

    return 1;
}


static int tf_recovery_write_install_set_logical_raw_image(
    long *inputs,
    struct tf_recovery_install_set_result *set,
    int image_index
) {
    if (
        !inputs
        || !set
        || image_index < 0
        || image_index >= set->image_count
    ) {
        return 0;
    }

    struct tf_recovery_install_set_image *image = (
        &set->images[image_index]
    );

    image->install_error_stage = 0;
    image->install_error_errno = 0;

    if (
        !set->install_transaction_started
        || set->install_transaction_complete
        || set->install_transaction_failed
        || image_index
            != set->install_written_count
        || image->install_write_attempted
        || image->install_written
        || !image->payload_verified
        || image->image_format
            != TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
        || image->target_type
            != TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        || image->target_flash_policy
            != TREEFORGE_RECOVERY_FLASH_POLICY_NORMAL
        || image->target_active
        || !image->target_selectable
        || !image->target_allocation_present
        || image->install_action
            != TREEFORGE_RECOVERY_INSTALL_ACTION_FITS
        || image->source_bytes == 0
        || image->expanded_bytes
            != image->source_bytes
        || !image->sha256[0]
    ) {
        image->install_error_stage = 40;
        return 0;
    }

    /*
     * Do not mark attempted until the complete non-destructive
     * per-image gate has passed.
     */
    const struct tf_recovery_flash_target *target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    const struct tf_recovery_logical_partition *partition = 0;

    if (
        !tf_recovery_logical_raw_target_ready(
            set,
            image,
            target,
            &tf_recovery_lp_inventory,
            &partition
        )
    ) {
        image->install_error_stage = 41;
        return 0;
    }

    image->install_write_attempted = 1;
    image->install_written = 0;
    image->install_readback_verified = 0;
    image->install_bytes_written = 0;
    image->install_stream_sha256[0] = '\0';
    image->install_readback_sha256[0] = '\0';

    char active_slot = (
        tf_resolve_active_slot()
    );

    if (
        active_slot != 'a'
        && active_slot != 'b'
    ) {
        image->install_error_stage = 42;
        return 0;
    }

    if (
        active_slot
        == set->target_slot
    ) {
        image->install_error_stage = 43;
        return 0;
    }

    /*
     * First destructive authorization pass.
     *
     * Rebuild physical + LP + unified topology before publishing
     * write-ready.
     */
    if (
        !tf_collect_inventory(
            &tf_recovery_inventory
        )
    ) {
        image->install_error_stage = 44;
        return 0;
    }

    target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    partition = 0;

    if (
        !tf_recovery_logical_raw_target_ready(
            set,
            image,
            target,
            &tf_recovery_lp_inventory,
            &partition
        )
    ) {
        image->install_error_stage = 45;
        return 0;
    }

    tf_recovery_transaction_progress_begin(
        set,
        image_index,
        "WAITING FOR HOST",
        1
    );

    if (
        !tf_recovery_install_set_transfer_state(
            set,
            "write-ready",
            image_index,
            0,
            0
        )
    ) {
        image->install_error_stage = 46;

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    /*
     * Same accepted pre-write cancellation contract as the physical
     * writer: FIFO is nonblocking and no writable super descriptor
     * exists yet.
     */
    long source = tf_open(
        TREEFORGE_RECOVERY_STREAM_FIFO_PATH,
        O_RDONLY
        | O_NONBLOCK
    );

    if (source < 0) {
        image->install_error_stage = 47;
        image->install_error_errno = (
            (u64) (-source)
        );

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    unsigned char first_stream_byte = 0;
    int first_stream_byte_ready = 0;

    while (!first_stream_byte_ready) {
        long amount = tf_syscall3(
            SYS_READ,
            source,
            (long) &first_stream_byte,
            1
        );

        if (amount == 1) {
            first_stream_byte_ready = 1;
            break;
        }

        if (
            amount < 0
            && amount != -11
        ) {
            tf_close(source);

            image->install_error_stage = 47;
            image->install_error_errno = (
                (u64) (-amount)
            );

            tf_recovery_install_set_transfer_state(
                set,
                "write-error",
                image_index,
                image->install_error_stage,
                image->install_error_errno
            );

            tf_recovery_transaction_progress_phase(
                "FAILED"
            );

            return 0;
        }

        int key = (
            tf_recovery_ui_poll_key_once(
                inputs
            )
        );

        if (
            key == KEY_POWER
            && image_index == 0
            && set->install_written_count == 0
        ) {
            tf_close(source);

            image->install_write_attempted = 0;
            image->install_error_stage = 0;
            image->install_error_errno = 0;

            tf_recovery_install_set_transfer_state(
                set,
                "write-cancelled",
                image_index,
                0,
                0
            );

            tf_recovery_transaction_progress_phase(
                "CANCELLED"
            );

            return -1;
        }

        tf_recovery_adbd_maintain();

        tf_recovery_ui_sleep_ms(
            TREEFORGE_RECOVERY_UI_POLL_MS
        );
    }

    tf_recovery_transaction_progress_phase(
        "REVALIDATING TARGET"
    );

    /*
     * A host byte commits the transaction but still does not authorize
     * a super write. Re-resolve slot + complete LP topology again.
     */
    active_slot = tf_resolve_active_slot();

    if (
        (
            active_slot != 'a'
            && active_slot != 'b'
        )
        || active_slot
            == set->target_slot
    ) {
        tf_close(source);

        image->install_error_stage = 48;

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            0
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    if (
        !tf_collect_inventory(
            &tf_recovery_inventory
        )
    ) {
        tf_close(source);

        image->install_error_stage = 49;

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            0
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    target = (
        tf_recovery_find_unified_flash_target(
            image->target_partition_name
        )
    );

    partition = 0;

    if (
        !tf_recovery_logical_raw_target_ready(
            set,
            image,
            target,
            &tf_recovery_lp_inventory,
            &partition
        )
    ) {
        tf_close(source);

        image->install_error_stage = 50;

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            0
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    u64 encoded_device = 0;

    if (
        !tf_encode_device_number(
            tf_recovery_lp_inventory.super_major,
            tf_recovery_lp_inventory.super_minor,
            &encoded_device
        )
    ) {
        tf_close(source);

        image->install_error_stage = 51;
        return 0;
    }

    /*
     * Only now may a writable super descriptor exist.
     */
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    long node_result = tf_syscall4(
        SYS_MKNODAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        S_IFBLK | 0600,
        (long) encoded_device
    );

    if (node_result < 0) {
        tf_close(source);

        image->install_error_stage = 52;
        image->install_error_errno = (
            (u64) (-node_result)
        );

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    long destination = tf_open(
        TREEFORGE_RECOVERY_LP_NODE_PATH,
        O_WRONLY
    );

    if (destination < 0) {
        tf_close(source);

        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            0
        );

        image->install_error_stage = 53;
        image->install_error_errno = (
            (u64) (-destination)
        );

        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    tf_recovery_transaction_progress_reset_bytes(
        "FLASHING",
        image->source_bytes
    );

    struct tf_sha256_context streamed_context;

    tf_sha256_init(
        &streamed_context
    );

    unsigned char buffer[4096];

    u64 source_remaining = (
        image->source_bytes
    );

    int first_byte_pending = 1;
    int write_failed = 0;

    for (
        u32 local_extent = 0;
        local_extent < partition->num_extents
            && !write_failed;
        local_extent++
    ) {
        int extent_matches = 0;

        const struct tf_recovery_logical_extent *extent = (
            tf_lp_find_partition_extent(
                &tf_recovery_lp_inventory,
                partition,
                local_extent,
                &extent_matches
            )
        );

        u64 extent_offset = 0;
        u64 extent_length = 0;

        if (
            extent_matches != 1
            || !extent
            || !tf_recovery_lp_linear_extent_bounds(
                &tf_recovery_lp_inventory,
                extent,
                &extent_offset,
                &extent_length
            )
        ) {
            image->install_error_stage = 54;
            write_failed = 1;
            break;
        }

        long seek_result = tf_syscall3(
            SYS_LSEEK,
            destination,
            (long) extent_offset,
            SEEK_SET
        );

        if (
            seek_result < 0
            || (u64) seek_result
                != extent_offset
        ) {
            image->install_error_stage = 55;

            if (seek_result < 0) {
                image->install_error_errno = (
                    (u64) (-seek_result)
                );
            }

            write_failed = 1;
            break;
        }

        u64 extent_remaining = (
            extent_length
        );

        if (first_byte_pending) {
            tf_sha256_update(
                &streamed_context,
                &first_stream_byte,
                1
            );

            long first_write = tf_syscall3(
                SYS_WRITE,
                destination,
                (long) &first_stream_byte,
                1
            );

            if (first_write != 1) {
                image->install_error_stage = 56;

                if (first_write < 0) {
                    image->install_error_errno = (
                        (u64) (-first_write)
                    );
                }

                write_failed = 1;
                break;
            }

            image->install_bytes_written++;
            source_remaining--;
            extent_remaining--;
            first_byte_pending = 0;

            tf_recovery_transaction_progress_bytes(
                image->install_bytes_written
            );
        }

        while (
            extent_remaining > 0
            && !write_failed
        ) {
            usize requested = (
                extent_remaining
                    < (u64) sizeof(buffer)
                ? (usize) extent_remaining
                : sizeof(buffer)
            );

            long amount = tf_syscall3(
                SYS_READ,
                source,
                (long) buffer,
                (long) requested
            );

            if (amount == -11) {
                tf_recovery_adbd_maintain();

                tf_recovery_ui_sleep_ms(
                    TREEFORGE_RECOVERY_UI_POLL_MS
                );

                continue;
            }

            if (amount < 0) {
                image->install_error_stage = 57;
                image->install_error_errno = (
                    (u64) (-amount)
                );
                write_failed = 1;
                break;
            }

            if (amount == 0) {
                image->install_error_stage = 58;
                write_failed = 1;
                break;
            }

            if (
                (u64) amount
                    > extent_remaining
                || (u64) amount
                    > source_remaining
            ) {
                image->install_error_stage = 59;
                write_failed = 1;
                break;
            }

            tf_sha256_update(
                &streamed_context,
                buffer,
                (usize) amount
            );

            usize written = 0;

            while (
                written
                < (usize) amount
            ) {
                long write_amount = tf_syscall3(
                    SYS_WRITE,
                    destination,
                    (long) (
                        buffer
                        + written
                    ),
                    (long) (
                        (usize) amount
                        - written
                    )
                );

                if (write_amount < 0) {
                    image->install_error_stage = 60;
                    image->install_error_errno = (
                        (u64) (-write_amount)
                    );
                    write_failed = 1;
                    break;
                }

                if (write_amount == 0) {
                    image->install_error_stage = 61;
                    write_failed = 1;
                    break;
                }

                written += (
                    (usize) write_amount
                );

                image->install_bytes_written += (
                    (u64) write_amount
                );

                tf_recovery_transaction_progress_bytes(
                    image->install_bytes_written
                );
            }

            if (write_failed) {
                break;
            }

            source_remaining -= (
                (u64) amount
            );

            extent_remaining -= (
                (u64) amount
            );
        }
    }

    if (
        !write_failed
        && (
            first_byte_pending
            || source_remaining != 0
            || image->install_bytes_written
                != image->source_bytes
        )
    ) {
        image->install_error_stage = 62;
        write_failed = 1;
    }

    /*
     * Exact FIFO framing. Wait through EAGAIN until the host closes.
     */
    if (!write_failed) {
        for (;;) {
            unsigned char extra = 0;

            long extra_amount = tf_syscall3(
                SYS_READ,
                source,
                (long) &extra,
                1
            );

            if (extra_amount == -11) {
                tf_recovery_adbd_maintain();

                tf_recovery_ui_sleep_ms(
                    TREEFORGE_RECOVERY_UI_POLL_MS
                );

                continue;
            }

            if (extra_amount < 0) {
                image->install_error_stage = 63;
                image->install_error_errno = (
                    (u64) (-extra_amount)
                );
                write_failed = 1;
            } else if (extra_amount != 0) {
                image->install_error_stage = 64;
                write_failed = 1;
            }

            break;
        }
    }

    if (!write_failed) {
        unsigned char digest[32];

        tf_sha256_final(
            &streamed_context,
            digest
        );

        tf_sha256_hex(
            digest,
            image->install_stream_sha256
        );

        if (
            !tf_string_equal(
                image->install_stream_sha256,
                image->sha256
            )
        ) {
            image->install_error_stage = 65;
            write_failed = 1;
        }
    }

    /*
     * Once super was writable, flush even a failed partial write.
     */
    tf_recovery_transaction_progress_phase(
        "SYNCING"
    );

    long fsync_result = tf_syscall1(
        SYS_FSYNC,
        destination
    );

    if (
        fsync_result != 0
        && !write_failed
    ) {
        image->install_error_stage = 66;
        image->install_error_errno = (
            (u64) (-fsync_result)
        );
        write_failed = 1;
    }

    tf_close(destination);
    tf_close(source);

    destination = -1;
    source = -1;

    tf_syscall1(
        SYS_SYNC,
        0
    );

    long cleanup_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    if (
        cleanup_result < 0
        && cleanup_result != -2
        && !write_failed
    ) {
        image->install_error_stage = 67;
        image->install_error_errno = (
            (u64) (-cleanup_result)
        );
        write_failed = 1;
    }

    /*
     * Independent readback starts from freshly parsed authoritative
     * LP metadata. Metadata itself was never modified.
     */
    if (!write_failed) {
        if (
            !tf_collect_inventory(
                &tf_recovery_inventory
            )
        ) {
            image->install_error_stage = 68;
            write_failed = 1;
        }
    }

    if (!write_failed) {
        target = (
            tf_recovery_find_unified_flash_target(
                image->target_partition_name
            )
        );

        partition = 0;

        if (
            !tf_recovery_logical_raw_target_ready(
                set,
                image,
                target,
                &tf_recovery_lp_inventory,
                &partition
            )
        ) {
            image->install_error_stage = 69;
            write_failed = 1;
        }
    }

    if (!write_failed) {
        encoded_device = 0;

        if (
            !tf_encode_device_number(
                tf_recovery_lp_inventory.super_major,
                tf_recovery_lp_inventory.super_minor,
                &encoded_device
            )
        ) {
            image->install_error_stage = 70;
            write_failed = 1;
        }
    }

    if (!write_failed) {
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            0
        );

        node_result = tf_syscall4(
            SYS_MKNODAT,
            AT_FDCWD,
            (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
            S_IFBLK | 0400,
            (long) encoded_device
        );

        if (node_result < 0) {
            image->install_error_stage = 71;
            image->install_error_errno = (
                (u64) (-node_result)
            );
            write_failed = 1;
        }
    }

    if (!write_failed) {
        tf_recovery_transaction_progress_reset_bytes(
            "READBACK VERIFY",
            image->source_bytes
        );

        long verify = tf_open(
            TREEFORGE_RECOVERY_LP_NODE_PATH,
            O_RDONLY
        );

        if (verify < 0) {
            image->install_error_stage = 72;
            image->install_error_errno = (
                (u64) (-verify)
            );
            write_failed = 1;
        } else {
            u64 verify_errno = 0;

            if (
                !tf_recovery_hash_logical_raw_exact_progress(
                    verify,
                    &tf_recovery_lp_inventory,
                    partition,
                    image->source_bytes,
                    image->install_readback_sha256,
                    &verify_errno
                )
            ) {
                image->install_error_stage = 73;
                image->install_error_errno = (
                    verify_errno
                );
                write_failed = 1;
            }

            tf_close(verify);
        }
    }

    cleanup_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_LP_NODE_PATH,
        0
    );

    if (
        cleanup_result < 0
        && cleanup_result != -2
        && !write_failed
    ) {
        image->install_error_stage = 74;
        image->install_error_errno = (
            (u64) (-cleanup_result)
        );
        write_failed = 1;
    }

    if (
        !write_failed
        && tf_string_equal(
            image->install_readback_sha256,
            image->sha256
        )
        && tf_string_equal(
            image->install_readback_sha256,
            image->install_stream_sha256
        )
    ) {
        image->install_readback_verified = 1;
        image->install_written = 1;
    }

    if (
        write_failed
        || !image->install_written
    ) {
        tf_recovery_install_set_transfer_state(
            set,
            "write-error",
            image_index,
            image->install_error_stage,
            image->install_error_errno
        );

        tf_recovery_transaction_progress_phase(
            "FAILED"
        );

        return 0;
    }

    /*
     * The writer owns data integrity only.
     *
     * Per-image protocol completion remains owned by the transaction
     * coordinator, exactly as it is for the hardware-accepted physical
     * RAW writer. The coordinator increments install_written_count and
     * publishes state=write-verified before authorizing the next image.
     */
    tf_recovery_transaction_progress_install_verified();

    return 1;
}


static int tf_recovery_install_existing_allocation_set(
    long *inputs,
    struct tf_recovery_install_set_result *set
) {
    /*
     * Whole-set destructive preflight uses one fresh physical + LP +
     * unified topology snapshot before image zero can begin.
     */
    if (
        !tf_collect_inventory(
            &tf_recovery_inventory
        )
        || !tf_recovery_install_set_existing_allocation_transaction_ready(
            set
        )
    ) {
        return 0;
    }

    tf_recovery_install_set_begin_transfer_generation();

    set->install_transaction_started = 1;
    set->install_transaction_complete = 0;
    set->install_transaction_failed = 0;
    set->install_written_count = 0;
    set->install_error_image_index = -1;

    for (
        int index = 0;
        index < set->image_count;
        index++
    ) {
        int write_result = 0;

        if (
            set->images[index].target_type
            == TREEFORGE_RECOVERY_FLASH_TARGET_PHYSICAL
        ) {
            write_result = (
                tf_recovery_write_install_set_physical_raw_image(
                    inputs,
                    set,
                    index
                )
            );
        } else if (
            set->images[index].target_type
            == TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
        ) {
            if (
                set->images[index].image_format
                == TREEFORGE_RECOVERY_IMAGE_FORMAT_RAW
            ) {
                write_result = (
                    tf_recovery_write_install_set_logical_raw_image(
                        inputs,
                        set,
                        index
                    )
                );
            } else if (
                set->images[index].image_format
                == TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
            ) {
                write_result = (
                    tf_recovery_write_install_set_logical_sparse_image(
                        inputs,
                        set,
                        index
                    )
                );
            } else {
                set->images[index].install_error_stage = 163;
                write_result = 0;
            }
        } else {
            set->images[index].install_error_stage = 75;
            write_result = 0;
        }

        if (write_result < 0) {
            /*
             * Cancellation is valid only before image zero commits.
             * Treat any impossible later cancellation as a transaction
             * failure rather than clearing destructive state.
             */
            if (
                index != 0
                || set->install_written_count != 0
            ) {
                set->install_transaction_failed = 1;
                set->install_error_image_index = index;

                tf_recovery_install_set_transfer_state(
                    set,
                    "write-error",
                    index,
                    26,
                    0
                );

                return 0;
            }

            set->install_transaction_started = 0;
            set->install_transaction_complete = 0;
            set->install_transaction_failed = 0;
            set->install_error_image_index = -1;

            return -1;
        }

        if (!write_result) {
            set->install_transaction_failed = 1;
            set->install_error_image_index = index;

            /*
             * Cover failures that occur before the writer has reached
             * its normal write-ready/write-error protocol states.
             */
            tf_recovery_install_set_transfer_state(
                set,
                "write-error",
                index,
                set->images[index].install_error_stage,
                set->images[index].install_error_errno
            );

            return 0;
        }

        set->install_written_count++;

        /*
         * Publish per-image completion before authorizing the next
         * stream. The host never independently chooses the next image.
         */
        if (
            !tf_recovery_install_set_transfer_state(
                set,
                "write-verified",
                index,
                0,
                0
            )
        ) {
            set->install_transaction_failed = 1;
            set->install_error_image_index = index;

            return 0;
        }
    }

    set->install_transaction_complete = 1;

    tf_recovery_install_set_transfer_state(
        set,
        "transaction-complete",
        -1,
        0,
        0
    );

    return 1;
}


static const char *tf_recovery_install_transaction_status_name(
    const struct tf_recovery_install_set_result *set
) {
    if (!set) {
        return "UNKNOWN";
    }

    if (
        set->wire_version
        == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
    ) {
        return "READ ONLY";
    }

    if (set->install_transaction_complete) {
        return "INSTALLED";
    }

    if (set->install_transaction_failed) {
        return "FAILED";
    }

    if (set->install_transaction_started) {
        return "INSTALLING";
    }

    if (
        set->payload_verification_complete
        && set->payload_verified_count
            == set->image_count
    ) {
        return "VERIFIED";
    }

    return "READY";
}


static void tf_recovery_ui_show_physical_raw_set_result(
    long *inputs,
    const struct tf_recovery_install_set_result *set
) {
    char installed_line[80];
    char failed_line[80];

    usize position = tf_append_text(
        installed_line,
        sizeof(installed_line),
        0,
        "INSTALLED                "
    );

    position = tf_append_u64(
        installed_line,
        sizeof(installed_line),
        position,
        (u64) set->install_written_count
    );

    position = tf_append_text(
        installed_line,
        sizeof(installed_line),
        position,
        " / "
    );

    tf_append_u64(
        installed_line,
        sizeof(installed_line),
        position,
        (u64) set->image_count
    );

    position = tf_append_text(
        failed_line,
        sizeof(failed_line),
        0,
        "FAILED IMAGE INDEX       "
    );

    if (
        set->install_error_image_index >= 0
    ) {
        tf_append_u64(
            failed_line,
            sizeof(failed_line),
            position,
            (u64) set->install_error_image_index
        );
    } else {
        tf_append_text(
            failed_line,
            sizeof(failed_line),
            position,
            "-"
        );
    }

    const char *lines[] = {
        (
            set->install_transaction_complete
            ? "TRANSACTION              VERIFIED"
            : (
                set->install_transaction_failed
                ? "TRANSACTION              FAILED"
                : "TRANSACTION              NOT STARTED"
            )
        ),
        installed_line,
        (
            set->install_transaction_complete
            ? "STREAM IDENTITIES        MATCHED"
            : "STREAM IDENTITIES        INCOMPLETE"
        ),
        (
            set->install_transaction_complete
            ? "READBACKS                MATCHED"
            : "READBACKS                INCOMPLETE"
        ),
        failed_line,
        "",
        "SLOT ACTIVATION          DISABLED",
        "NO LOGICAL PARTITIONS WRITTEN",
    };

    tf_recovery_ui_draw_info(
        "INSTALL SET RESULT",
        lines,
        8,
        "POWER: BACK"
    );

    while (
        tf_recovery_ui_wait_key(
            inputs
        )
        != KEY_POWER
    ) {
    }
}


static int tf_recovery_ui_confirm_physical_raw_set(
    long *inputs,
    const struct tf_recovery_install_set_result *set
) {
    char subtitle[96];

    usize position = tf_append_text(
        subtitle,
        sizeof(subtitle),
        0,
        "TARGET SLOT "
    );

    char slot[2];

    slot[0] = (
        set->target_slot == 'a'
        ? 'A'
        : 'B'
    );
    slot[1] = '\0';

    position = tf_append_text(
        subtitle,
        sizeof(subtitle),
        position,
        slot
    );

    position = tf_append_text(
        subtitle,
        sizeof(subtitle),
        position,
        " - "
    );

    position = tf_append_u64(
        subtitle,
        sizeof(subtitle),
        position,
        (u64) set->image_count
    );

    tf_append_text(
        subtitle,
        sizeof(subtitle),
        position,
        " IMAGES - DESTRUCTIVE"
    );

    static const char *items[] = {
        "YES - INSTALL SET",
        "NO - GO BACK",
    };

    int selected = 1;

    for (;;) {
        tf_recovery_ui_draw_menu(
            "INSTALL STAGED SET?",
            subtitle,
            items,
            2,
            selected
        );

        int key = tf_recovery_ui_wait_key(
            inputs
        );

        if (
            key == KEY_VOLUMEUP
            || key == KEY_VOLUMEDOWN
        ) {
            selected = (
                selected
                + 1
            ) % 2;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        return (
            selected == 0
        );
    }
}


static void tf_recovery_ui_physical_raw_install_set(
    long *inputs,
    struct tf_recovery_install_set_result *set
) {
    /*
     * Once any destructive transaction has started, never silently
     * restart it. Re-entering this action becomes status-only.
     */
    if (set->install_transaction_started) {
        tf_recovery_ui_show_physical_raw_set_result(
            inputs,
            set
        );

        return;
    }

    if (
        !tf_recovery_install_set_existing_allocation_transaction_ready(
            set
        )
    ) {
        const char *lines[] = {
            "CURRENT WRITER           PHYSICAL RAW",
            "WHOLE SET REQUIRED       YES",
            "PAYLOADS VERIFIED        REQUIRED",
            "LOGICAL TARGETS          NOT SUPPORTED",
            "SPARSE WRITES            NOT SUPPORTED",
            "",
            "NO PARTITION WAS WRITTEN",
            "SLOT ACTIVATION          DISABLED",
        };

        tf_recovery_ui_draw_info(
            "INSTALL SET UNAVAILABLE",
            lines,
            8,
            "POWER: BACK"
        );

        while (
            tf_recovery_ui_wait_key(
                inputs
            )
            != KEY_POWER
        ) {
        }

        return;
    }

    char target_line[80];
    char images_line[80];
    char command_display[64];

    usize position = tf_append_text(
        target_line,
        sizeof(target_line),
        0,
        "TARGET SLOT              "
    );

    char slot[2];

    slot[0] = (
        set->target_slot == 'a'
        ? 'A'
        : 'B'
    );
    slot[1] = '\0';

    tf_append_text(
        target_line,
        sizeof(target_line),
        position,
        slot
    );

    position = tf_append_text(
        images_line,
        sizeof(images_line),
        0,
        "IMAGES                   "
    );

    tf_append_u64(
        images_line,
        sizeof(images_line),
        position,
        (u64) set->image_count
    );

    tf_recovery_ui_display_text(
        "treeforge recovery install",
        command_display,
        sizeof(command_display)
    );

    const char *lines[] = {
        target_line,
        images_line,
        "WRITER                   PHYSICAL RAW",
        "VERIFY                   STREAM + READBACK",
        "",
        "RUN ON HOST:",
        command_display,
        "SLOT ACTIVATION          DISABLED",
    };

    tf_recovery_ui_draw_info(
        "INSTALL STAGED SET",
        lines,
        8,
        "POWER: CONTINUE"
    );

    while (
        tf_recovery_ui_wait_key(
            inputs
        )
        != KEY_POWER
    ) {
    }

    if (
        !tf_recovery_ui_confirm_physical_raw_set(
            inputs,
            set
        )
    ) {
        return;
    }

    tf_recovery_transaction_progress_clear();

    int result = (
        tf_recovery_install_existing_allocation_set(
            inputs,
            set
        )
    );

    tf_recovery_transaction_progress_clear();

    if (result < 0) {
        /*
         * Cancellable WAITING FOR HOST ended before any partition write.
         */
        return;
    }

    if (
        !result
        && !set->install_transaction_failed
    ) {
        set->install_transaction_failed = 1;
    }

    tf_recovery_ui_show_physical_raw_set_result(
        inputs,
        set
    );
}


static int tf_recovery_ui_confirm_payload_verification(
    long *inputs,
    const struct tf_recovery_install_set_result *set
) {
    if (
        !set
        || !set->plan_resolved
    ) {
        return 0;
    }

    static const char *items[] = {
        "YES - VERIFY PAYLOADS",
        "NO - GO BACK",
    };

    int selected = 1;

    for (;;) {
        tf_recovery_ui_draw_menu(
            "VERIFY STAGED PAYLOADS?",
            "NO PARTITIONS WILL BE WRITTEN",
            items,
            2,
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (
            key == KEY_VOLUMEUP
            || key == KEY_VOLUMEDOWN
        ) {
            selected = (
                selected
                + 1
            ) % 2;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        return (
            selected == 0
        );
    }
}


static void tf_recovery_ui_show_payload_verification_result(
    long *inputs,
    const struct tf_recovery_install_set_result *set,
    int success
) {
    char verified[64];

    usize position = tf_append_text(
        verified,
        sizeof(verified),
        0,
        "VERIFIED                 "
    );

    position = tf_append_u64(
        verified,
        sizeof(verified),
        position,
        (u64) set->payload_verified_count
    );

    position = tf_append_text(
        verified,
        sizeof(verified),
        position,
        " / "
    );

    tf_append_u64(
        verified,
        sizeof(verified),
        position,
        (u64) set->image_count
    );

    char stage[64];

    position = tf_append_text(
        stage,
        sizeof(stage),
        0,
        "ERROR STAGE              "
    );

    tf_append_u64(
        stage,
        sizeof(stage),
        position,
        (u64) set->payload_error_stage
    );

    const char *lines[] = {
        (
            success
            ? "PAYLOAD STATUS           VERIFIED"
            : "PAYLOAD STATUS           FAILED"
        ),
        verified,
        (
            set->wire_version
                == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
            ? (
                success
                ? "TRANSPORT IDENTITY       MATCHED"
                : "TRANSPORT IDENTITY       NOT ACCEPTED"
            )
            : (
                success
                ? "SOURCE IDENTITY          MATCHED"
                : "SOURCE IDENTITY          NOT ACCEPTED"
            )
        ),
        (
            set->wire_version
                == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
            ? (
                success
                ? "TRANSPORT FRAMING        EXACT"
                : "TRANSPORT FRAMING        FAILED"
            )
            : (
                success
                ? "IMAGE STRUCTURE          VALID"
                : "IMAGE STRUCTURE          FAILED / UNKNOWN"
            )
        ),
        stage,
        "",
        "FLASHING                 DISABLED",
        "NO PARTITIONS WERE WRITTEN",
    };

    tf_recovery_ui_draw_info(
        "PAYLOAD VERIFICATION",
        lines,
        8,
        "POWER: BACK"
    );

    for (;;) {
        if (
            tf_recovery_ui_wait_key(
                inputs
            )
            == KEY_POWER
        ) {
            return;
        }
    }
}


static void tf_recovery_ui_verify_install_set_payloads(
    long *inputs,
    struct tf_recovery_install_set_result *set
) {
    if (
        !tf_recovery_ui_confirm_payload_verification(
            inputs,
            set
        )
    ) {
        return;
    }

    tf_recovery_transaction_progress_clear();

    int result = (
        tf_recovery_verify_install_set_payloads(
            inputs,
            set
        )
    );

    tf_recovery_transaction_progress_clear();

    if (result < 0) {
        return;
    }

    tf_recovery_ui_show_payload_verification_result(
        inputs,
        set,
        result
    );
}


static void tf_recovery_ui_install_set_review(
    long *inputs,
    const struct tf_recovery_install_set_result *set
) {
    if (
        !set
        || !set->plan_resolved
    ) {
        return;
    }

    const int rows_per_page = 6;
    int page = 0;

    int page_count = (
        set->image_count
        + rows_per_page
        - 1
    ) / rows_per_page;

    if (page_count < 1) {
        page_count = 1;
    }

    for (;;) {
        char buffers[8][128];
        const char *lines[8];

        for (
            int index = 0;
            index < 8;
            index++
        ) {
            buffers[index][0] = '\0';
            lines[index] = buffers[index];
        }

        tf_copy_string(
            buffers[0],
            sizeof(buffers[0]),
            (
                set->wire_version
                    == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
                ? "PARTITION         TYPE      PAYLOAD    ACTION"
                : "PARTITION         TYPE      FORMAT     ACTION"
            )
        );

        int first = (
            page
            * rows_per_page
        );

        int rows = 0;

        for (
            int offset = 0;
            offset < rows_per_page;
            offset++
        ) {
            int index = (
                first
                + offset
            );

            if (index >= set->image_count) {
                break;
            }

            const struct tf_recovery_install_set_image *image = (
                &set->images[index]
            );

            char display[
                TREEFORGE_RECOVERY_PARTITION_NAME_CAPACITY
            ];

            tf_recovery_ui_display_text(
                image->canonical_name,
                display,
                sizeof(display)
            );

            usize position = 0;

            position = tf_recovery_ui_append_padded(
                buffers[offset + 1],
                sizeof(buffers[offset + 1]),
                position,
                display,
                18
            );

            position = tf_recovery_ui_append_padded(
                buffers[offset + 1],
                sizeof(buffers[offset + 1]),
                position,
                (
                    image->target_type
                        == TREEFORGE_RECOVERY_FLASH_TARGET_LOGICAL
                    ? "LOGICAL"
                    : "PHYSICAL"
                ),
                10
            );

            position = tf_recovery_ui_append_padded(
                buffers[offset + 1],
                sizeof(buffers[offset + 1]),
                position,
                (
                    set->wire_version
                        == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
                    ? (
                        image->manifest_payload_kind
                            == TREEFORGE_RECOVERY_PAYLOAD_KIND_COW
                        ? "COW"
                        : "IMAGE"
                    )
                    : (
                        image->image_format
                            == TREEFORGE_RECOVERY_IMAGE_FORMAT_ANDROID_SPARSE
                        ? "SPARSE"
                        : "RAW"
                    )
                ),
                11
            );

            tf_append_text(
                buffers[offset + 1],
                sizeof(buffers[offset + 1]),
                position,
                tf_recovery_install_action_name(
                    image->install_action
                )
            );

            rows++;
        }

        tf_recovery_ui_page_line(
            page,
            page_count,
            buffers[7],
            sizeof(buffers[7])
        );

        tf_recovery_ui_draw_info(
            "INSTALL SET REVIEW",
            lines,
            8,
            "VOL +/-: PAGE   POWER: BACK"
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_POWER) {
            return;
        }

        if (key == KEY_VOLUMEUP) {
            page = (
                page
                + page_count
                - 1
            ) % page_count;
        }

        if (key == KEY_VOLUMEDOWN) {
            page = (
                page
                + 1
            ) % page_count;
        }
    }
}


static void tf_recovery_ui_install_set_summary(
    long *inputs,
    struct tf_recovery_install_set_result *set
) {
    if (
        !set
        || !set->plan_resolved
    ) {
        return;
    }

    for (;;) {
        char target_slot[64];
        char active_slot[64];
        char images[64];
        char physical[64];
        char logical[64];
        char formats[96];
        char changes[96];
        char wire[64];
        char snapshots[64];

        target_slot[0] = '\0';

        usize position = tf_append_text(
            target_slot,
            sizeof(target_slot),
            0,
            "TARGET SLOT              "
        );

        char target_value[2];

        target_value[0] = (
            set->target_slot == 'a'
            ? 'A'
            : 'B'
        );

        target_value[1] = '\0';

        tf_append_text(
            target_slot,
            sizeof(target_slot),
            position,
            target_value
        );

        active_slot[0] = '\0';

        position = tf_append_text(
            active_slot,
            sizeof(active_slot),
            0,
            "ACTIVE SLOT              "
        );

        char active_value[2];

        active_value[0] = (
            set->active_slot == 'a'
            ? 'A'
            : 'B'
        );

        active_value[1] = '\0';

        tf_append_text(
            active_slot,
            sizeof(active_slot),
            position,
            active_value
        );

        images[0] = '\0';

        position = tf_append_text(
            images,
            sizeof(images),
            0,
            "IMAGES                   "
        );

        tf_append_u64(
            images,
            sizeof(images),
            position,
            (u64) set->image_count
        );

        physical[0] = '\0';

        position = tf_append_text(
            physical,
            sizeof(physical),
            0,
            "PHYSICAL                 "
        );

        tf_append_u64(
            physical,
            sizeof(physical),
            position,
            (u64) set->physical_count
        );

        logical[0] = '\0';

        position = tf_append_text(
            logical,
            sizeof(logical),
            0,
            "LOGICAL                  "
        );

        tf_append_u64(
            logical,
            sizeof(logical),
            position,
            (u64) set->logical_count
        );

        formats[0] = '\0';

        position = tf_append_text(
            formats,
            sizeof(formats),
            0,
            "RAW / SPARSE             "
        );

        position = tf_append_u64(
            formats,
            sizeof(formats),
            position,
            (u64) set->raw_count
        );

        position = tf_append_text(
            formats,
            sizeof(formats),
            position,
            " / "
        );

        tf_append_u64(
            formats,
            sizeof(formats),
            position,
            (u64) set->sparse_count
        );

        changes[0] = '\0';

        position = tf_append_text(
            changes,
            sizeof(changes),
            0,
            "ALLOCATE / RESIZE        "
        );

        position = tf_append_u64(
            changes,
            sizeof(changes),
            position,
            (u64) set->allocation_count
        );

        position = tf_append_text(
            changes,
            sizeof(changes),
            position,
            " / "
        );

        tf_append_u64(
            changes,
            sizeof(changes),
            position,
            (u64) set->resize_count
        );

        tf_copy_string(
            wire,
            sizeof(wire),
            (
                set->wire_version
                    == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
                ? "WIRE                     V2"
                : "WIRE                     V1"
            )
        );

        snapshots[0] = '\0';

        position = tf_append_text(
            snapshots,
            sizeof(snapshots),
            0,
            "SNAPSHOT COW             "
        );

        tf_append_u64(
            snapshots,
            sizeof(snapshots),
            position,
            (u64) set->snapshot_cow_count
        );

        const char *lines[8];

        if (
            set->wire_version
            == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
        ) {
            lines[0] = target_slot;
            lines[1] = active_slot;
            lines[2] = wire;
            lines[3] = images;
            lines[4] = physical;
            lines[5] = logical;
            lines[6] = snapshots;
            lines[7] = "PLAN STATUS              READ ONLY";
        } else {
            lines[0] = target_slot;
            lines[1] = active_slot;
            lines[2] = images;
            lines[3] = physical;
            lines[4] = logical;
            lines[5] = formats;
            lines[6] = changes;
            lines[7] = "PLAN STATUS              READY";
        }

        tf_recovery_ui_draw_info(
            "STAGED INSTALL SET",
            lines,
            8,
            "VOL DOWN: IMAGE REVIEW   POWER: BACK"
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_POWER) {
            return;
        }

        if (key == KEY_VOLUMEDOWN) {
            tf_recovery_ui_install_set_review(
                inputs,
                set
            );
        }
    }
}


static void tf_recovery_ui_show_receive_ready(
    long *inputs
) {
    for (;;) {
        char active_slot[64];

        tf_recovery_ui_active_slot_line(
            active_slot,
            sizeof(active_slot)
        );

        char command_display[64];

        tf_recovery_ui_display_text(
            "treeforge recovery stage",
            command_display,
            sizeof(command_display)
        );

        const char *lines[] = {
            active_slot,
            "SOURCE                  TREEFORGE HOST",
            "RECEIVE MODE            ON",
            "FLASHING                DISABLED",
            "",
            "RUN ON HOST:",
            command_display,
            "THEN CHECK PACKAGE",
        };

        tf_recovery_ui_draw_info(
            "READY TO RECEIVE",
            lines,
            8,
            "VOL DOWN: CHECK   POWER: CANCEL"
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_POWER) {
            tf_recovery_set_install_set_receive_ready(
                0
            );

            return;
        }

        if (key != KEY_VOLUMEDOWN) {
            continue;
        }

        int status = tf_recovery_load_install_set(
            &tf_recovery_install_set
        );

        if (status == 1) {
            /*
             * Package metadata has been accepted. Receiving is no longer
             * armed while the user reviews this exact package.
             */
            tf_recovery_set_install_set_receive_ready(
                0
            );

            /*
             * Package metadata is now accepted.
             *
             * Return to the owning staged-set loop so it reloads the
             * valid package and presents the real action menu.
             */
            return;
        }

        const char *error_lines[] = {
            (
                status == 0
                ? "PACKAGE                 NOT RECEIVED"
                : "PACKAGE                 INVALID"
            ),
            "FLASHING                DISABLED",
            "",
            "NO PARTITIONS WERE WRITTEN",
        };

        tf_recovery_ui_draw_info(
            "STAGED INSTALL SET",
            error_lines,
            4,
            "POWER: BACK"
        );

        for (;;) {
            if (
                tf_recovery_ui_wait_key(
                    inputs
                )
                == KEY_POWER
            ) {
                break;
            }
        }
    }
}


static int tf_recovery_ui_confirm_receive(
    long *inputs
) {
    static const char *items[] = {
        "YES - ALLOW HOST",
        "NO - GO BACK",
    };

    /*
     * Default to NO even though receiving is non-destructive. This keeps
     * explicit host-session authorization visibly intentional.
     */
    int selected = 1;

    for (;;) {
        tf_recovery_ui_draw_menu(
            "ENABLE RECEIVE?",
            "NO PARTITIONS WILL BE WRITTEN",
            items,
            2,
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_VOLUMEUP) {
            selected = (
                selected
                + 1
            ) % 2;

            continue;
        }

        if (key == KEY_VOLUMEDOWN) {
            selected = (
                selected
                + 1
            ) % 2;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        return (
            selected == 0
        );
    }
}


static int tf_recovery_discard_install_set_metadata(
    void
) {
    /*
     * Discarding a package also disarms any receive session.
     */
    tf_recovery_set_install_set_receive_ready(
        0
    );

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_INSTALL_SET_TRANSFER_STATE_PATH,
        0
    );

    long result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_INSTALL_SET_MANIFEST_PATH,
        0
    );

    if (
        result != 0
        && result != -2
    ) {
        return 0;
    }

    memset(
        &tf_recovery_install_set,
        0,
        sizeof(tf_recovery_install_set)
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );

    return 1;
}


static int tf_recovery_ui_confirm_install_set_metadata_action(
    long *inputs,
    const char *title,
    const char *subtitle,
    const char *yes_label
) {
    const char *items[2];

    items[0] = yes_label;
    items[1] = "NO - GO BACK";

    /*
     * Package deletion/replacement defaults to No.
     */
    int selected = 1;

    for (;;) {
        tf_recovery_ui_draw_menu(
            title,
            subtitle,
            items,
            2,
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (
            key == KEY_VOLUMEUP
            || key == KEY_VOLUMEDOWN
        ) {
            selected = (
                selected
                + 1
            ) % 2;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        return (
            selected == 0
        );
    }
}


static void tf_recovery_ui_show_install_set_discard_result(
    long *inputs,
    int success
) {
    const char *lines[] = {
        (
            success
            ? "STAGED SET              DISCARDED"
            : "STAGED SET              DISCARD FAILED"
        ),
        "FLASHING                DISABLED",
        "",
        (
            success
            ? "PACKAGE METADATA REMOVED"
            : "PACKAGE METADATA PRESERVED"
        ),
    };

    tf_recovery_ui_draw_info(
        "STAGED INSTALL SET",
        lines,
        4,
        "POWER: BACK"
    );

    for (;;) {
        if (
            tf_recovery_ui_wait_key(
                inputs
            )
            == KEY_POWER
        ) {
            return;
        }
    }
}



static void tf_recovery_ui_show_v2_install_unavailable(
    long *inputs,
    const struct tf_recovery_install_set_result *set
) {
    if (!inputs || !set) {
        return;
    }

    char snapshots[64];

    usize position = tf_append_text(
        snapshots,
        sizeof(snapshots),
        0,
        "SNAPSHOT COW             "
    );

    tf_append_u64(
        snapshots,
        sizeof(snapshots),
        position,
        (u64) set->snapshot_cow_count
    );

    const char *lines[] = {
        "WIRE                     V2",
        snapshots,
        "VIRTUAL A/B              RECOGNIZED",
        "PAYLOAD VERIFY           VERIFIED",
        "SNAPSHOT COORDINATOR     NOT ENABLED",
        "FLASHING                 DISABLED",
        "NO PARTITIONS WERE WRITTEN",
        "SLOT ACTIVATION          DISABLED",
    };

    tf_recovery_ui_draw_info(
        "V2 INSTALL UNAVAILABLE",
        lines,
        8,
        "POWER: BACK"
    );

    while (
        tf_recovery_ui_wait_key(
            inputs
        )
        != KEY_POWER
    ) {
    }
}


static void tf_recovery_ui_show_staged_install_set(
    long *inputs
) {
    for (;;) {
        int request_receive = 0;

        int existing_status = (
            tf_recovery_load_install_set(
                &tf_recovery_install_set
            )
        );

        /*
         * Valid persisted package.
         *
         * Persistence across Recovery reboot is intentional, but it must
         * never prevent the user from replacing or discarding the set.
         */
        if (existing_status == 1) {
            int selected = 0;

            for (;;) {
                char subtitle[128];

                usize position = tf_append_text(
                    subtitle,
                    sizeof(subtitle),
                    0,
                    "TARGET SLOT: "
                );

                char slot[2];

                slot[0] = (
                    tf_recovery_install_set.target_slot == 'a'
                    ? 'A'
                    : 'B'
                );
                slot[1] = '\0';

                position = tf_append_text(
                    subtitle,
                    sizeof(subtitle),
                    position,
                    slot
                );

                position = tf_append_text(
                    subtitle,
                    sizeof(subtitle),
                    position,
                    "  STATUS: "
                );

                tf_append_text(
                    subtitle,
                    sizeof(subtitle),
                    position,
                    tf_recovery_install_transaction_status_name(
                        &tf_recovery_install_set
                    )
                );

                const char *items[5];
                int item_count = 0;

                if (
                    tf_recovery_install_set
                        .install_transaction_started
                ) {
                    items[0] = "INSTALL STATUS";
                    items[1] = "REVIEW STAGED SET";
                    items[2] = "BACK";
                    item_count = 3;
                } else {
                    items[0] = "REVIEW STAGED SET";

                    items[1] = (
                        tf_recovery_install_set.wire_version
                            == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
                        ? (
                            tf_recovery_install_set
                                .payload_verification_complete
                            && tf_recovery_install_set
                                .payload_verified_count
                                == tf_recovery_install_set
                                    .image_count
                            ? "VABC INSTALL DISABLED"
                            : "VERIFY PAYLOADS"
                        )
                        : (
                            tf_recovery_install_set
                                .payload_verification_complete
                            && tf_recovery_install_set
                                .payload_verified_count
                                == tf_recovery_install_set
                                    .image_count
                            ? "INSTALL SET"
                            : "VERIFY PAYLOADS"
                        )
                    );

                    items[2] = "RECEIVE NEW SET";
                    items[3] = "DISCARD STAGED SET";
                    items[4] = "BACK";
                    item_count = 5;
                }

                if (selected >= item_count) {
                    selected = 0;
                }

                tf_recovery_ui_draw_menu(
                    "STAGED INSTALL SET",
                    subtitle,
                    items,
                    item_count,
                    selected
                );

                int key = tf_recovery_ui_wait_key(
                    inputs
                );

                if (key == KEY_VOLUMEUP) {
                    selected = (
                        selected
                        + item_count
                        - 1
                    ) % item_count;

                    continue;
                }

                if (key == KEY_VOLUMEDOWN) {
                    selected = (
                        selected
                        + 1
                    ) % item_count;

                    continue;
                }

                if (key != KEY_POWER) {
                    continue;
                }

                /*
                 * Once a destructive transaction starts, replacement
                 * and discard disappear. Re-entry is status-only.
                 */
                if (
                    tf_recovery_install_set
                        .install_transaction_started
                ) {
                    if (selected == 0) {
                        tf_recovery_ui_show_physical_raw_set_result(
                            inputs,
                            &tf_recovery_install_set
                        );

                        continue;
                    }

                    if (selected == 1) {
                        tf_recovery_ui_install_set_summary(
                            inputs,
                            &tf_recovery_install_set
                        );

                        continue;
                    }

                    return;
                }

                if (selected == 0) {
                    tf_recovery_ui_install_set_summary(
                        inputs,
                        &tf_recovery_install_set
                    );

                    continue;
                }

                if (selected == 1) {
                    if (
                        tf_recovery_install_set.wire_version
                            == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
                        && !(
                            tf_recovery_install_set
                                .payload_verification_complete
                            && tf_recovery_install_set
                                .payload_verified_count
                                == tf_recovery_install_set
                                    .image_count
                        )
                    ) {
                        tf_recovery_ui_verify_install_set_payloads(
                            inputs,
                            &tf_recovery_install_set
                        );
                    } else if (
                        tf_recovery_install_set.wire_version
                        == TREEFORGE_RECOVERY_INSTALL_SET_WIRE_V2
                    ) {
                        tf_recovery_ui_show_v2_install_unavailable(
                            inputs,
                            &tf_recovery_install_set
                        );
                    } else if (
                        tf_recovery_install_set
                            .payload_verification_complete
                        && tf_recovery_install_set
                            .payload_verified_count
                            == tf_recovery_install_set
                                .image_count
                    ) {
                        tf_recovery_ui_physical_raw_install_set(
                            inputs,
                            &tf_recovery_install_set
                        );
                    } else {
                        tf_recovery_ui_verify_install_set_payloads(
                            inputs,
                            &tf_recovery_install_set
                        );
                    }

                    continue;
                }

                if (selected == 2) {
                    if (
                        !tf_recovery_ui_confirm_install_set_metadata_action(
                            inputs,
                            "REPLACE STAGED SET?",
                            "OLD PACKAGE WILL BE DISCARDED",
                            "YES - RECEIVE NEW"
                        )
                    ) {
                        continue;
                    }

                    int discarded = (
                        tf_recovery_discard_install_set_metadata()
                    );

                    if (!discarded) {
                        tf_recovery_ui_show_install_set_discard_result(
                            inputs,
                            0
                        );

                        continue;
                    }

                    request_receive = 1;
                    break;
                }

                if (selected == 3) {
                    if (
                        !tf_recovery_ui_confirm_install_set_metadata_action(
                            inputs,
                            "DISCARD STAGED SET?",
                            "PACKAGE METADATA WILL BE REMOVED",
                            "YES - DISCARD"
                        )
                    ) {
                        continue;
                    }

                    int discarded = (
                        tf_recovery_discard_install_set_metadata()
                    );

                    tf_recovery_ui_show_install_set_discard_result(
                        inputs,
                        discarded
                    );

                    break;
                }

                return;
            }

            if (!request_receive) {
                continue;
            }
        }

        else if (existing_status < 0) {
            static const char *items[] = {
                "RECEIVE NEW SET",
                "DISCARD INVALID SET",
                "BACK",
            };

            int selected = 0;

            for (;;) {
                tf_recovery_ui_draw_menu(
                    "INVALID STAGED SET",
                    "FLASHING DISABLED",
                    items,
                    3,
                    selected
                );

                int key = (
                    tf_recovery_ui_wait_key(
                        inputs
                    )
                );

                if (key == KEY_VOLUMEUP) {
                    selected = (
                        selected
                        + 2
                    ) % 3;

                    continue;
                }

                if (key == KEY_VOLUMEDOWN) {
                    selected = (
                        selected
                        + 1
                    ) % 3;

                    continue;
                }

                if (key != KEY_POWER) {
                    continue;
                }

                if (selected == 0) {
                    if (
                        !tf_recovery_ui_confirm_install_set_metadata_action(
                            inputs,
                            "REPLACE INVALID SET?",
                            "OLD METADATA WILL BE REMOVED",
                            "YES - RECEIVE NEW"
                        )
                    ) {
                        continue;
                    }

                    if (
                        !tf_recovery_discard_install_set_metadata()
                    ) {
                        tf_recovery_ui_show_install_set_discard_result(
                            inputs,
                            0
                        );

                        continue;
                    }

                    request_receive = 1;
                    break;
                }

                if (selected == 1) {
                    if (
                        !tf_recovery_ui_confirm_install_set_metadata_action(
                            inputs,
                            "DISCARD INVALID SET?",
                            "PACKAGE METADATA WILL BE REMOVED",
                            "YES - DISCARD"
                        )
                    ) {
                        continue;
                    }

                    int discarded = (
                        tf_recovery_discard_install_set_metadata()
                    );

                    tf_recovery_ui_show_install_set_discard_result(
                        inputs,
                        discarded
                    );

                    break;
                }

                return;
            }

            if (!request_receive) {
                continue;
            }
        }

        /*
         * No package is present. Preserve the explicit receive
         * authorization boundary.
         */
        else {
            static const char *items[] = {
                "ENABLE RECEIVE",
                "BACK",
            };

            int selected = 0;

            for (;;) {
                char active_slot[64];

                tf_recovery_ui_active_slot_line(
                    active_slot,
                    sizeof(active_slot)
                );

                tf_recovery_ui_draw_menu(
                    "STAGED INSTALL SET",
                    active_slot,
                    items,
                    2,
                    selected
                );

                int key = (
                    tf_recovery_ui_wait_key(
                        inputs
                    )
                );

                if (
                    key == KEY_VOLUMEUP
                    || key == KEY_VOLUMEDOWN
                ) {
                    selected = (
                        selected
                        + 1
                    ) % 2;

                    continue;
                }

                if (key != KEY_POWER) {
                    continue;
                }

                if (selected == 0) {
                    request_receive = 1;
                    break;
                }

                return;
            }
        }

        if (!request_receive) {
            continue;
        }

        if (
            !tf_recovery_ui_confirm_receive(
                inputs
            )
        ) {
            continue;
        }

        if (
            !tf_recovery_set_install_set_receive_ready(
                1
            )
        ) {
            const char *error_lines[] = {
                "RECEIVE MODE            ERROR",
                "FLASHING                DISABLED",
                "",
                "FAILED TO ARM HOST RECEIVE",
            };

            tf_recovery_ui_draw_info(
                "STAGED INSTALL SET",
                error_lines,
                4,
                "POWER: BACK"
            );

            for (;;) {
                if (
                    tf_recovery_ui_wait_key(
                        inputs
                    )
                    == KEY_POWER
                ) {
                    break;
                }
            }

            continue;
        }

        tf_recovery_ui_show_receive_ready(
            inputs
        );

        /*
         * Re-evaluate persisted package state after receive/check.
         *
         * A successful CHECK PACKAGE therefore transitions directly
         * into the valid staged-set action menu.
         */
        continue;
    }
}


static void tf_recovery_ui_show_device_image_placeholder(
    long *inputs
) {
    const char *lines[] = {
        "SOURCE                  DEVICE FILE",
        "BROWSER                 NOT YET ENABLED",
        "FLASHING                DISABLED",
        "",
        "THIS PATH WILL USE THE",
        "SAME UNIFIED IMAGE PLANNER",
    };

    tf_recovery_ui_draw_info(
        "IMAGE ON DEVICE",
        lines,
        6,
        "POWER: BACK"
    );

    for (;;) {
        if (
            tf_recovery_ui_wait_key(
                inputs
            )
            == KEY_POWER
        ) {
            return;
        }
    }
}


static void tf_recovery_ui_show_flash_options(
    long *inputs
) {
    static const char *items[] = {
        "STAGED INSTALL SET",
        "IMAGE ON DEVICE",
        "BACK",
    };

    int selected = 0;

    for (;;) {
        char active_slot[64];

        tf_recovery_ui_active_slot_line(
            active_slot,
            sizeof(active_slot)
        );

        tf_recovery_ui_draw_menu(
            "FLASH OPTIONS",
            active_slot,
            items,
            3,
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_VOLUMEUP) {
            selected = (
                selected
                + 2
            ) % 3;

            continue;
        }

        if (key == KEY_VOLUMEDOWN) {
            selected = (
                selected
                + 1
            ) % 3;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        if (selected == 0) {
            tf_recovery_ui_show_staged_install_set(
                inputs
            );

            continue;
        }

        if (selected == 1) {
            tf_recovery_ui_show_device_image_placeholder(
                inputs
            );

            continue;
        }

        return;
    }
}


__attribute__((noreturn))
static void tf_recovery_ui_reboot_action(
    const char *target,
    long *inputs,
    int created_input_directory,
    int *created_input_nodes
) {
    tf_drm_menu_cleanup();

    tf_recovery_ui_close_inputs(
        inputs
    );

    tf_recovery_ui_cleanup_realized_input_nodes(
        created_input_directory,
        created_input_nodes
    );

    tf_close(
        tf_recovery_ui_tty
    );

    tf_close(
        tf_recovery_ui_console
    );

    tf_close(
        tf_recovery_ui_kmsg
    );

    tf_recovery_ui_tty = -1;
    tf_recovery_ui_console = -1;
    tf_recovery_ui_kmsg = -1;

    tf_syscall1(
        SYS_SYNC,
        0
    );

    if (
        target
        && target[0]
    ) {
        tf_syscall4(
            SYS_REBOOT,
            LINUX_REBOOT_MAGIC1,
            LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART2,
            (long) target
        );
    } else {
        tf_syscall4(
            SYS_REBOOT,
            LINUX_REBOOT_MAGIC1,
            LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART,
            0
        );
    }

    for (;;) {
        tf_recovery_ui_sleep_ms(
            1000
        );
    }
}


__attribute__((noreturn))
static void tf_recovery_ui_run(void) {
    tf_recovery_ui_kmsg = tf_open(
        "/dev/kmsg",
        O_WRONLY
        | O_NONBLOCK
    );

    tf_recovery_ui_tty = tf_open(
        "/dev/tty0",
        O_WRONLY
        | O_NONBLOCK
    );

    tf_recovery_ui_console = tf_open(
        "/dev/console",
        O_WRONLY
        | O_NONBLOCK
    );

    int created_input_directory = 0;

    int created_input_nodes[
        TREEFORGE_RECOVERY_UI_INPUT_COUNT
    ];

    int sysfs_devices_seen = 0;

    tf_recovery_ui_realize_input_nodes(
        &created_input_directory,
        created_input_nodes,
        &sysfs_devices_seen
    );

    long inputs[
        TREEFORGE_RECOVERY_UI_INPUT_COUNT
    ];

    tf_recovery_ui_open_inputs(
        inputs
    );

    /*
     * This is the exact accepted generic DRM/KMS realization path
     * copied from TreeForge's hardware-accepted early dispatcher.
     */
    tf_probe_display_surfaces();

    tf_recovery_ui_log(
        "ui begin"
    );

    static const char *items[] = {
        "FLASH OPTIONS",
        "PARTITION INFORMATION",
        "DIAGNOSTICS",
        "REBOOT ANDROID",
        "REBOOT BOOTLOADER",
        "REBOOT STOCK RECOVERY",
    };

    int selected = 0;

    for (;;) {
        char active_slot[64];

        tf_recovery_ui_active_slot_line(
            active_slot,
            sizeof(active_slot)
        );

        tf_recovery_ui_draw_menu(
            "TREEFORGE RECOVERY",
            active_slot,
            items,
            6,
            selected
        );

        int key = (
            tf_recovery_ui_wait_key(
                inputs
            )
        );

        if (key == KEY_VOLUMEUP) {
            selected = (
                selected
                + 5
            ) % 6;

            continue;
        }

        if (key == KEY_VOLUMEDOWN) {
            selected = (
                selected
                + 1
            ) % 6;

            continue;
        }

        if (key != KEY_POWER) {
            continue;
        }

        if (selected == 0) {
            tf_recovery_ui_show_flash_options(
                inputs
            );

            continue;
        }

        if (selected == 1) {
            tf_recovery_ui_show_partitions(
                inputs
            );

            continue;
        }

        if (selected == 2) {
            tf_recovery_ui_show_diagnostics(
                inputs
            );

            continue;
        }

        if (selected == 3) {
            tf_recovery_ui_reboot_action(
                0,
                inputs,
                created_input_directory,
                created_input_nodes
            );
        }

        if (selected == 4) {
            tf_recovery_ui_reboot_action(
                "bootloader",
                inputs,
                created_input_directory,
                created_input_nodes
            );
        }

        tf_recovery_ui_reboot_action(
            "recovery",
            inputs,
            created_input_directory,
            created_input_nodes
        );
    }
}


static void tf_reboot_after_inventory(void) {
    tf_syscall1(
        SYS_SYNC,
        0
    );

    tf_syscall4(
        SYS_REBOOT,
        LINUX_REBOOT_MAGIC1,
        LINUX_REBOOT_MAGIC2,
        LINUX_REBOOT_CMD_RESTART,
        0
    );
}



/*
 * TreeForge Recovery ADB USB scaffold.
 *
 * This stage realizes only the generic kernel-facing prerequisites for
 * canonical Android Recovery ADB:
 *
 *   configfs
 *     -> usb_gadget/g1
 *     -> functions/ffs.adb
 *     -> configs/b.1
 *
 *   FunctionFS
 *     -> /dev/usb-ffs/adb
 *
 * It intentionally does NOT:
 *
 *   - launch adbd;
 *   - link ffs.adb into the active gadget configuration;
 *   - bind a USB device controller;
 *   - enable any block-device writer.
 *
 * Canonical USB VID/PID/controller realization belongs to the following
 * ADB lifecycle/binding milestone.
 */

#define TREEFORGE_RECOVERY_ADB_USB_STATUS_PATH \
    "/metadata/treeforge/recovery-adb-usb-status"

#define TREEFORGE_RECOVERY_ADBD_LAUNCH_STATUS_PATH \
    "/metadata/treeforge/recovery-adbd-launch-status"

#define TREEFORGE_RECOVERY_ADBD_CHILD_STATUS_PATH \
    "/metadata/treeforge/recovery-adbd-child-status"

#define TREEFORGE_RECOVERY_ADB_PREFLIGHT_REQUEST_PATH \
    "/dev/treeforge-recovery-adb-preflight"

#define TREEFORGE_RECOVERY_VABC_PROBE_REQUEST_PATH \
    "/metadata/treeforge/recovery-vabc-probe-request"

#define TREEFORGE_RECOVERY_VABC_PROBE_REPORT_PATH \
    "/metadata/treeforge/recovery-vabc-probe"

#define TREEFORGE_RECOVERY_VABC_PROBE_STATUS_PATH \
    "/metadata/treeforge/recovery-vabc-probe-status"

#define TREEFORGE_RECOVERY_ADB_HANDOFF_PATH \
    "/dev/treeforge-recovery-adb-handoff"

#define TF_USB_ERRNO_EBUSY 16
#define TF_USB_ERRNO_EEXIST 17


static long tf_usb_syscall5(
    long number,
    long arg1,
    long arg2,
    long arg3,
    long arg4,
    long arg5
) {
    register long x8 asm("x8") = number;
    register long x0 asm("x0") = arg1;
    register long x1 asm("x1") = arg2;
    register long x2 asm("x2") = arg3;
    register long x3 asm("x3") = arg4;
    register long x4 asm("x4") = arg5;

    asm volatile(
        "svc 0"
        : "+r"(x0)
        : "r"(x8),
          "r"(x1),
          "r"(x2),
          "r"(x3),
          "r"(x4)
        : "memory"
    );

    return x0;
}


static int tf_usb_mkdir(
    const char *path,
    long mode
) {
    long result = tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) path,
        mode
    );

    return (
        result == 0
        || result == -TF_USB_ERRNO_EEXIST
    );
}


static int tf_usb_mount(
    const char *source,
    const char *target,
    const char *filesystem,
    unsigned long flags,
    const char *options
) {
    long result = tf_usb_syscall5(
        SYS_MOUNT,
        (long) source,
        (long) target,
        (long) filesystem,
        (long) flags,
        (long) options
    );

    /*
     * EBUSY is accepted because Recovery may inherit an already-mounted
     * instance from the Android first-stage environment.
     */
    return (
        result == 0
        || result == -TF_USB_ERRNO_EBUSY
    );
}


static void tf_usb_write_all(
    long fd,
    const char *value
) {
    if (
        fd < 0
        || !value
    ) {
        return;
    }

    usize length = tf_strlen(
        value
    );

    usize written = 0;

    while (
        written < length
    ) {
        long result = tf_syscall3(
            SYS_WRITE,
            fd,
            (long) (
                value
                + written
            ),
            length - written
        );

        if (result <= 0) {
            return;
        }

        written += (
            (usize) result
        );
    }
}


#define TF_USB_ERRNO_ENOENT 2

#define TREEFORGE_RECOVERY_ADB_FFS_READY_PATH \
    "/config/usb_gadget/g1/functions/ffs.adb/ready"

#define TREEFORGE_RECOVERY_ADBD_FUNCTIONFS_STATUS_PATH \
    "/metadata/treeforge/recovery-adbd-functionfs-status"

#define TREEFORGE_RECOVERY_ADB_FUNCTION_LINK_PATH \
    "/config/usb_gadget/g1/configs/b.1/f1"

#define TREEFORGE_RECOVERY_ADB_FUNCTION_TARGET \
    "/config/usb_gadget/g1/functions/ffs.adb"

#define TREEFORGE_RECOVERY_USB_UDC_PATH \
    "/config/usb_gadget/g1/UDC"

#define TREEFORGE_RECOVERY_ADB_READY_POLL_MS 25
#define TREEFORGE_RECOVERY_ADB_READY_POLL_COUNT 200

static int tf_usb_write_path_checked(
    const char *path,
    const char *value
) {
    if (
        !path
        || !value
    ) {
        return 0;
    }

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) path,
        O_WRONLY,
        0
    );

    if (fd < 0) {
        return 0;
    }

    usize length = tf_strlen(
        value
    );

    usize written = 0;

    while (
        written < length
    ) {
        long amount = tf_syscall3(
            SYS_WRITE,
            fd,
            (long) (
                value
                + written
            ),
            length - written
        );

        if (amount <= 0) {
            tf_close(
                fd
            );

            return 0;
        }

        written += (
            (usize) amount
        );
    }

    tf_close(
        fd
    );

    return 1;
}


static void tf_recovery_adbd_write_u64(
    long fd,
    u64 value
) {
    char reversed[32];
    char output[32];

    usize count = 0;

    do {
        reversed[count++] = (
            (char) (
                '0'
                + (
                    value % 10ULL
                )
            )
        );

        value /= 10ULL;
    } while (
        value != 0
        && count < sizeof(reversed)
    );

    for (
        usize index = 0;
        index < count;
        index++
    ) {
        output[index] = (
            reversed[
                count - index - 1
            ]
        );
    }

    output[count] = '\0';

    tf_usb_write_all(
        fd,
        output
    );
}


static void tf_recovery_adbd_write_launch_status(
    const char *stage,
    long result
) {
    tf_usb_mkdir(
        "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_ADBD_LAUNCH_STATUS_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return;
    }

    tf_usb_write_all(
        fd,
        "stage="
    );

    tf_usb_write_all(
        fd,
        stage
        ? stage
        : "unknown"
    );

    tf_usb_write_all(
        fd,
        "\nerrno="
    );

    tf_recovery_adbd_write_u64(
        fd,
        result < 0
        ? (u64) (-result)
        : 0ULL
    );

    tf_usb_write_all(
        fd,
        "\n"
    );

    tf_close(
        fd
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );
}


static void tf_recovery_adbd_write_child_status(
    int status
) {
    tf_usb_mkdir(
        "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_ADBD_CHILD_STATUS_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return;
    }

    unsigned int raw = (
        (unsigned int) status
    );

    unsigned int low = (
        raw & 0x7fU
    );

    int exited = (
        low == 0
    );

    int signaled = (
        low != 0
        && low != 0x7fU
    );

    unsigned int exit_code = (
        (raw >> 8)
        & 0xffU
    );

    tf_usb_write_all(
        fd,
        "wait_raw="
    );

    tf_recovery_adbd_write_u64(
        fd,
        raw
    );

    tf_usb_write_all(
        fd,
        "\nexited="
    );

    tf_usb_write_all(
        fd,
        exited
        ? "1"
        : "0"
    );

    tf_usb_write_all(
        fd,
        "\nexit_code="
    );

    tf_recovery_adbd_write_u64(
        fd,
        exited
        ? exit_code
        : 0
    );

    tf_usb_write_all(
        fd,
        "\nsignaled="
    );

    tf_usb_write_all(
        fd,
        signaled
        ? "1"
        : "0"
    );

    tf_usb_write_all(
        fd,
        "\nsignal="
    );

    tf_recovery_adbd_write_u64(
        fd,
        signaled
        ? low
        : 0
    );

    tf_usb_write_all(
        fd,
        "\n"
    );

    tf_close(
        fd
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );
}


static int tf_recovery_adb_usb_scaffold_ready = 0;
static int tf_recovery_adb_functionfs_descriptors_ready = 0;
static int tf_recovery_adb_function_linked = 0;
static int tf_recovery_adb_gadget_bound = 0;

static int tf_recovery_adbd_started = 0;
static long tf_recovery_adbd_pid = -1;


static void tf_usb_write_status(
    int configfs_ready,
    int functionfs_ready
) {
    /*
     * /metadata/treeforge normally already exists because Recovery owns
     * that diagnostics namespace. Keep this idempotent for robustness.
     */
    tf_usb_mkdir(
        "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_ADB_USB_STATUS_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return;
    }

    if (configfs_ready) {
        tf_usb_write_all(
            fd,
            "configfs_ready=1\n"
        );
    } else {
        tf_usb_write_all(
            fd,
            "configfs_ready=0\n"
        );
    }

    if (functionfs_ready) {
        tf_usb_write_all(
            fd,
            "functionfs_ready=1\n"
        );
    } else {
        tf_usb_write_all(
            fd,
            "functionfs_ready=0\n"
        );
    }

    if (tf_recovery_adbd_started) {
        tf_usb_write_all(
            fd,
            "adbd_started=1\n"
        );
    } else {
        tf_usb_write_all(
            fd,
            "adbd_started=0\n"
        );
    }

    if (
        tf_recovery_adb_functionfs_descriptors_ready
    ) {
        tf_usb_write_all(
            fd,
            "functionfs_descriptors_ready=1\n"
        );
    } else {
        tf_usb_write_all(
            fd,
            "functionfs_descriptors_ready=0\n"
        );
    }

    if (
        tf_recovery_adb_function_linked
    ) {
        tf_usb_write_all(
            fd,
            "function_linked=1\n"
        );
    } else {
        tf_usb_write_all(
            fd,
            "function_linked=0\n"
        );
    }

    if (
        tf_recovery_adb_gadget_bound
    ) {
        tf_usb_write_all(
            fd,
            "gadget_bound=1\n"
        );
    } else {
        tf_usb_write_all(
            fd,
            "gadget_bound=0\n"
        );
    }

    /*
     * Writer capability exists, but there is no generic enable switch.
     * Every writable block descriptor remains gated by an exact
     * revalidated interactive flash plan.
     */
    tf_usb_write_all(
        fd,
        "writer_enabled=1\n"
    );

    tf_usb_write_all(
        fd,
        "writer_requires_plan_authorization=1\n"
    );

    tf_close(
        fd
    );
}


static void tf_setup_recovery_adb_usb_scaffold(void) {
    int configfs_ready = 0;
    int functionfs_ready = 0;

    /*
     * Android FirstStageMain may already have created /config. mkdirat is
     * deliberately idempotent.
     */
    if (
        !tf_usb_mkdir(
            "/config",
            0755
        )
    ) {
        tf_usb_write_status(
            0,
            0
        );

        return;
    }

    if (
        !tf_usb_mount(
            "none",
            "/config",
            "configfs",
            0,
            0
        )
    ) {
        tf_usb_write_status(
            0,
            0
        );

        return;
    }

    /*
     * Realize only the ADB-relevant subset of the canonical Recovery
     * configfs topology.
     */
    const char *configfs_directories[] = {
        "/config/usb_gadget",
        "/config/usb_gadget/g1",
        "/config/usb_gadget/g1/strings",
        "/config/usb_gadget/g1/strings/0x409",
        "/config/usb_gadget/g1/functions",
        "/config/usb_gadget/g1/functions/ffs.adb",
        "/config/usb_gadget/g1/configs",
        "/config/usb_gadget/g1/configs/b.1",
        "/config/usb_gadget/g1/configs/b.1/strings",
        "/config/usb_gadget/g1/configs/b.1/strings/0x409",
    };

    const int configfs_directory_count = (
        sizeof(configfs_directories)
        / sizeof(configfs_directories[0])
    );

    for (
        int index = 0;
        index < configfs_directory_count;
        index++
    ) {
        if (
            !tf_usb_mkdir(
                configfs_directories[index],
                0770
            )
        ) {
            tf_usb_write_status(
                0,
                0
            );

            return;
        }
    }

    configfs_ready = 1;

    /*
     * Canonical Recovery creates this mount before starting adbd.
     *
     * Keep the exact Recovery FunctionFS ownership contract here:
     * uid=2000,gid=2000.
     *
     * adbd itself is still deliberately not started in this patch.
     */
    if (
        !tf_usb_mkdir(
            "/dev/usb-ffs",
            0775
        )
        || !tf_usb_mkdir(
            "/dev/usb-ffs/adb",
            0770
        )
    ) {
        tf_usb_write_status(
            configfs_ready,
            0
        );

        return;
    }

    if (
        !tf_usb_mount(
            "adb",
            "/dev/usb-ffs/adb",
            "functionfs",
            0,
            "uid=2000,gid=2000"
        )
    ) {
        tf_usb_write_status(
            configfs_ready,
            0
        );

        return;
    }

    functionfs_ready = 1;
    tf_recovery_adb_usb_scaffold_ready = 1;

    tf_usb_write_status(
        configfs_ready,
        functionfs_ready
    );
}
 

static void tf_recovery_adbd_update_status(void) {
    tf_usb_write_status(
        tf_recovery_adb_usb_scaffold_ready,
        tf_recovery_adb_usb_scaffold_ready
    );
}


/*
 * TREEFORGE_RECOVERY_VABC_PROBE_V1
 *
 * Execute TreeForge's bundled full-COW libsnapshot coordinator in its
 * explicitly non-destructive probe mode.
 *
 * This milestone does NOT call BeginUpdate(), CreateUpdateSnapshots(),
 * MapAllSnapshots(), write a COW, mutate LP metadata, or activate a slot.
 *
 * Failure is non-fatal to Recovery. The coordinator's stdout/stderr is
 * persisted separately from the parent launch status.
 */
static void tf_recovery_vabc_probe_write_status(
    const char *stage,
    long result,
    int wait_raw
) {
    tf_usb_mkdir(
        "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_VABC_PROBE_STATUS_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return;
    }

    tf_usb_write_all(
        fd,
        "treeforge-recovery-vabc-probe-status-v1\nstage="
    );

    tf_usb_write_all(
        fd,
        stage
        ? stage
        : "unknown"
    );

    tf_usb_write_all(
        fd,
        "\nerrno="
    );

    tf_recovery_adbd_write_u64(
        fd,
        result < 0
        ? (u64) (-result)
        : 0ULL
    );

    tf_usb_write_all(
        fd,
        "\nwait_raw="
    );

    tf_recovery_adbd_write_u64(
        fd,
        (u64) (
            (unsigned int)
            wait_raw
        )
    );

    tf_usb_write_all(
        fd,
        "\n"
    );

    tf_close(
        fd
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );
}


static int tf_recovery_run_vabc_probe(
    const struct tf_runtime_partition_inventory *inventory
) {
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_VABC_PROBE_REPORT_PATH,
        0
    );

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_VABC_PROBE_STATUS_PATH,
        0
    );

    if (
        !inventory
        || !inventory->active_slot_resolved
        || (
            inventory->active_slot != 'a'
            && inventory->active_slot != 'b'
        )
    ) {
        tf_recovery_vabc_probe_write_status(
            "slot-unresolved",
            -1,
            0
        );

        return 0;
    }

    tf_usb_mkdir(
        "/metadata/treeforge",
        0755
    );

    long child = tf_syscall5(
        SYS_CLONE,
        TREEFORGE_SIGCHLD,
        0,
        0,
        0,
        0
    );

    if (child < 0) {
        tf_recovery_vabc_probe_write_status(
            "clone",
            child,
            0
        );

        return 0;
    }

    if (child == 0) {
        long output = tf_syscall4(
            SYS_OPENAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_VABC_PROBE_REPORT_PATH,
            O_WRONLY
            | O_CREAT
            | O_TRUNC,
            0644
        );

        if (output < 0) {
            tf_syscall1(
                SYS_EXIT,
                126
            );

            for (;;) {
            }
        }

        long stdout_result = tf_syscall3(
            SYS_DUP3,
            output,
            1,
            0
        );

        long stderr_result = tf_syscall3(
            SYS_DUP3,
            output,
            2,
            0
        );

        if (
            stdout_result < 0
            || stderr_result < 0
        ) {
            tf_syscall1(
                SYS_EXIT,
                125
            );

            for (;;) {
            }
        }

        if (output > 2) {
            tf_close(
                output
            );
        }

        char slot_argument[] =
            "--slot=_a";

        slot_argument[8] = (
            inventory->active_slot
        );

        char *argv[] = {
            (char *)
                "/dev/treeforge-recovery-runtime/system/bin/linker64",
            (char *)
                "/dev/treeforge-recovery-runtime/system/bin/treeforge-vabc-coordinator",
            (char *) "--probe",
            slot_argument,
            0
        };

        char *envp[] = {
            (char *) "HOME=/",
            (char *)
                "PATH=/sbin:/system/bin:/system/xbin",
            (char *) "ANDROID_ROOT=/system",
            (char *)
                "LD_LIBRARY_PATH=/dev/treeforge-recovery-runtime/system/lib64",
            0
        };

        long exec_result = tf_syscall3(
            SYS_EXECVE,
            (long)
                "/dev/treeforge-recovery-runtime/system/bin/linker64",
            (long) argv,
            (long) envp
        );

        tf_usb_write_all(
            2,
            "treeforge-vabc-probe-exec-failed\nerrno="
        );

        tf_recovery_adbd_write_u64(
            2,
            exec_result < 0
            ? (u64) (-exec_result)
            : 0ULL
        );

        tf_usb_write_all(
            2,
            "\n"
        );

        tf_syscall1(
            SYS_EXIT,
            127
        );

        for (;;) {
        }
    }

    /*
     * Keep a failed provider from hanging Recovery indefinitely.
     * Probe construction should complete essentially immediately;
     * allow roughly two seconds before terminating the child.
     */
    for (
        int attempt = 0;
        attempt < 200;
        attempt++
    ) {
        int child_status = 0;

        long wait_result = tf_syscall4(
            SYS_WAIT4,
            child,
            (long) &child_status,
            TREEFORGE_WAIT_WNOHANG,
            0
        );

        if (wait_result == child) {
            unsigned int raw = (
                (unsigned int)
                child_status
            );

            int exited = (
                (raw & 0x7fU)
                == 0U
            );

            unsigned int exit_code = (
                (raw >> 8)
                & 0xffU
            );

            tf_recovery_vabc_probe_write_status(
                (
                    exited
                    && exit_code == 0U
                )
                ? "complete"
                : "child-error",
                0,
                child_status
            );

            return (
                exited
                && exit_code == 0U
            );
        }

        if (wait_result < 0) {
            tf_recovery_vabc_probe_write_status(
                "wait4",
                wait_result,
                child_status
            );

            return 0;
        }

        tf_recovery_ui_sleep_ms(
            10
        );
    }

    tf_syscall3(
        SYS_KILL,
        child,
        TREEFORGE_SIGKILL,
        0
    );

    int child_status = 0;

    tf_syscall4(
        SYS_WAIT4,
        child,
        (long) &child_status,
        0,
        0
    );

    tf_recovery_vabc_probe_write_status(
        "timeout",
        0,
        child_status
    );

    return 0;
}


static int tf_start_recovery_adbd(void) {
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_ADBD_LAUNCH_STATUS_PATH,
        0
    );

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_ADBD_CHILD_STATUS_PATH,
        0
    );

    if (
        !tf_recovery_adb_usb_scaffold_ready
    ) {
        tf_recovery_adbd_started = 0;
        tf_recovery_adbd_pid = -1;

        tf_recovery_adbd_update_status();

        return 0;
    }

    /*
     * AArch64 clone(SIGCHLD, NULL, NULL, NULL, NULL) provides
     * fork-like semantics:
     *
     *   child  -> 0
     *   parent -> child pid
     */
    long child = tf_syscall5(
        SYS_CLONE,
        TREEFORGE_SIGCHLD,
        0,
        0,
        0,
        0
    );

    if (child < 0) {
        tf_recovery_adbd_write_launch_status(
            "clone",
            child
        );

        tf_recovery_adbd_started = 0;
        tf_recovery_adbd_pid = -1;

        tf_recovery_adbd_update_status();

        return 0;
    }

    if (child == 0) {
        /*
         * Do not pass --root_seclabel.
         *
         * The bundled TreeForge standalone provider intentionally
         * avoids the normal pre-exec SELinux transition because
         * TreeForge Recovery runs before Android selinux_setup.
         */
        char *argv[] = {
            (char *)
                "/dev/treeforge-recovery-runtime/system/bin/linker64",
            (char *)
                "/dev/treeforge-recovery-runtime/system/bin/adbd",
            (char *) "--device_banner=recovery",
            0
        };

        /*
         * TreeForge Recovery runs before Android second-stage init and
         * before userdata is necessarily mounted writable.
         *
         * AOSP adbd does not require /data/local/tmp or /sdcard to
         * initialize its USB transport. Keep the daemon launch
         * environment independent of userdata availability.
         *
         * shell_service.cpp constructs subprocess-specific identity and
         * TMPDIR state later, when a shell service is actually requested.
         */
        char *envp[] = {
            (char *) "HOME=/",
            (char *) "PATH=/sbin:/system/bin:/system/xbin",
            (char *) "ANDROID_ROOT=/system",
            (char *)
                "LD_LIBRARY_PATH=/dev/treeforge-recovery-runtime/system/lib64",
            0
        };

        long exec_result = tf_syscall3(
            SYS_EXECVE,
            (long)
                "/dev/treeforge-recovery-runtime/system/bin/linker64",
            (long) argv,
            (long) envp
        );

        /*
         * Successful execve never returns.
         *
         * If we get here, preserve the exact Linux errno before the
         * child exits with the existing sentinel status 127.
         */
        tf_recovery_adbd_write_launch_status(
            "execve",
            exec_result
        );

        /*
         * execve returning is an error. The child must never continue
         * into TreeForge Recovery controller/UI code.
         */
        tf_syscall1(
            SYS_EXIT,
            127
        );

        for (;;) {
        }
    }

    tf_recovery_adbd_pid = child;

    /*
     * Reap an immediately failed child without blocking Recovery.
     *
     * A return of zero means the child is still alive. This is only
     * process-start acceptance; FunctionFS descriptor readiness is
     * deliberately a later lifecycle milestone.
     */
    int child_status = 0;

    long wait_result = tf_syscall4(
        SYS_WAIT4,
        tf_recovery_adbd_pid,
        (long) &child_status,
        TREEFORGE_WAIT_WNOHANG,
        0
    );

    if (
        wait_result == tf_recovery_adbd_pid
        || wait_result < 0
    ) {
        if (
            wait_result
            == tf_recovery_adbd_pid
        ) {
            tf_recovery_adbd_write_child_status(
                child_status
            );
        } else {
            tf_recovery_adbd_write_launch_status(
                "wait4",
                wait_result
            );
        }

        tf_recovery_adbd_started = 0;
        tf_recovery_adbd_pid = -1;

        tf_recovery_adbd_update_status();

        return 0;
    }

    tf_recovery_adbd_started = 1;

    tf_recovery_adbd_update_status();

    return 1;
}



static int tf_usb_inline_space(
    char value
) {
    return (
        value == ' '
        || value == '\t'
        || value == '\r'
    );
}


static int tf_usb_span_equals(
    const char *source,
    usize begin,
    usize end,
    const char *expected
) {
    if (
        !source
        || !expected
        || end < begin
    ) {
        return 0;
    }

    usize expected_length = tf_strlen(
        expected
    );

    usize actual_length = (
        end - begin
    );

    if (
        actual_length
        != expected_length
    ) {
        return 0;
    }

    return (
        memcmp(
            source + begin,
            expected,
            expected_length
        )
        == 0
    );
}


static int tf_usb_copy_span(
    const char *source,
    usize begin,
    usize end,
    char *output,
    usize capacity
) {
    if (
        !source
        || !output
        || capacity == 0
        || end < begin
    ) {
        return 0;
    }

    usize length = (
        end - begin
    );

    if (
        length + 1
        > capacity
    ) {
        output[0] = '\0';

        return 0;
    }

    for (
        usize index = 0;
        index < length;
        index++
    ) {
        char value = (
            source[
                begin + index
            ]
        );

        if (
            value == '\0'
            || value == '\n'
            || value == '\r'
        ) {
            output[0] = '\0';

            return 0;
        }

        output[index] = value;
    }

    output[length] = '\0';

    return 1;
}


/*
 * This is a targeted freestanding equivalent of AOSP r36
 * ImportBootconfigFromString() for one exact key.
 *
 * A found-but-empty value is intentionally reported as found. Android
 * allows a later source to replace an earlier value with empty data;
 * TreeForge must not silently fall through to a lower-priority source.
 */
static int tf_usb_find_bootconfig_value(
    const char *source,
    usize length,
    const char *key,
    char *output,
    usize capacity
) {
    if (
        !source
        || !key
        || !output
        || capacity == 0
    ) {
        return 0;
    }

    output[0] = '\0';

    usize cursor = 0;

    while (
        cursor < length
    ) {
        usize line_begin = cursor;

        while (
            cursor < length
            && source[cursor] != '\n'
        ) {
            cursor++;
        }

        usize line_end = cursor;

        if (
            cursor < length
            && source[cursor] == '\n'
        ) {
            cursor++;
        }

        usize equal = line_begin;

        while (
            equal < line_end
            && source[equal] != '='
        ) {
            equal++;
        }

        usize key_begin = line_begin;
        usize key_end = equal;

        while (
            key_begin < key_end
            && tf_usb_inline_space(
                source[key_begin]
            )
        ) {
            key_begin++;
        }

        while (
            key_end > key_begin
            && tf_usb_inline_space(
                source[key_end - 1]
            )
        ) {
            key_end--;
        }

        if (
            !tf_usb_span_equals(
                source,
                key_begin,
                key_end,
                key
            )
        ) {
            continue;
        }

        /*
         * AOSP treats "key" and "key =" as an empty value.
         */
        if (equal >= line_end) {
            return 1;
        }

        usize value_begin = (
            equal + 1
        );

        usize value_end = line_end;

        while (
            value_begin < value_end
            && tf_usb_inline_space(
                source[value_begin]
            )
        ) {
            value_begin++;
        }

        while (
            value_end > value_begin
            && tf_usb_inline_space(
                source[value_end - 1]
            )
        ) {
            value_end--;
        }

        /*
         * For ordinary values AOSP consumes surrounding quotes.
         * serialno is not one of the comma-list special cases.
         */
        if (
            value_end > value_begin + 1
            && source[value_begin] == '"'
            && source[value_end - 1] == '"'
        ) {
            value_begin++;
            value_end--;
        }

        tf_usb_copy_span(
            source,
            value_begin,
            value_end,
            output,
            capacity
        );

        return 1;
    }

    return 0;
}


/*
 * Targeted equivalent of AOSP r36 ImportKernelCmdlineFromString().
 *
 * Quoted spans may contain spaces. Quote characters themselves are
 * removed before the first '=' is interpreted.
 */
static int tf_usb_find_cmdline_value(
    const char *source,
    usize length,
    const char *key,
    char *output,
    usize capacity
) {
    if (
        !source
        || !key
        || !output
        || capacity == 0
    ) {
        return 0;
    }

    output[0] = '\0';

    usize cursor = 0;

    while (
        cursor < length
    ) {
        while (
            cursor < length
            && source[cursor] == ' '
        ) {
            cursor++;
        }

        if (cursor >= length) {
            break;
        }

        char piece[512];
        usize piece_length = 0;
        int quoted = 0;
        int overflow = 0;

        while (
            cursor < length
        ) {
            char value = source[cursor];

            if (value == '"') {
                quoted = !quoted;
                cursor++;
                continue;
            }

            if (
                value == ' '
                && !quoted
            ) {
                break;
            }

            if (
                piece_length + 1
                < sizeof(piece)
            ) {
                piece[piece_length++] = value;
            } else {
                overflow = 1;
            }

            cursor++;
        }

        while (
            cursor < length
            && source[cursor] == ' '
        ) {
            cursor++;
        }

        if (overflow) {
            continue;
        }

        piece[piece_length] = '\0';

        usize equal = 0;

        while (
            equal < piece_length
            && piece[equal] != '='
        ) {
            equal++;
        }

        usize key_end = (
            equal < piece_length
            ? equal
            : piece_length
        );

        if (
            !tf_usb_span_equals(
                piece,
                0,
                key_end,
                key
            )
        ) {
            continue;
        }

        if (equal >= piece_length) {
            return 1;
        }

        tf_usb_copy_span(
            piece,
            equal + 1,
            piece_length,
            output,
            capacity
        );

        return 1;
    }

    return 0;
}


static int tf_usb_serial_valid(
    const char *value
) {
    if (
        !value
        || !value[0]
    ) {
        return 0;
    }

    for (
        usize index = 0;
        value[index] != '\0';
        index++
    ) {
        if (
            value[index] == '\n'
            || value[index] == '\r'
            || value[index] == '\t'
        ) {
            return 0;
        }
    }

    return 1;
}


static int tf_usb_join_path(
    const char *directory,
    const char *name,
    char *output,
    usize capacity
) {
    if (
        !directory
        || !name
        || !output
        || capacity == 0
    ) {
        return 0;
    }

    usize directory_length = tf_strlen(
        directory
    );

    usize name_length = tf_strlen(
        name
    );

    int needs_slash = (
        directory_length > 0
        && directory[
            directory_length - 1
        ] != '/'
    );

    usize required = (
        directory_length
        + (
            needs_slash
            ? 1
            : 0
        )
        + name_length
        + 1
    );

    if (required > capacity) {
        return 0;
    }

    usize cursor = 0;

    for (
        usize index = 0;
        index < directory_length;
        index++
    ) {
        output[cursor++] = directory[index];
    }

    if (needs_slash) {
        output[cursor++] = '/';
    }

    for (
        usize index = 0;
        index < name_length;
        index++
    ) {
        output[cursor++] = name[index];
    }

    output[cursor] = '\0';

    return 1;
}


static int tf_usb_android_dt_directory(
    char *output,
    usize capacity
) {
    static char source[65536];

    char configured[512];

    long amount = tf_read_path(
        "/proc/bootconfig",
        source,
        sizeof(source)
    );

    if (amount >= 0) {
        int found = tf_usb_find_bootconfig_value(
            source,
            (usize) amount,
            "androidboot.android_dt_dir",
            configured,
            sizeof(configured)
        );

        if (found) {
            if (configured[0]) {
                usize length = tf_strlen(
                    configured
                );

                if (
                    length + 1
                    > capacity
                ) {
                    return 0;
                }

                memcpy(
                    output,
                    configured,
                    length + 1
                );

                return 1;
            }

            /*
             * GetAndroidDtDir() uses the default when bootconfig
             * explicitly supplies an empty value.
             */
            goto default_path;
        }
    }

    amount = tf_read_path(
        "/proc/cmdline",
        source,
        sizeof(source)
    );

    if (amount >= 0) {
        int found = tf_usb_find_cmdline_value(
            source,
            (usize) amount,
            "androidboot.android_dt_dir",
            configured,
            sizeof(configured)
        );

        if (
            found
            && configured[0]
        ) {
            usize length = tf_strlen(
                configured
            );

            if (
                length + 1
                > capacity
            ) {
                return 0;
            }

            memcpy(
                output,
                configured,
                length + 1
            );

            return 1;
        }
    }

default_path:
    {
        static const char path[] =
            "/proc/device-tree/firmware/android/";

        if (
            sizeof(path)
            > capacity
        ) {
            return 0;
        }

        memcpy(
            output,
            path,
            sizeof(path)
        );
    }

    return 1;
}


/*
 * Match the effective value Android eventually exports as ro.serialno.
 *
 * PropertyInit processes:
 *
 *     Android DT
 *     kernel cmdline
 *     bootconfig
 *
 * in that order, so the final-value precedence is the reverse:
 *
 *     bootconfig -> cmdline -> Android DT
 */
static int tf_recovery_runtime_serial(
    char *output,
    usize capacity
) {
    if (
        !output
        || capacity == 0
    ) {
        return 0;
    }

    output[0] = '\0';

    static char source[65536];

    long amount = tf_read_path(
        "/proc/bootconfig",
        source,
        sizeof(source)
    );

    if (amount >= 0) {
        int found = tf_usb_find_bootconfig_value(
            source,
            (usize) amount,
            "androidboot.serialno",
            output,
            capacity
        );

        if (found) {
            return tf_usb_serial_valid(
                output
            );
        }
    }

    amount = tf_read_path(
        "/proc/cmdline",
        source,
        sizeof(source)
    );

    if (amount >= 0) {
        int found = tf_usb_find_cmdline_value(
            source,
            (usize) amount,
            "androidboot.serialno",
            output,
            capacity
        );

        if (found) {
            return tf_usb_serial_valid(
                output
            );
        }
    }

    char android_dt_dir[512];

    if (
        !tf_usb_android_dt_directory(
            android_dt_dir,
            sizeof(android_dt_dir)
        )
    ) {
        return 0;
    }

    char serial_path[640];

    if (
        !tf_usb_join_path(
            android_dt_dir,
            "serialno",
            serial_path,
            sizeof(serial_path)
        )
    ) {
        return 0;
    }

    amount = tf_read_path(
        serial_path,
        source,
        sizeof(source)
    );

    if (amount <= 0) {
        return 0;
    }

    usize end = 0;

    while (
        end < (usize) amount
        && source[end] != '\0'
        && source[end] != '\n'
        && source[end] != '\r'
    ) {
        end++;
    }

    if (
        end == 0
        || !tf_usb_copy_span(
            source,
            0,
            end,
            output,
            capacity
        )
    ) {
        return 0;
    }

    return tf_usb_serial_valid(
        output
    );
}


static int tf_recovery_adbd_poll_alive(void) {
    if (
        !tf_recovery_adbd_started
        || tf_recovery_adbd_pid <= 0
    ) {
        return 0;
    }

    int child_status = 0;

    long wait_result = tf_syscall4(
        SYS_WAIT4,
        tf_recovery_adbd_pid,
        (long) &child_status,
        TREEFORGE_WAIT_WNOHANG,
        0
    );

    if (wait_result == 0) {
        return 1;
    }

    if (
        wait_result
        == tf_recovery_adbd_pid
    ) {
        tf_recovery_adbd_write_child_status(
            child_status
        );
    } else if (wait_result < 0) {
        tf_recovery_adbd_write_launch_status(
            "wait4",
            wait_result
        );
    }

    /*
     * A returned PID means the child was reaped.
     * A negative result means its lifecycle can no longer safely be
     * supervised as the expected child.
     */
    tf_recovery_adbd_started = 0;
    tf_recovery_adbd_pid = -1;
    tf_recovery_adb_functionfs_descriptors_ready = 0;

    return 0;
}


static void tf_recovery_adb_deactivate_gadget(void) {
    /*
     * Use the exact canonical Recovery INIT UDC-unbind value.
     *
     * Do not remove f1 until the gadget is known to be unbound.
     */
    if (
        tf_recovery_adb_gadget_bound
    ) {
        if (
            tf_usb_write_path_checked(
                TREEFORGE_RECOVERY_USB_UDC_PATH,
                TREEFORGE_RECOVERY_USB_UNBIND_VALUE
            )
        ) {
            tf_recovery_adb_gadget_bound = 0;
        }
    }

    if (
        !tf_recovery_adb_gadget_bound
        && tf_recovery_adb_function_linked
    ) {
        long unlink_result = tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_ADB_FUNCTION_LINK_PATH,
            0
        );

        if (
            unlink_result == 0
            || unlink_result
                == -TF_USB_ERRNO_ENOENT
        ) {
            tf_recovery_adb_function_linked = 0;
        }
    }

    tf_recovery_adbd_update_status();
}


static int tf_recovery_functionfs_provider_ready(void) {
    char value[128];

    long amount = tf_read_path(
        TREEFORGE_RECOVERY_ADBD_FUNCTIONFS_STATUS_PATH,
        value,
        sizeof(value)
    );

    if (amount <= 0) {
        return 0;
    }

    /*
     * The standalone TreeForge adbd provider emits:
     *
     *   stage=descriptors-ready
     *   errno=0
     *
     * immediately after FunctionFS accepts both its descriptors and
     * strings. That is the same AOSP boundary that ordinarily publishes
     * sys.usb.ffs.ready=1 through Android's property service.
     *
     * The provider can immediately advance through the bulk endpoint
     * opens, so the persistent status may instead already contain:
     *
     *   stage=success
     *   errno=0
     *
     * which is strictly later and therefore also proves descriptor
     * readiness.
     */
    usize first_end = 0;

    while (
        first_end < (usize) amount
        && value[first_end] != '\n'
        && value[first_end] != '\r'
    ) {
        first_end++;
    }

    int ready_stage = (
        tf_usb_span_equals(
            value,
            0,
            first_end,
            "stage=descriptors-ready"
        )
        || tf_usb_span_equals(
            value,
            0,
            first_end,
            "stage=success"
        )
    );

    if (!ready_stage) {
        return 0;
    }

    usize position = first_end;

    while (
        position < (usize) amount
        && (
            value[position] == '\n'
            || value[position] == '\r'
        )
    ) {
        position++;
    }

    usize second_end = position;

    while (
        second_end < (usize) amount
        && value[second_end] != '\n'
        && value[second_end] != '\r'
    ) {
        second_end++;
    }

    return tf_usb_span_equals(
        value,
        position,
        second_end,
        "errno=0"
    );
}


static int tf_recovery_functionfs_kernel_ready(void) {
    char value[32];

    long amount = tf_read_path(
        TREEFORGE_RECOVERY_ADB_FFS_READY_PATH,
        value,
        sizeof(value)
    );

    if (amount <= 0) {
        return 0;
    }

    for (
        long index = 0;
        index < amount;
        index++
    ) {
        if (
            value[index] == ' '
            || value[index] == '\t'
            || value[index] == '\n'
            || value[index] == '\r'
        ) {
            continue;
        }

        return (
            value[index] == '1'
        );
    }

    return 0;
}


static int tf_recovery_functionfs_ready(void) {
    /*
     * Prefer direct provider evidence from the process that actually
     * writes the FunctionFS descriptors. Retain the configfs signal as
     * an independent kernel-side acceptance path on kernels that expose
     * it as expected.
     */
    return (
        tf_recovery_functionfs_provider_ready()
        || tf_recovery_functionfs_kernel_ready()
    );
}


static int tf_recovery_wait_for_functionfs_ready(void) {
    tf_recovery_adb_functionfs_descriptors_ready = 0;

    for (
        int attempt = 0;
        attempt
            < TREEFORGE_RECOVERY_ADB_READY_POLL_COUNT;
        attempt++
    ) {
        if (
            !tf_recovery_adbd_poll_alive()
        ) {
            tf_recovery_adb_deactivate_gadget();

            return 0;
        }

        if (
            tf_recovery_functionfs_ready()
        ) {
            tf_recovery_adb_functionfs_descriptors_ready = 1;

            tf_recovery_adbd_update_status();

            return 1;
        }

        tf_recovery_ui_sleep_ms(
            TREEFORGE_RECOVERY_ADB_READY_POLL_MS
        );
    }

    tf_recovery_adbd_update_status();

    return 0;
}


static int tf_recovery_link_adb_function(void) {
    /*
     * Ensure stale, unbound state cannot turn EEXIST into a false
     * successful activation.
     */
    long unlink_result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_ADB_FUNCTION_LINK_PATH,
        0
    );

    if (
        unlink_result != 0
        && unlink_result
            != -TF_USB_ERRNO_ENOENT
    ) {
        return 0;
    }

    long link_result = tf_syscall3(
        SYS_SYMLINKAT,
        (long)
            TREEFORGE_RECOVERY_ADB_FUNCTION_TARGET,
        AT_FDCWD,
        (long)
            TREEFORGE_RECOVERY_ADB_FUNCTION_LINK_PATH
    );

    if (link_result != 0) {
        return 0;
    }

    tf_recovery_adb_function_linked = 1;

    return 1;
}


static int tf_recovery_activate_adb_usb(void) {
    if (
        !tf_recovery_adb_usb_scaffold_ready
        || !tf_recovery_adbd_started
    ) {
        return 0;
    }

    if (
        !tf_recovery_wait_for_functionfs_ready()
    ) {
        return 0;
    }

    if (
        !tf_recovery_adbd_poll_alive()
    ) {
        tf_recovery_adb_deactivate_gadget();

        return 0;
    }

    char serial[256];

    if (
        !tf_recovery_runtime_serial(
            serial,
            sizeof(serial)
        )
    ) {
        tf_recovery_adbd_update_status();

        return 0;
    }

    /*
     * These values are not device constants in the generic runtime.
     * The macros are generated from canonical Parsing evidence by
     * AndroidBootstrapRecoveryUsbIdentityBuilder.
     */
    if (
        !tf_usb_write_path_checked(
            "/config/usb_gadget/g1/idVendor",
            TREEFORGE_RECOVERY_USB_VENDOR_ID
        )
        || !tf_usb_write_path_checked(
            "/config/usb_gadget/g1/idProduct",
            TREEFORGE_RECOVERY_USB_ADB_PRODUCT_ID
        )
        || !tf_usb_write_path_checked(
            "/config/usb_gadget/g1/strings/0x409/manufacturer",
            TREEFORGE_RECOVERY_USB_MANUFACTURER
        )
        || !tf_usb_write_path_checked(
            "/config/usb_gadget/g1/strings/0x409/product",
            TREEFORGE_RECOVERY_USB_PRODUCT
        )
        || !tf_usb_write_path_checked(
            "/config/usb_gadget/g1/strings/0x409/serialnumber",
            serial
        )
        || !tf_usb_write_path_checked(
            "/config/usb_gadget/g1/configs/b.1/MaxPower",
            TREEFORGE_RECOVERY_USB_MAX_POWER
        )
        || !tf_usb_write_path_checked(
            "/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration",
            TREEFORGE_RECOVERY_USB_ADB_CONFIGURATION
        )
    ) {
        tf_recovery_adbd_update_status();

        return 0;
    }

    if (
        !tf_recovery_link_adb_function()
    ) {
        tf_recovery_adbd_update_status();

        return 0;
    }

    if (
        !tf_recovery_adbd_poll_alive()
    ) {
        tf_recovery_adb_deactivate_gadget();

        return 0;
    }

    if (
        !tf_usb_write_path_checked(
            TREEFORGE_RECOVERY_USB_UDC_PATH,
            TREEFORGE_RECOVERY_USB_CONTROLLER
        )
    ) {
        tf_recovery_adb_deactivate_gadget();

        return 0;
    }

    tf_recovery_adb_gadget_bound = 1;

    tf_recovery_adbd_update_status();

    return 1;
}


/*
 * Called from Recovery's existing UI poll loop.
 *
 * A dead adbd is reaped and its gadget is unbound. Local Recovery stays
 * operational; TreeForge does not automatically restart the daemon.
 */
static void tf_recovery_adbd_maintain(void) {
    if (
        tf_recovery_adbd_started
    ) {
        if (
            !tf_recovery_adbd_poll_alive()
        ) {
            tf_recovery_adb_deactivate_gadget();

            return;
        }

        /*
         * The standalone provider may publish its FunctionFS descriptors
         * after the initial bounded activation wait has expired.
         *
         * Recovery's UI loop is already the long-lived lifecycle owner.
         * Detect that one-way readiness transition here and finish the
         * existing activation sequence with the already-running daemon.
         *
         * Gate this on descriptors_ready == 0 so a later VID/PID,
         * function-link, or UDC failure remains stable diagnostic
         * evidence instead of being retried every 25 ms.
         */
        if (
            !tf_recovery_adb_gadget_bound
            && !tf_recovery_adb_functionfs_descriptors_ready
            && tf_recovery_functionfs_ready()
        ) {
            tf_recovery_activate_adb_usb();
        }

        return;
    }

    if (
        tf_recovery_adb_gadget_bound
        || tf_recovery_adb_function_linked
    ) {
        tf_recovery_adb_deactivate_gadget();
    }
}


/*
 * Boot-menu Recovery ADB preflight handoff.
 *
 * The preflight Recovery process is a child of the TreeForge PID-1
 * dispatcher. Its standalone adbd is therefore reparented to PID 1 when
 * preflight exits. The dispatcher then execs the normal Recovery runtime
 * in that same PID, preserving the parent/child relationship required by
 * the existing wait4-based supervision code.
 *
 * /dev is boot-local and survives the dispatcher -> Recovery exec
 * transition, making it suitable for this transient handoff without
 * creating stale state across boots.
 */
static void tf_recovery_write_adb_preflight_handoff(
    int activated
) {
    if (
        !tf_recovery_adbd_started
        || tf_recovery_adbd_pid <= 0
    ) {
        return;
    }

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_ADB_HANDOFF_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return;
    }

    /*
     * Line 1: standalone adbd PID.
     * Line 2: complete USB gadget activation state.
     */
    tf_recovery_adbd_write_u64(
        fd,
        (u64) tf_recovery_adbd_pid
    );

    tf_usb_write_all(
        fd,
        "\n"
    );

    tf_usb_write_all(
        fd,
        activated
        ? "1\n"
        : "0\n"
    );

    tf_close(
        fd
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );
}


static int tf_recovery_adopt_adb_preflight(void) {
    char state[96];

    long amount = tf_read_path(
        TREEFORGE_RECOVERY_ADB_HANDOFF_PATH,
        state,
        sizeof(state)
    );

    if (amount <= 0) {
        return 0;
    }

    /*
     * Consume the boot-local handoff exactly once.
     */
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_RECOVERY_ADB_HANDOFF_PATH,
        0
    );

    u64 pid_value = 0;

    if (
        !tf_parse_u64(
            state,
            &pid_value
        )
        || pid_value == 0
        || pid_value > 0x7fffffffffffffffULL
    ) {
        return 0;
    }

    usize second_line = 0;

    while (
        second_line < (usize) amount
        && state[second_line] != '\n'
    ) {
        second_line++;
    }

    u64 activated_value = 0;

    if (
        second_line < (usize) amount
        && state[second_line] == '\n'
    ) {
        second_line++;

        if (second_line < (usize) amount) {
            tf_parse_u64(
                state + second_line,
                &activated_value
            );
        }
    }

    tf_recovery_adb_usb_scaffold_ready = 1;
    tf_recovery_adbd_started = 1;
    tf_recovery_adbd_pid = (long) pid_value;

    if (activated_value == 1) {
        tf_recovery_adb_functionfs_descriptors_ready = 1;
        tf_recovery_adb_function_linked = 1;
        tf_recovery_adb_gadget_bound = 1;
    } else {
        /*
         * The preflight may have timed out waiting for FunctionFS while
         * adbd remained alive. Preserve that daemon and allow normal
         * Recovery to continue the existing activation state machine.
         */
        tf_recovery_adb_functionfs_descriptors_ready = 0;
        tf_recovery_adb_function_linked = 0;
        tf_recovery_adb_gadget_bound = 0;
    }

    /*
     * Confirm the reparented daemon is really our live child before
     * accepting the handoff. Failure falls back to Recovery's normal
     * standalone-adbd launch path.
     */
    if (!tf_recovery_adbd_poll_alive()) {
        tf_recovery_adb_deactivate_gadget();

        return 0;
    }

    tf_recovery_adbd_update_status();

    return 1;
}


__attribute__((noreturn))
void _start(void) {
    /*
     * The executable was entered through retained initramfs FD 96.
     * Once exec succeeds, Recovery no longer needs to retain its own
     * backing descriptor.
     */
    tf_close(
        96
    );

    /*
     * One-shot boot-menu ADB preflight.
     *
     * The dispatcher creates this marker only after the user explicitly
     * selects TreeForge Recovery. Remove it before doing any work so an
     * error or failed exec can never turn the subsequent normal Recovery
     * entry into another preflight.
     */
    char preflight_request[8];

    if (
        tf_read_path(
            TREEFORGE_RECOVERY_ADB_PREFLIGHT_REQUEST_PATH,
            preflight_request,
            sizeof(preflight_request)
        ) > 0
    ) {
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_ADB_PREFLIGHT_REQUEST_PATH,
            0
        );

        /*
         * The preflight needs no retained dispatcher descriptors.
         * Close the inherited private range before forking standalone
         * adbd so the daemon cannot pin TreeForge transition/runtime FDs.
         */
        for (
            long fd = 3;
            fd < 256;
            fd++
        ) {
            tf_close(
                fd
            );
        }

        tf_setup_recovery_adb_usb_scaffold();

        int activated = 0;

        if (
            tf_recovery_adb_usb_scaffold_ready
            && tf_start_recovery_adbd()
        ) {
            activated = (
                tf_recovery_activate_adb_usb()
            );
        }

        /*
         * A still-live adbd is useful even when the first descriptor
         * readiness window has not completed. Hand it to normal Recovery,
         * which can continue activation without restarting the daemon.
         */
        if (tf_recovery_adbd_started) {
            tf_recovery_write_adb_preflight_handoff(
                activated
            );
        }

        tf_syscall1(
            SYS_EXIT,
            0
        );

        for (;;) {
        }
    }

    int adb_preflight_adopted = (
        tf_recovery_adopt_adb_preflight()
    );

    tf_collect_inventory(
        &tf_recovery_inventory
    );

    /*
     * TreeForge Virtual A/B provider acceptance is explicitly opt-in.
     *
     * Never execute an experimental runtime provider automatically on
     * every Recovery boot. Consume the request before launching so even
     * a crashing provider cannot create a persistent boot loop.
     */
    if (
        tf_recovery_ui_probe_readable_path(
            TREEFORGE_RECOVERY_VABC_PROBE_REQUEST_PATH
        )
    ) {
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long)
                TREEFORGE_RECOVERY_VABC_PROBE_REQUEST_PATH,
            0
        );

        tf_recovery_run_vabc_probe(
            &tf_recovery_inventory
        );
    }

    /*
     * Prepare the kernel USB/FunctionFS surface independently from adbd.
     *
     * A successful boot-menu preflight leaves this exact mount/configfs
     * topology alive across the dispatcher -> Recovery exec boundary.
     * Do not remount or recreate it when Recovery adopted that preflight.
     */
    if (!adb_preflight_adopted) {
        tf_setup_recovery_adb_usb_scaffold();
    }

    /*
     * Preserve the existing automated hardware-test controls.
     *
     * If either request exists, execute exactly the requested
     * read-only/no-write backend operation, persist the report, and
     * reboot as before.
     */
    int automated_request = (
        tf_recovery_ui_probe_readable_path(
            TREEFORGE_RECOVERY_READ_PROBE_REQUEST_PATH
        )
        || tf_recovery_ui_probe_readable_path(
            TREEFORGE_RECOVERY_LP_READ_PROBE_REQUEST_PATH
        )
        || tf_recovery_ui_probe_readable_path(
            TREEFORGE_RECOVERY_FLASH_PLAN_REQUEST_PATH
        )
    );

    if (automated_request) {
        tf_run_requested_lp_read_probe(
            &tf_recovery_lp_inventory,
            &tf_recovery_lp_read_probe
        );

        tf_run_requested_read_probe(
            &tf_recovery_inventory,
            &tf_recovery_read_probe
        );

        tf_run_requested_flash_plan(
            &tf_recovery_inventory,
            &tf_recovery_flash_plan
        );

        tf_emit_inventory(
            &tf_recovery_inventory
        );

        /*
         * The ordinary runtime report is replaced on every Recovery
         * startup. Preserve a dedicated one-shot LP probe result before
         * the automated reboot so it remains retrievable afterward.
         */
        tf_emit_lp_read_probe_report(
            &tf_recovery_lp_read_probe
        );

        tf_reboot_after_inventory();

        for (;;) {
        }
    }

    /*
     * Interactive Recovery exposes a boot-local streaming endpoint.
     * Failure leaves streaming plans unavailable but does not regress
     * the already-accepted regular-file staging fallback.
     */
    tf_recovery_prepare_stream_fifo();

    /*
     * The automated Recovery test path above deliberately runs without
     * adbd. Only an interactive Recovery session starts the standalone
     * daemon.
     *
     * FunctionFS linking and UDC binding are attempted only after
     * standalone adbd reaches direct kernel-reported readiness.
     */
    if (tf_recovery_adb_usb_scaffold_ready) {
        if (adb_preflight_adopted) {
            /*
             * The boot-menu preflight already owns the standalone adbd.
             *
             * If it completed USB activation, nothing further is needed.
             * If descriptor readiness had not completed before the
             * preflight returned, continue activation here with the same
             * daemon instead of launching a second adbd.
             */
            if (
                tf_recovery_adbd_started
                && !tf_recovery_adb_gadget_bound
            ) {
                tf_recovery_activate_adb_usb();
            }
        } else if (tf_start_recovery_adbd()) {
            tf_recovery_activate_adb_usb();
        }
    }

    /*
     * Direct boot-menu entry is interactive.
     *
     * Persist the initial inventory before presenting the UI so
     * diagnostics remain available even if rendering/input later
     * fails.
     */
    tf_emit_inventory(
        &tf_recovery_inventory
    );

    tf_recovery_ui_run();
}
'''

    @staticmethod
    def _elf_machine(
        data: bytes
    ) -> int:
        if (
            len(data) < 20
            or data[:4] != b"\x7fELF"
        ):
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime requires canonical ELF init"
            )

        if data[4] != 2:
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime currently requires ELF64"
            )

        if data[5] != 1:
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime currently requires "
                "little-endian canonical init"
            )

        return struct.unpack_from(
            "<H",
            data,
            18,
        )[0]

    @staticmethod
    def _compiler() -> Path:
        explicit = os.environ.get(
            "TREEFORGE_CLANG"
        )

        if explicit:
            candidate = (
                Path(explicit)
                .expanduser()
                .resolve()
            )

            if not candidate.is_file():
                raise AndroidBootstrapRecoveryRuntimeError(
                    "TREEFORGE_CLANG does not reference an existing file: "
                    f"{candidate}"
                )

            return candidate

        discovered = shutil.which(
            "clang"
        )

        if discovered is None:
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime requires clang. "
                "Install clang or set TREEFORGE_CLANG."
            )

        return Path(
            discovered
        ).resolve()

    @classmethod
    def build(
        cls,
        *,
        canonical_init: bytes,
        partition_manifest: AndroidBootstrapRecoveryPartitionManifest,
        usb_identity: AndroidBootstrapRecoveryUsbIdentity,
        output_root: Path,
    ) -> AndroidBootstrapRecoveryRuntimeBuild:
        if not isinstance(
            partition_manifest,
            AndroidBootstrapRecoveryPartitionManifest,
        ):
            raise TypeError(
                "partition_manifest must be an "
                "AndroidBootstrapRecoveryPartitionManifest"
            )

        if not isinstance(
            usb_identity,
            AndroidBootstrapRecoveryUsbIdentity,
        ):
            raise TypeError(
                "usb_identity must be an "
                "AndroidBootstrapRecoveryUsbIdentity"
            )

        if (
            usb_identity.parsing
            is not partition_manifest.parsing
        ):
            raise ValueError(
                "Recovery USB identity and partition manifest "
                "must retain the exact same canonical Parsing "
                "identity"
            )

        if not isinstance(
            output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        machine = cls._elf_machine(
            canonical_init
        )

        if (
            machine
            != cls.ELF_MACHINE_AARCH64
        ):
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime does not yet have a "
                "freestanding provider for canonical ELF machine "
                f"{machine}"
            )

        target_triple = (
            "aarch64-linux-gnu"
        )

        compiler = cls._compiler()

        output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_path = (
            output_root
            / "treeforge-recovery.c"
        )

        executable_path = (
            output_root
            / "treeforge-recovery"
        )

        manifest_source = (
            render_recovery_partition_manifest_c(
                partition_manifest
            )
        )

        usb_identity_source = (
            render_recovery_usb_identity_c(
                usb_identity
            )
        )

        manifest_marker = (
            "/* TREEFORGE_RECOVERY_CANONICAL_MANIFEST */"
        )

        if (
            cls._SOURCE.count(
                manifest_marker
            )
            != 1
        ):
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime canonical manifest "
                "insertion marker is not unique"
            )

        source = cls._SOURCE.replace(
            manifest_marker,
            manifest_source,
            1,
        )

        if manifest_marker in source:
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime canonical manifest "
                "was not fully materialized"
            )

        usb_identity_marker = (
            "/* TREEFORGE_RECOVERY_CANONICAL_USB_IDENTITY */"
        )

        if (
            source.count(
                usb_identity_marker
            )
            != 1
        ):
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime canonical USB "
                "identity insertion marker is not unique"
            )

        source = source.replace(
            usb_identity_marker,
            usb_identity_source,
            1,
        )

        if usb_identity_marker in source:
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime canonical USB "
                "identity was not fully materialized"
            )

        source_path.write_text(
            source,
            encoding="utf-8",
        )

        executable_path.unlink(
            missing_ok=True
        )

        command = (
            str(compiler),
            f"--target={target_triple}",
            "-Os",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-fno-pic",
            "-nostdlib",
            "-static",
            "-fuse-ld=lld",
            "-Wl,-e,_start",
            "-Wl,--build-id=none",
            "-Wl,-z,max-page-size=4096",
            str(source_path),
            "-o",
            str(executable_path),
        )

        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if completed.returncode != 0:
            raise AndroidBootstrapRecoveryRuntimeError(
                "unable to build TreeForge recovery runtime:\n"
                + completed.stderr.decode(
                    "utf-8",
                    errors="replace",
                )
            )

        if not executable_path.is_file():
            raise AndroidBootstrapRecoveryRuntimeError(
                "clang completed without producing the "
                "TreeForge recovery runtime"
            )

        executable = (
            executable_path.read_bytes()
        )

        if (
            cls._elf_machine(
                executable
            )
            != machine
        ):
            raise AndroidBootstrapRecoveryRuntimeError(
                "TreeForge recovery runtime architecture does not "
                "match canonical init architecture"
            )

        executable_path.chmod(
            0o755
        )

        return AndroidBootstrapRecoveryRuntimeBuild(
            source_path=source_path,
            executable_path=executable_path,
            compiler_path=compiler,
            elf_machine=machine,
            target_triple=target_triple,
        )


__all__ = (
    "AndroidBootstrapRecoveryRuntimeBuild",
    "AndroidBootstrapRecoveryRuntimeBuilder",
    "AndroidBootstrapRecoveryRuntimeError",
)
