from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import struct
import subprocess
import tomllib


class AndroidBootstrapEarlyDispatcherError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEarlyDispatcherBuild:
    source_path: Path
    executable_path: Path
    compiler_path: Path
    elf_machine: int
    target_triple: str


class AndroidBootstrapEarlyDispatcherBuilder:
    """
    Build TreeForge's early-boot interactive dispatcher.

    The dispatcher first runs as the kernel's initial PID 1 and
    transparently enters the exact preserved canonical Android
    FirstStageMain. TreeForge resumes at the canonical first-stage ->
    selinux_setup transition, after Android has established its
    first-stage kernel-module and /dev environment.

    At that boundary the dispatcher provides the early boot menu and
    then either:

      - continues Android's exact selinux_setup transition;
      - requests a bootloader reboot; or
      - requests a recovery reboot.

    It is deliberately freestanding and uses Linux syscalls directly.
    No Android property service, libc, shell, or AOSP checkout is
    required at runtime or build time.

    Compiler selection is a generic host-provider concern:
      TREEFORGE_CLANG may explicitly select clang;
      otherwise the first host `clang` on PATH is used.
    """

    ELF_MACHINE_AARCH64 = 183

    _SOURCE = r'''
typedef unsigned long usize;
typedef long ssize;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef int s32;


/*
 * Minimal freestanding memory primitives.
 *
 * Clang may lower aggregate copies/initialization to these routines
 * even for -ffreestanding -nostdlib code. TreeForge therefore owns
 * these tiny compiler-runtime providers rather than depending on libc.
 *
 * Volatile byte accesses intentionally keep these implementations from
 * themselves being rewritten into calls to the same libc primitives.
 */

void *memcpy(
    void *destination,
    const void *source,
    usize count
) {
    volatile unsigned char *output = (
        (volatile unsigned char *)
        destination
    );

    const volatile unsigned char *input = (
        (const volatile unsigned char *)
        source
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
        (volatile unsigned char *)
        destination
    );

    const volatile unsigned char *input = (
        (const volatile unsigned char *)
        source
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
        (volatile unsigned char *)
        destination
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
        (const volatile unsigned char *)
        left
    );

    const volatile unsigned char *right_bytes = (
        (const volatile unsigned char *)
        right
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
#define SYS_IOCTL 29
#define SYS_MKNODAT 33
#define SYS_MKDIRAT 34
#define SYS_UNLINKAT 35
#define SYS_UMOUNT2 39
#define SYS_MOUNT 40
#define SYS_OPENAT 56
#define SYS_CLOSE 57
#define SYS_GETDENTS64 61
#define SYS_READ 63
#define SYS_WRITE 64
#define SYS_SYNC 81
#define SYS_EXIT 93
#define SYS_NANOSLEEP 101
#define SYS_REBOOT 142
#define SYS_MUNMAP 215
#define SYS_EXECVE 221
#define SYS_MMAP 222

#define AT_FDCWD (-100)
#define AT_REMOVEDIR 0x200

#define O_RDONLY 0
#define O_WRONLY 1
#define O_RDWR 2
#define O_CREAT 0100
#define O_TRUNC 01000
#define O_NONBLOCK 04000
#define O_DIRECTORY 040000

#define TREEFORGE_TRANSITION_FD 99
#define TREEFORGE_ADB_DEBUG_FD 98
#define TREEFORGE_USERDEBUG_SEPOLICY_FD 97
#define TREEFORGE_RECOVERY_FD 96

/*
 * Generic retained Recovery-runtime descriptor range.
 *
 * Bootstrap generates the concrete provider population from the
 * validated runtime-provider rootfs. These descriptors survive
 * Android FirstStageMain / FreeRamdisk and are consumed only when
 * TreeForge Recovery is selected.
 */
#define TREEFORGE_RECOVERY_RUNTIME_FD_BASE 64
#define TREEFORGE_RECOVERY_RUNTIME_FD_CAPACITY 32
#define TREEFORGE_RECOVERY_RUNTIME_FILE_COUNT \
    __TREEFORGE_RECOVERY_RUNTIME_FILE_COUNT__

struct tf_recovery_runtime_file {
    const char *source_path;
    const char *destination_path;
    long mode;
};

static const struct tf_recovery_runtime_file
tf_recovery_runtime_files[] = {
__TREEFORGE_RECOVERY_RUNTIME_FILE_TABLE__
};

#define TREEFORGE_ROOT_EXEC_ENVIRONMENT_FAILED (-1)
#define TREEFORGE_ROOT_EXEC_DEBUG_RAMDISK_FAILED (-2)
#define TREEFORGE_ROOT_EXEC_SELINUX_FAILED (-3)

#define PROT_READ 1
#define PROT_WRITE 2

#define MAP_SHARED 1

#define S_IFCHR 0020000

#define MS_RDONLY 1
#define MNT_DETACH 2

#define LINUX_REBOOT_MAGIC1 0xfee1deadUL
#define LINUX_REBOOT_MAGIC2 672274793UL
#define LINUX_REBOOT_CMD_RESTART 0x01234567UL
#define LINUX_REBOOT_CMD_RESTART2 0xa1b2c3d4UL

#define EV_KEY 1
#define KEY_VOLUMEDOWN 114
#define KEY_VOLUMEUP 115
#define KEY_POWER 116

#define INPUT_COUNT 32

#define MENU_TIMEOUT_MS 10000
#define POLL_INTERVAL_MS 25

#define TREEFORGE_PSTORE_MAX_RECORDS 16
#define TREEFORGE_PSTORE_NAME_CAPACITY 96
#define TREEFORGE_PSTORE_RECORD_CAPACITY 8192

struct tf_timespec {
    long tv_sec;
    long tv_nsec;
};

struct tf_input_event {
    long tv_sec;
    long tv_usec;
    u16 type;
    u16 code;
    s32 value;
};

struct tf_linux_dirent64 {
    u64 d_ino;
    long long d_off;
    u16 d_reclen;
    unsigned char d_type;
    char d_name[];
};


struct tf_pstore_record {
    char name[
        TREEFORGE_PSTORE_NAME_CAPACITY
    ];

    char data[
        TREEFORGE_PSTORE_RECORD_CAPACITY
        + 1
    ];

    usize size;
    int readable;
    int truncated;
};


struct tf_pstore_snapshot {
    int available;
    int record_count;
    int records_omitted;
    int enumeration_error;

    struct tf_pstore_record records[
        TREEFORGE_PSTORE_MAX_RECORDS
    ];
};


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

static long tf_syscall6(
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

static long tf_syscall4(
    long number,
    long a0,
    long a1,
    long a2,
    long a3
) {
    return tf_syscall6(
        number,
        a0,
        a1,
        a2,
        a3,
        0,
        0
    );
}

static long tf_syscall3(
    long number,
    long a0,
    long a1,
    long a2
) {
    return tf_syscall6(
        number,
        a0,
        a1,
        a2,
        0,
        0,
        0
    );
}

static long tf_syscall2(
    long number,
    long a0,
    long a1
) {
    return tf_syscall6(
        number,
        a0,
        a1,
        0,
        0,
        0,
        0
    );
}

static long tf_syscall1(
    long number,
    long a0
) {
    return tf_syscall6(
        number,
        a0,
        0,
        0,
        0,
        0,
        0
    );
}

static usize tf_strlen(
    const char *value
) {
    usize length = 0;

    while (value[length] != '\0') {
        length++;
    }

    return length;
}


static long tf_ioctl(
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

static void tf_write_all(
    long fd,
    const char *value
) {
    if (fd < 0) {
        return;
    }

    usize remaining = tf_strlen(
        value
    );

    const char *cursor = value;

    while (remaining != 0) {
        long written = tf_syscall3(
            SYS_WRITE,
            fd,
            (long) cursor,
            (long) remaining
        );

        if (written <= 0) {
            return;
        }

        cursor += written;
        remaining -= (usize) written;
    }
}

static int tf_write_bytes(
    long fd,
    const unsigned char *value,
    usize size
) {
    if (fd < 0) {
        return 0;
    }

    usize remaining = size;
    const unsigned char *cursor = value;

    while (remaining != 0) {
        long written = tf_syscall3(
            SYS_WRITE,
            fd,
            (long) cursor,
            (long) remaining
        );

        if (written <= 0) {
            return 0;
        }

        cursor += written;
        remaining -= (usize) written;
    }

    return 1;
}


static int tf_copy_fd_to_path(
    long source_fd,
    const char *destination_path,
    long mode
) {
    if (source_fd < 0) {
        return 0;
    }

    long destination_fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) destination_path,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        mode
    );

    if (destination_fd < 0) {
        return 0;
    }

    unsigned char buffer[4096];

    for (;;) {
        long amount = tf_syscall3(
            SYS_READ,
            source_fd,
            (long) buffer,
            (long) sizeof(buffer)
        );

        if (amount < 0) {
            tf_close(
                destination_fd
            );

            tf_syscall3(
                SYS_UNLINKAT,
                AT_FDCWD,
                (long) destination_path,
                0
            );

            return 0;
        }

        if (amount == 0) {
            break;
        }

        if (
            !tf_write_bytes(
                destination_fd,
                buffer,
                (usize) amount
            )
        ) {
            tf_close(
                destination_fd
            );

            tf_syscall3(
                SYS_UNLINKAT,
                AT_FDCWD,
                (long) destination_path,
                0
            );

            return 0;
        }
    }

    tf_close(
        destination_fd
    );

    return 1;
}


static void tf_close_recovery_runtime_fds(void) {
    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_RUNTIME_FILE_COUNT;
        index++
    ) {
        tf_close(
            TREEFORGE_RECOVERY_RUNTIME_FD_BASE
            + index
        );
    }
}


static int tf_create_parent_directories(
    const char *path
) {
    if (
        !path
        || path[0] != '/'
    ) {
        return 0;
    }

    char buffer[512];

    usize length = tf_strlen(
        path
    );

    if (
        length == 0
        || length >= sizeof(buffer)
    ) {
        return 0;
    }

    for (
        usize index = 0;
        index <= length;
        index++
    ) {
        buffer[index] = path[index];
    }

    /*
     * Existing directories are harmless. The final destination open
     * performed by tf_copy_fd_to_path() is the authoritative test.
     */
    for (
        usize index = 1;
        index < length;
        index++
    ) {
        if (buffer[index] != '/') {
            continue;
        }

        buffer[index] = '\0';

        tf_syscall3(
            SYS_MKDIRAT,
            AT_FDCWD,
            (long) buffer,
            0755
        );

        buffer[index] = '/';
    }

    return 1;
}


static int tf_realize_recovery_runtime_files(void) {
    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_RUNTIME_FILE_COUNT;
        index++
    ) {
        const struct tf_recovery_runtime_file *entry = (
            &tf_recovery_runtime_files[index]
        );

        if (
            !entry->destination_path
            || !tf_create_parent_directories(
                entry->destination_path
            )
        ) {
            return 0;
        }

        if (
            !tf_copy_fd_to_path(
                TREEFORGE_RECOVERY_RUNTIME_FD_BASE
                + index,
                entry->destination_path,
                entry->mode
            )
        ) {
            return 0;
        }
    }

    return 1;
}


static int tf_realize_debug_ramdisk(void) {
    /*
     * Android may or may not already have created this directory at
     * TreeForge's post-FirstStageMain boundary. An existing directory
     * is harmless; subsequent file creation is the authoritative test.
     */
    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/debug_ramdisk",
        0755
    );

    if (
        !tf_copy_fd_to_path(
            TREEFORGE_ADB_DEBUG_FD,
            "/debug_ramdisk/adb_debug.prop",
            0644
        )
    ) {
        return 0;
    }

    if (
        !tf_copy_fd_to_path(
            TREEFORGE_USERDEBUG_SEPOLICY_FD,
            "/debug_ramdisk/userdebug_plat_sepolicy.cil",
            0644
        )
    ) {
        /*
         * Do not leave a partially realized TreeForge debug ramdisk.
         */
        tf_syscall3(
            SYS_UNLINKAT,
            AT_FDCWD,
            (long) "/debug_ramdisk/adb_debug.prop",
            0
        );

        return 0;
    }

    return 1;
}


static int tf_environment_key_matches(
    const char *entry,
    const char *key
) {
    if (
        !entry
        || !key
    ) {
        return 0;
    }

    usize index = 0;

    while (key[index] != '\0') {
        if (
            entry[index]
            != key[index]
        ) {
            return 0;
        }

        index++;
    }

    return entry[index] == '=';
}


static int tf_build_root_environment(
    char **envp,
    char **destination,
    usize capacity
) {
    /*
     * Preserve Android's inherited first-stage environment, replacing
     * any pre-existing INIT_FORCE_DEBUGGABLE assignment with the exact
     * TreeForge rooted-boot value.
     *
     * The caller owns destination storage. Capacity includes the final
     * NULL entry.
     */
    if (
        !destination
        || capacity < 2
    ) {
        return 0;
    }

    usize output_index = 0;

    if (envp) {
        for (
            usize input_index = 0;
            envp[input_index] != 0;
            input_index++
        ) {
            if (
                tf_environment_key_matches(
                    envp[input_index],
                    "INIT_FORCE_DEBUGGABLE"
                )
            ) {
                continue;
            }

            /*
             * Reserve two additional slots:
             *   INIT_FORCE_DEBUGGABLE=true
             *   NULL
             */
            if (
                output_index + 2
                >= capacity
            ) {
                return 0;
            }

            destination[output_index] = (
                envp[input_index]
            );

            output_index++;
        }
    }

    if (
        output_index + 2
        > capacity
    ) {
        return 0;
    }

    destination[output_index] = (
        (char *) "INIT_FORCE_DEBUGGABLE=true"
    );

    output_index++;

    destination[output_index] = 0;

    return 1;
}


static int tf_exec_rooted_android(
    char **envp
) {
    /*
     * Build the rooted second-stage environment before mutating the
     * filesystem. If the inherited environment cannot be represented,
     * canonical Android remains untouched.
     */
    static char *root_environment[256];

    if (
        !tf_build_root_environment(
            envp,
            root_environment,
            sizeof(root_environment)
            / sizeof(root_environment[0])
        )
    ) {
        return TREEFORGE_ROOT_EXEC_ENVIRONMENT_FAILED;
    }

    /*
     * Recreate Android's force-debuggable first-stage result from the
     * TreeForge-retained canonical payload descriptors.
     */
    if (!tf_realize_debug_ramdisk()) {
        return TREEFORGE_ROOT_EXEC_DEBUG_RAMDISK_FAILED;
    }

    /*
     * The payload bytes have now been materialized and the TreeForge
     * dispatcher executable is already mapped. None of these retained
     * descriptors should leak into Android second stage.
     */
    tf_close(
        TREEFORGE_ADB_DEBUG_FD
    );

    tf_close(
        TREEFORGE_USERDEBUG_SEPOLICY_FD
    );

    tf_close(
        TREEFORGE_TRANSITION_FD
    );

    char *next_argv[] = {
        (char *) "/system/bin/init",
        (char *) "selinux_setup",
        0
    };

    tf_syscall3(
        SYS_EXECVE,
        (long) "/system/bin/init",
        (long) next_argv,
        (long) root_environment
    );

    /*
     * execve() only returns on failure. Remove TreeForge's temporary
     * debug payloads rather than leaving an incomplete transition
     * behind in the current boot.
     */
    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) "/debug_ramdisk/adb_debug.prop",
        0
    );

    tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) "/debug_ramdisk/userdebug_plat_sepolicy.cil",
        0
    );

    return TREEFORGE_ROOT_EXEC_SELINUX_FAILED;
}


static void tf_sleep_ms(
    long milliseconds
) {
    struct tf_timespec delay;

    delay.tv_sec = (
        milliseconds
        / 1000
    );

    delay.tv_nsec = (
        milliseconds
        % 1000
    ) * 1000000L;

    tf_syscall2(
        SYS_NANOSLEEP,
        (long) &delay,
        0
    );
}

/*
 * Linux dev_t encoding as used by new_encode_dev().
 *
 * We derive evdev major/minor numbers from sysfs rather than
 * assuming a particular event-node assignment.
 */
static unsigned long tf_makedev(
    unsigned int major_number,
    unsigned int minor_number
) {
    return (
        (
            (unsigned long)
            (
                minor_number
                & 0xffU
            )
        )
        | (
            (
                (unsigned long)
                (
                    major_number
                    & 0xfffU
                )
            )
            << 8
        )
        | (
            (
                (unsigned long)
                (
                    minor_number
                    & ~0xffU
                )
            )
            << 12
        )
        | (
            (
                (unsigned long)
                (
                    major_number
                    & ~0xfffU
                )
            )
            << 32
        )
    );
}

static long tf_mknod_path(
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


static int tf_prepare_mounts(
    int *mounted_dev,
    int *mounted_proc,
    int *mounted_sys
) {
    *mounted_dev = 0;
    *mounted_proc = 0;
    *mounted_sys = 0;

    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/dev",
        0755
    );

    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/proc",
        0755
    );

    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/sys",
        0755
    );

    /*
     * This kernel does not expose devtmpfs as a mountable filesystem
     * at the early PID-1 boundary. sysfs, however, already exposes the
     * input-device topology created by the kernel.
     */
    long result = tf_syscall6(
        SYS_MOUNT,
        (long) "sysfs",
        (long) "/sys",
        (long) "sysfs",
        0,
        0,
        0
    );

    if (result == 0) {
        *mounted_sys = 1;
    }

    result = tf_syscall6(
        SYS_MOUNT,
        (long) "proc",
        (long) "/proc",
        (long) "proc",
        0,
        0,
        0
    );

    if (result == 0) {
        *mounted_proc = 1;
    }

    /*
     * Android first-stage init normally constructs its own /dev.
     * TreeForge temporarily owns a private tmpfs /dev only while the
     * early dispatcher is active, then unmounts it before execve().
     */
    result = tf_syscall6(
        SYS_MOUNT,
        (long) "tmpfs",
        (long) "/dev",
        (long) "tmpfs",
        0,
        (long) "mode=0755",
        0
    );

    if (result == 0) {
        *mounted_dev = 1;

        tf_syscall3(
            SYS_MKDIRAT,
            AT_FDCWD,
            (long) "/dev/input",
            0755
        );

        /*
         * Standard Linux character-device identities.
         *
         * Failure to create any optional display/logging node is not
         * fatal. Input nodes are populated separately from sysfs.
         */
        tf_mknod_path(
            "/dev/null",
            S_IFCHR | 0666,
            tf_makedev(
                1,
                3
            )
        );

        tf_mknod_path(
            "/dev/kmsg",
            S_IFCHR | 0600,
            tf_makedev(
                1,
                11
            )
        );

        tf_mknod_path(
            "/dev/tty0",
            S_IFCHR | 0600,
            tf_makedev(
                4,
                0
            )
        );

        tf_mknod_path(
            "/dev/console",
            S_IFCHR | 0600,
            tf_makedev(
                5,
                1
            )
        );
    }

    return 0;
}

static void tf_cleanup_mounts(
    int mounted_dev,
    int mounted_proc,
    int mounted_sys
) {
    if (mounted_dev) {
        tf_syscall2(
            SYS_UMOUNT2,
            (long) "/dev",
            MNT_DETACH
        );
    }

    if (mounted_sys) {
        tf_syscall2(
            SYS_UMOUNT2,
            (long) "/sys",
            MNT_DETACH
        );
    }

    if (mounted_proc) {
        tf_syscall2(
            SYS_UMOUNT2,
            (long) "/proc",
            MNT_DETACH
        );
    }
}

static long tf_tty = -1;
static long tf_console = -1;
static long tf_kmsg = -1;

/*
 * Retained TreeForge DRM menu session.
 *
 * The framebuffer uses the native DRM mode coordinates exactly as
 * exposed by the kernel. No rotation or orientation policy is
 * applied here.
 */
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

        case 'I': {
            static const unsigned char rows[7] = {
                0x1f, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1f
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

        case 'Y': {
            static const unsigned char rows[7] = {
                0x11, 0x11, 0x0a, 0x04, 0x04, 0x04, 0x04
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


#define TREEFORGE_MENU_MAIN 0

static const char tf_treeforge_version[] =
    "V__TREEFORGE_VERSION__";


static int tf_menu_item_count(
    int menu_page
) {
    (void) menu_page;

    return 5;
}


static const char *tf_menu_section_title(
    int menu_page
) {
    (void) menu_page;

    return "";
}


static const char *tf_menu_item(
    int menu_page,
    int index,
    int persistent_root_installed
) {
    (void) menu_page;

    static const char *unrooted_items[5] = {
        "BOOT ANDROID (NORMAL)",
        "BOOT ROOTED ANDROID (NON PERSISTENT)",
        "INSTALL ROOT",
        "REBOOT BOOTLOADER",
        "TREEFORGE RECOVERY",
    };

    static const char *rooted_items[5] = {
        "BOOT ANDROID (ROOTED)",
        "BOOT NORMAL ANDROID (NON PERSISTENT)",
        "UNINSTALL ROOT",
        "REBOOT BOOTLOADER",
        "TREEFORGE RECOVERY",
    };

    return (
        persistent_root_installed
        ? rooted_items[index]
        : unrooted_items[index]
    );
}


static const char *tf_countdown_line(
    int seconds,
    int persistent_root_installed
) {
    if (seconds <= 0) {
        return "AUTO BOOT PAUSED BY USER INPUT";
    }

    if (persistent_root_installed) {
        switch (seconds) {
            case 10:
                return "CONTINUING ROOTED ANDROID IN 10 SECONDS";
            case 9:
                return "CONTINUING ROOTED ANDROID IN 9 SECONDS";
            case 8:
                return "CONTINUING ROOTED ANDROID IN 8 SECONDS";
            case 7:
                return "CONTINUING ROOTED ANDROID IN 7 SECONDS";
            case 6:
                return "CONTINUING ROOTED ANDROID IN 6 SECONDS";
            case 5:
                return "CONTINUING ROOTED ANDROID IN 5 SECONDS";
            case 4:
                return "CONTINUING ROOTED ANDROID IN 4 SECONDS";
            case 3:
                return "CONTINUING ROOTED ANDROID IN 3 SECONDS";
            case 2:
                return "CONTINUING ROOTED ANDROID IN 2 SECONDS";
            default:
                return "CONTINUING ROOTED ANDROID IN 1 SECOND";
        }
    }

    switch (seconds) {
        case 10:
            return "CONTINUING ANDROID IN 10 SECONDS";
        case 9:
            return "CONTINUING ANDROID IN 9 SECONDS";
        case 8:
            return "CONTINUING ANDROID IN 8 SECONDS";
        case 7:
            return "CONTINUING ANDROID IN 7 SECONDS";
        case 6:
            return "CONTINUING ANDROID IN 6 SECONDS";
        case 5:
            return "CONTINUING ANDROID IN 5 SECONDS";
        case 4:
            return "CONTINUING ANDROID IN 4 SECONDS";
        case 3:
            return "CONTINUING ANDROID IN 3 SECONDS";
        case 2:
            return "CONTINUING ANDROID IN 2 SECONDS";
        default:
            return "CONTINUING ANDROID IN 1 SECOND";
    }
}


static void tf_drm_render_menu(
    int menu_page,
    int selected,
    int countdown_seconds,
    int persistent_root_installed
) {
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
        tf_drm_menu_width
        / 160U
    );

    u32 height_scale = (
        tf_drm_menu_height
        / 220U
    );

    if (
        height_scale < scale
    ) {
        scale = height_scale;
    }

    if (scale < 2U) {
        scale = 2U;
    }

    if (scale > 8U) {
        scale = 8U;
    }

    static const char title[] =
        "TREEFORGE";

    const char *section_title = (
        tf_menu_section_title(
            menu_page
        )
    );

    int item_count = (
        tf_menu_item_count(
            menu_page
        )
    );

    u32 title_width = (
        tf_drm_text_width(
            title,
            scale
        )
    );

    u32 title_x = (
        tf_drm_menu_width
        > title_width
        ? (
            tf_drm_menu_width
            - title_width
        ) / 2U
        : 0
    );

    u32 row_height = (
        13U * scale
    );

    u32 row_gap = (
        4U * scale
    );

    u32 total_rows = (
        row_height
        * (u32) item_count
        + row_gap
        * (u32) (
            item_count - 1
        )
    );

    u32 rows_y = (
        tf_drm_menu_height
        > total_rows
        ? (
            tf_drm_menu_height
            - total_rows
        ) / 2U
        : 0
    );

    u32 title_offset = (
        section_title[0] != '\0'
        ? 46U * scale
        : 34U * scale
    );

    u32 title_y = (
        rows_y
        > title_offset
        ? (
            rows_y
            - title_offset
        )
        : scale
    );

    tf_drm_draw_text(
        title_x,
        title_y,
        title,
        scale,
        foreground
    );

    u32 version_width = (
        tf_drm_text_width(
            tf_treeforge_version,
            scale
        )
    );

    u32 version_x = (
        tf_drm_menu_width
        > version_width
        ? (
            tf_drm_menu_width
            - version_width
        ) / 2U
        : 0
    );

    tf_drm_draw_text(
        version_x,
        title_y + 10U * scale,
        tf_treeforge_version,
        scale,
        foreground
    );

    const char *root_status = (
        persistent_root_installed
        ? "PERSISTENT ROOT INSTALLED"
        : "PERSISTENT ROOT NOT INSTALLED"
    );

    u32 root_status_width = (
        tf_drm_text_width(
            root_status,
            scale
        )
    );

    u32 root_status_x = (
        tf_drm_menu_width
        > root_status_width
        ? (
            tf_drm_menu_width
            - root_status_width
        ) / 2U
        : 0
    );

    tf_drm_draw_text(
        root_status_x,
        title_y + 20U * scale,
        root_status,
        scale,
        foreground
    );

    if (section_title[0] != '\0') {
        u32 section_width = (
            tf_drm_text_width(
                section_title,
                scale
            )
        );

        u32 section_x = (
            tf_drm_menu_width
            > section_width
            ? (
                tf_drm_menu_width
                - section_width
            ) / 2U
            : 0
        );

        tf_drm_draw_text(
            section_x,
            title_y + 32U * scale,
            section_title,
            scale,
            foreground
        );
    }

    u32 box_x = (
        tf_drm_menu_width
        / 10U
    );

    u32 box_width = (
        tf_drm_menu_width
        - (
            box_x * 2U
        )
    );

    for (
        int index = 0;
        index < item_count;
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

        const char *item_text = (
            tf_menu_item(
                menu_page,
                index,
                persistent_root_installed
            )
        );

        u32 item_scale = scale;

        u32 text_margin = (
            4U * scale
        );

        u32 available_text_width = (
            box_width > text_margin
            ? box_width - text_margin
            : box_width
        );

        while (
            item_scale > 2U
            && tf_drm_text_width(
                item_text,
                item_scale
            ) > available_text_width
        ) {
            item_scale--;
        }

        u32 text_width = (
            tf_drm_text_width(
                item_text,
                item_scale
            )
        );

        u32 text_x = (
            tf_drm_menu_width
            > text_width
            ? (
                tf_drm_menu_width
                - text_width
            ) / 2U
            : box_x
        );

        u32 glyph_height = (
            7U * item_scale
        );

        u32 text_y = (
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
            text_x,
            text_y,
            item_text,
            item_scale,
            active
            ? background
            : foreground
        );
    }

    const char *countdown = (
        tf_countdown_line(
            countdown_seconds,
            persistent_root_installed
        )
    );

    u32 countdown_scale = scale;

    u32 countdown_available_width = (
        box_width
    );

    while (
        countdown_scale > 2U
        && tf_drm_text_width(
            countdown,
            countdown_scale
        ) > countdown_available_width
    ) {
        countdown_scale--;
    }

    u32 countdown_width = (
        tf_drm_text_width(
            countdown,
            countdown_scale
        )
    );

    u32 countdown_x = (
        tf_drm_menu_width
        > countdown_width
        ? (
            tf_drm_menu_width
            - countdown_width
        ) / 2U
        : 0
    );

    u32 countdown_y = (
        rows_y
        + total_rows
        + 12U * scale
    );

    if (
        countdown_y
        + 7U * countdown_scale
        < tf_drm_menu_height
    ) {
        tf_drm_draw_text(
            countdown_x,
            countdown_y,
            countdown,
            countdown_scale,
            foreground
        );
    }

}


static void tf_output(
    const char *value
) {
    tf_write_all(
        tf_tty,
        value
    );

    tf_write_all(
        tf_console,
        value
    );
}

static void tf_log(
    const char *value
) {
    tf_write_all(
        tf_kmsg,
        "<6>treeforge: "
    );

    tf_write_all(
        tf_kmsg,
        value
    );

    tf_write_all(
        tf_kmsg,
        "\n"
    );
}

static void tf_render(
    int menu_page,
    int selected,
    int countdown_seconds,
    int persistent_root_installed
) {
    tf_output(
        "\033[2J\033[H"
        "TreeForge\n\n"
    );

    tf_output(
        tf_treeforge_version
    );

    tf_output(
        "\n"
    );

    tf_output(
        persistent_root_installed
        ? "PERSISTENT ROOT INSTALLED\n\n"
        : "PERSISTENT ROOT NOT INSTALLED\n\n"
    );

    const char *section_title = (
        tf_menu_section_title(
            menu_page
        )
    );

    if (section_title[0] != '\0') {
        tf_output(
            section_title
        );

        tf_output(
            "\n\n"
        );
    }

    int item_count = (
        tf_menu_item_count(
            menu_page
        )
    );

    for (
        int index = 0;
        index < item_count;
        index++
    ) {
        tf_output(
            index == selected
            ? "> "
            : "  "
        );

        tf_output(
            tf_menu_item(
                menu_page,
                index,
                persistent_root_installed
            )
        );

        tf_output(
            "\n"
        );
    }

    tf_output(
        "\n"
        "Volume Up/Down: navigate\n"
        "Power: select\n"
        "\n\n"
    );

    tf_output(
        tf_countdown_line(
            countdown_seconds,
            persistent_root_installed
        )
    );

    tf_output(
        "\n"
    );

    tf_drm_render_menu(
        menu_page,
        selected,
        countdown_seconds,
        persistent_root_installed
    );
}


static const char *tf_root_reboot_line(
    int seconds
) {
    if (seconds < 0) {
        return "PLEASE WAIT";
    }

    switch (seconds) {
        case 5:
            return "REBOOTING IN 5 SECONDS";
        case 4:
            return "REBOOTING IN 4 SECONDS";
        case 3:
            return "REBOOTING IN 3 SECONDS";
        case 2:
            return "REBOOTING IN 2 SECONDS";
        case 1:
            return "REBOOTING IN 1 SECOND";
        default:
            return "REBOOTING NOW";
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


static void tf_render_root_operation(
    int installing,
    int success,
    int reboot_seconds
) {
    const char *operation = (
        installing
        ? "INSTALLING ROOT PREFERENCE"
        : "REMOVING ROOT PREFERENCE"
    );

    const char *storage = (
        installing
        ? "TO PERSISTENT STORAGE"
        : "FROM PERSISTENT STORAGE"
    );

    const char *status = (
        success > 0
        ? "COMPLETE"
        : (
            success == 0
            ? "FAILED"
            : "WORKING"
        )
    );

    const char *reboot_line = (
        tf_root_reboot_line(
            reboot_seconds
        )
    );

    tf_output(
        "\033[2J\033[H"
        "TreeForge\n\n"
    );

    tf_output(
        tf_treeforge_version
    );

    tf_output(
        "\n\n"
    );

    tf_output(
        operation
    );

    tf_output(
        "\n"
    );

    tf_output(
        storage
    );

    tf_output(
        "\n\n"
    );

    tf_output(
        status
    );

    tf_output(
        "\n\n"
    );

    tf_output(
        reboot_line
    );

    tf_output(
        "\n\n"
        "PRESS POWER TO REBOOT NOW\n"
    );

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

    tf_drm_draw_management_line(
        "TREEFORGE",
        18U * scale,
        scale,
        foreground
    );

    tf_drm_draw_management_line(
        tf_treeforge_version,
        30U * scale,
        scale,
        foreground
    );

    tf_drm_draw_management_line(
        operation,
        58U * scale,
        scale,
        foreground
    );

    tf_drm_draw_management_line(
        storage,
        72U * scale,
        scale,
        foreground
    );

    tf_drm_draw_management_line(
        status,
        98U * scale,
        scale,
        foreground
    );

    tf_drm_draw_management_line(
        reboot_line,
        124U * scale,
        scale,
        foreground
    );

    tf_drm_draw_management_line(
        "PRESS POWER TO REBOOT NOW",
        148U * scale,
        scale,
        foreground
    );
}


static void tf_event_path(
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

static void tf_sysfs_event_dev_path(
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


static int tf_parse_device_number(
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


static int tf_prepare_input_node(
    int index,
    const char *device_path
) {
    char sysfs_path[48];

    tf_sysfs_event_dev_path(
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
        tf_parse_device_number(
            value,
            amount,
            &major_number,
            &minor_number
        )
        != 0
    ) {
        return -1;
    }

    long result = tf_mknod_path(
        device_path,
        S_IFCHR | 0600,
        tf_makedev(
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



static void tf_runtime_sysfs_event_dev_path(
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

static unsigned long tf_runtime_makedev(
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

static int tf_runtime_parse_device_number(
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

static int tf_get_event_device_number(
    int index,
    unsigned long *major,
    unsigned long *minor
) {
    char path[64];

    tf_runtime_sysfs_event_dev_path(
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

    return tf_runtime_parse_device_number(
        buffer,
        amount,
        major,
        minor
    );
}

static int tf_realize_input_nodes(
    int *created_input_directory,
    int *created_nodes,
    int *sysfs_devices_seen
) {
    *created_input_directory = 0;
    *sysfs_devices_seen = 0;

    for (
        int index = 0;
        index < INPUT_COUNT;
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
        index < INPUT_COUNT;
        index++
    ) {
        unsigned long major;
        unsigned long minor;

        if (
            tf_get_event_device_number(
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

        tf_event_path(
            index,
            path
        );

        long result = tf_syscall4(
            SYS_MKNODAT,
            AT_FDCWD,
            (long) path,
            S_IFCHR | 0600,
            (long) tf_runtime_makedev(
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

static void tf_cleanup_realized_input_nodes(
    int created_input_directory,
    int *created_nodes
) {
    for (
        int index = 0;
        index < INPUT_COUNT;
        index++
    ) {
        if (!created_nodes[index]) {
            continue;
        }

        char path[32];

        tf_event_path(
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

static void tf_close_inputs(
    long *inputs
) {
    for (
        int index = 0;
        index < INPUT_COUNT;
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

static int tf_reboot(void) {
    tf_syscall1(
        SYS_SYNC,
        0
    );

    long result = tf_syscall4(
        SYS_REBOOT,
        LINUX_REBOOT_MAGIC1,
        LINUX_REBOOT_MAGIC2,
        LINUX_REBOOT_CMD_RESTART,
        0
    );

    return (
        result == 0
        ? 0
        : -1
    );
}


static int tf_reboot_to(
    const char *target
) {
    tf_syscall1(
        SYS_SYNC,
        0
    );

    long result = tf_syscall4(
        SYS_REBOOT,
        LINUX_REBOOT_MAGIC1,
        LINUX_REBOOT_MAGIC2,
        LINUX_REBOOT_CMD_RESTART2,
        (long) target
    );

    return (
        result == 0
        ? 0
        : -1
    );
}

static void tf_boot_android(
    long *inputs,
    int mounted_dev,
    int mounted_proc,
    int mounted_sys
) {
    tf_log(
        "selection=android"
    );

    tf_output(
        "\033[2J\033[H"
        "TreeForge\n\n"
        "Continuing Android boot...\n"
    );

    tf_close_inputs(
        inputs
    );

    tf_close(
        tf_tty
    );

    tf_close(
        tf_console
    );

    tf_close(
        tf_kmsg
    );

    tf_tty = -1;
    tf_console = -1;
    tf_kmsg = -1;

    tf_cleanup_mounts(
        mounted_dev,
        mounted_proc,
        mounted_sys
    );

    char *argv[] = {
        (char *) "/init",
        0
    };

    char *envp[] = {
        (char *) "HOME=/",
        (char *) "TERM=linux",
        (char *) "PATH=/sbin:/system/bin:/system/xbin",
        0
    };

    tf_syscall3(
        SYS_EXECVE,
        (long) "/init.treeforge-original",
        (long) argv,
        (long) envp
    );

    /*
     * execve returning means the preserved canonical init could not be
     * entered. Never strand PID 1: return to the bootloader so the
     * failure remains recoverable.
     */
    tf_reboot_to(
        "bootloader"
    );

    for (;;) {
        tf_sleep_ms(
            1000
        );
    }
}

#define SYS_KILL 129
#define SYS_CLONE 220
#define SYS_WAIT4 260

#define TREEFORGE_SIGKILL 9
#define TREEFORGE_SIGCHLD 17

#define TREEFORGE_WAIT_WNOHANG 1

#define TREEFORGE_ROOT_MARKER_PATH \
    "/metadata/treeforge/root-enabled"

#define TREEFORGE_TRANSITION_FAILURE_PATH \
    "/metadata/treeforge/last-transition-failure"

#define TREEFORGE_RECOVERY_TEST_MARKER_PATH \
    "/metadata/treeforge/recovery-test"

#define TREEFORGE_RECOVERY_ADB_PREFLIGHT_REQUEST_PATH \
    "/dev/treeforge-recovery-adb-preflight"

#define TREEFORGE_RECOVERY_ADB_HANDOFF_PATH \
    "/dev/treeforge-recovery-adb-handoff"

static int tf_string_equal(
    const char *left,
    const char *right
) {
    if (!left || !right) {
        return 0;
    }

    while (*left && *right) {
        if (*left != *right) {
            return 0;
        }

        left++;
        right++;
    }

    return (
        *left == 0
        && *right == 0
    );
}


static int tf_probe_readable_path(
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


static int tf_copy_string_bounded(
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

    while (source[index] != '\0') {
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


static int tf_join_path(
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

    int needs_separator = (
        directory_length > 0
        && directory[
            directory_length - 1
        ] != '/'
    );

    usize required = (
        directory_length
        + (
            needs_separator
            ? 1
            : 0
        )
        + name_length
        + 1
    );

    if (required > capacity) {
        output[0] = '\0';
        return 0;
    }

    usize position = 0;

    for (
        usize index = 0;
        index < directory_length;
        index++
    ) {
        output[position++] = directory[index];
    }

    if (needs_separator) {
        output[position++] = '/';
    }

    for (
        usize index = 0;
        index < name_length;
        index++
    ) {
        output[position++] = name[index];
    }

    output[position] = '\0';

    return 1;
}


static long tf_read_path_bounded(
    const char *path,
    char *destination,
    usize capacity,
    int *truncated
) {
    if (
        !path
        || !destination
        || !truncated
    ) {
        return -1;
    }

    *truncated = 0;

    long fd = tf_open(
        path,
        O_RDONLY
        | O_NONBLOCK
    );

    if (fd < 0) {
        return -1;
    }

    usize total = 0;

    while (total < capacity) {
        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) (
                destination
                + total
            ),
            (long) (
                capacity
                - total
            )
        );

        if (amount < 0) {
            tf_close(
                fd
            );

            return -1;
        }

        if (amount == 0) {
            break;
        }

        total += (
            (usize) amount
        );
    }

    if (total == capacity) {
        char extra;

        long amount = tf_syscall3(
            SYS_READ,
            fd,
            (long) &extra,
            1
        );

        if (amount > 0) {
            *truncated = 1;
        }
    }

    tf_close(
        fd
    );

    destination[total] = '\0';

    return (
        (long) total
    );
}


static int tf_prepare_pstore_read(
    int *mounted_by_treeforge
) {
    if (!mounted_by_treeforge) {
        return 0;
    }

    *mounted_by_treeforge = 0;

    /*
     * pstore belongs canonically to Android. TreeForge mounts it only
     * for an explicitly requested diagnostics read, and does so
     * read-only.
     */
    long mount_result = tf_syscall6(
        SYS_MOUNT,
        (long) "pstore",
        (long) "/sys/fs/pstore",
        (long) "pstore",
        MS_RDONLY,
        0,
        0
    );

    if (mount_result == 0) {
        *mounted_by_treeforge = 1;

        return 1;
    }

    /*
     * /sys/fs/pstore exists as a kernel-created sysfs mount point
     * even when the pstore filesystem is not mounted. Therefore
     * directory readability is not evidence of an existing pstore
     * mount.
     *
     * Do not guess ownership. A failed TreeForge mount means this
     * diagnostics read is unavailable.
     */
    return 0;
}


static void tf_finish_pstore_read(
    int mounted_by_treeforge
) {
    if (!mounted_by_treeforge) {
        return;
    }

    /*
     * Remove only the mount layer TreeForge itself created.
     */
    tf_syscall2(
        SYS_UMOUNT2,
        (long) "/sys/fs/pstore",
        MNT_DETACH
    );
}


__attribute__((used))
static int tf_pstore_collect(
    struct tf_pstore_snapshot *snapshot
) {
    if (!snapshot) {
        return 0;
    }

    snapshot->available = 0;
    snapshot->record_count = 0;
    snapshot->records_omitted = 0;
    snapshot->enumeration_error = 0;

    int mounted_by_treeforge = 0;

    if (
        !tf_prepare_pstore_read(
            &mounted_by_treeforge
        )
    ) {
        return 0;
    }

    long directory_fd = tf_open(
        "/sys/fs/pstore",
        O_RDONLY
        | O_DIRECTORY
        | O_NONBLOCK
    );

    if (directory_fd < 0) {
        tf_finish_pstore_read(
            mounted_by_treeforge
        );

        return 0;
    }

    snapshot->available = 1;

    unsigned char directory_buffer[4096];

    for (;;) {
        long amount = tf_syscall3(
            SYS_GETDENTS64,
            directory_fd,
            (long) directory_buffer,
            (long) sizeof(
                directory_buffer
            )
        );

        if (amount < 0) {
            snapshot->enumeration_error = 1;
            break;
        }

        if (amount == 0) {
            break;
        }

        usize offset = 0;

        while (
            offset
            < (usize) amount
        ) {
            if (
                (usize) amount - offset
                < 19
            ) {
                snapshot->enumeration_error = 1;
                offset = (usize) amount;
                break;
            }

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
                snapshot->enumeration_error = 1;
                offset = (usize) amount;
                break;
            }

            usize name_capacity = (
                (usize) entry->d_reclen
                - name_offset
            );

            usize name_length = 0;

            while (
                name_length < name_capacity
                && entry->d_name[
                    name_length
                ] != '\0'
            ) {
                name_length++;
            }

            if (
                name_length == 0
                || name_length
                    == name_capacity
            ) {
                snapshot->records_omitted = 1;
                offset += entry->d_reclen;
                continue;
            }

            if (
                tf_string_equal(
                    entry->d_name,
                    "."
                )
                || tf_string_equal(
                    entry->d_name,
                    ".."
                )
            ) {
                offset += entry->d_reclen;
                continue;
            }

            /*
             * DT_DIR == 4. pstore records are files; do not recurse.
             * DT_UNKNOWN remains eligible and is tested by open().
             */
            if (entry->d_type == 4) {
                offset += entry->d_reclen;
                continue;
            }

            if (
                snapshot->record_count
                >= TREEFORGE_PSTORE_MAX_RECORDS
            ) {
                snapshot->records_omitted = 1;
                offset += entry->d_reclen;
                continue;
            }

            struct tf_pstore_record *record = (
                &snapshot->records[
                    snapshot->record_count
                ]
            );

            if (
                name_length + 1
                > TREEFORGE_PSTORE_NAME_CAPACITY
            ) {
                snapshot->records_omitted = 1;
                offset += entry->d_reclen;
                continue;
            }

            if (
                !tf_copy_string_bounded(
                    record->name,
                    sizeof(record->name),
                    entry->d_name
                )
            ) {
                snapshot->records_omitted = 1;
                offset += entry->d_reclen;
                continue;
            }

            char record_path[
                TREEFORGE_PSTORE_NAME_CAPACITY
                + 32
            ];

            if (
                !tf_join_path(
                    "/sys/fs/pstore",
                    record->name,
                    record_path,
                    sizeof(record_path)
                )
            ) {
                snapshot->records_omitted = 1;
                offset += entry->d_reclen;
                continue;
            }

            record->size = 0;
            record->readable = 0;
            record->truncated = 0;

            long record_size = tf_read_path_bounded(
                record_path,
                record->data,
                TREEFORGE_PSTORE_RECORD_CAPACITY,
                &record->truncated
            );

            if (record_size >= 0) {
                record->size = (
                    (usize) record_size
                );

                record->readable = 1;
            }

            snapshot->record_count++;

            offset += entry->d_reclen;
        }
    }

    tf_close(
        directory_fd
    );

    tf_finish_pstore_read(
        mounted_by_treeforge
    );

    return 1;
}


static void tf_create_presence_marker(
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


static int tf_root_marker_installed(void) {
    long fd = tf_open(
        TREEFORGE_ROOT_MARKER_PATH,
        O_RDONLY
    );

    if (fd < 0) {
        return 0;
    }

    tf_close(
        fd
    );

    return 1;
}


static int tf_install_root_marker(void) {
    /*
     * /metadata is canonically mounted during Android first stage.
     * TreeForge owns only its own subdirectory and marker.
     */
    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) TREEFORGE_ROOT_MARKER_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return 0;
    }

    tf_close(
        fd
    );

    tf_syscall1(
        SYS_SYNC,
        0
    );

    return 1;
}


static int tf_uninstall_root_marker(void) {
    /*
     * Uninstall is intentionally idempotent. If TreeForge's marker
     * does not exist, the requested state is already satisfied.
     */
    if (!tf_root_marker_installed()) {
        return 1;
    }

    long result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_ROOT_MARKER_PATH,
        0
    );

    if (result < 0) {
        return 0;
    }

    tf_syscall1(
        SYS_SYNC,
        0
    );

    return 1;
}


static void tf_record_transition_failure(
    const char *reason
) {
    /*
     * Transition diagnostics are TreeForge-owned userspace evidence.
     *
     * /metadata may not be available for failures that occur before
     * Android first stage mounts it, so this path is strictly
     * best-effort and must never become a new boot dependency.
     */
    tf_syscall3(
        SYS_MKDIRAT,
        AT_FDCWD,
        (long) "/metadata/treeforge",
        0755
    );

    long fd = tf_syscall4(
        SYS_OPENAT,
        AT_FDCWD,
        (long) TREEFORGE_TRANSITION_FAILURE_PATH,
        O_WRONLY
        | O_CREAT
        | O_TRUNC,
        0644
    );

    if (fd < 0) {
        return;
    }

    tf_write_all(
        fd,
        "treeforge-transition-failure-v1\n"
        "reason="
    );

    tf_write_all(
        fd,
        (
            reason
            ? reason
            : "unknown"
        )
    );

    tf_write_all(
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


static void tf_clear_transition_failure(void) {
    /*
     * Clear stale evidence only when TreeForge is about to attempt
     * a new Android handoff. If that exec fails, the current failure
     * path immediately writes a replacement record.
     */
    long result = tf_syscall3(
        SYS_UNLINKAT,
        AT_FDCWD,
        (long) TREEFORGE_TRANSITION_FAILURE_PATH,
        0
    );

    if (result == 0) {
        tf_syscall1(
            SYS_SYNC,
            0
        );
    }
}


static int tf_root_management_reboot(
    int installing,
    int success,
    long *inputs
) {
    const int ticks_per_second = (
        1000
        / POLL_INTERVAL_MS
    );

    const int total_ticks = (
        5
        * ticks_per_second
    );

    int elapsed_ticks = 0;
    int displayed_seconds = 5;

    tf_render_root_operation(
        installing,
        success,
        displayed_seconds
    );

    while (
        elapsed_ticks
        < total_ticks
    ) {
        for (
            int index = 0;
            index < INPUT_COUNT;
            index++
        ) {
            if (inputs[index] < 0) {
                continue;
            }

            for (;;) {
                struct tf_input_event event;

                long amount = tf_syscall3(
                    SYS_READ,
                    inputs[index],
                    (long) &event,
                    (long) sizeof(event)
                );

                if (
                    amount
                    != (long) sizeof(event)
                ) {
                    break;
                }

                if (
                    event.type == EV_KEY
                    && event.code == KEY_POWER
                    && event.value == 1
                ) {
                    tf_log(
                        "root-management reboot=power"
                    );

                    tf_render_root_operation(
                        installing,
                        success,
                        0
                    );

                    return tf_reboot();
                }
            }
        }

        tf_sleep_ms(
            POLL_INTERVAL_MS
        );

        elapsed_ticks++;

        int remaining_ticks = (
            total_ticks
            - elapsed_ticks
        );

        int remaining_seconds = (
            remaining_ticks
            + ticks_per_second
            - 1
        ) / ticks_per_second;

        if (
            remaining_seconds > 0
            && remaining_seconds
                != displayed_seconds
        ) {
            displayed_seconds = (
                remaining_seconds
            );

            tf_render_root_operation(
                installing,
                success,
                displayed_seconds
            );
        }
    }

    tf_log(
        "root-management reboot=countdown"
    );

    tf_render_root_operation(
        installing,
        success,
        0
    );

    return tf_reboot();
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

    return tf_parse_device_number(
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

    long node_result = tf_mknod_path(
        "/dev/dri/card0",
        S_IFCHR | 0600,
        tf_makedev(
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

    long result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_SET_CLIENT_CAP,
        &capability
    );

    if (result < 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-universal-planes-failed"
        );

        return;
    }

    tf_create_presence_marker(
        "/dev/treeforge-display-drm-universal-planes-ok"
    );

    static struct tf_drm_mode_get_plane_res resources;

    resources.plane_id_ptr = 0;
    resources.count_planes = 0;
    resources.pad = 0;

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETPLANERESOURCES,
        &resources
    );

    if (result < 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-plane-resources-failed"
        );

        return;
    }

    if (resources.count_planes == 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-planes-empty"
        );

        return;
    }

    tf_create_presence_marker(
        "/dev/treeforge-display-drm-planes-present"
    );

    if (
        resources.count_planes
        > TF_DRM_PLANE_LIMIT
    ) {
        tf_create_presence_marker(
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

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETPLANERESOURCES,
        &resources
    );

    if (result < 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-plane-ids-failed"
        );

        return;
    }

    if (
        resources.count_planes
        > plane_count
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-plane-race"
        );

        return;
    }

    tf_create_presence_marker(
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

        result = tf_ioctl(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-plane-query-ok"
        );
    }

    if (attached_plane) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-plane-attached"
        );
    }

    if (framebuffer_plane) {
        tf_create_presence_marker(
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

    long result = tf_ioctl(
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

    result = tf_ioctl(
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

        result = tf_ioctl(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-orientation-mode-landscape"
        );
    } else if (mode->vdisplay > mode->hdisplay) {
        tf_create_presence_marker(
            "/dev/treeforge-display-orientation-mode-portrait"
        );
    } else {
        tf_create_presence_marker(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-orientation-plane-rotation-absent"
        );
    } else {
        tf_create_presence_marker(
            "/dev/treeforge-display-orientation-plane-rotation-present"
        );

        if (rotation_value == 0) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-zero"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_0
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-0"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_90
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-90"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_180
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-180"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_ROTATE_270
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-rotate-270"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_REFLECT_X
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-plane-current-reflect-x"
            );
        }

        if (
            rotation_value
            & TF_DRM_MODE_REFLECT_Y
        ) {
            tf_create_presence_marker(
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

        long result = tf_ioctl(
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

            result = tf_ioctl(
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
                tf_create_presence_marker(
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
                        tf_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-0"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "rotate-90"
                        )
                    ) {
                        tf_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-90"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "rotate-180"
                        )
                    ) {
                        tf_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-180"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "rotate-270"
                        )
                    ) {
                        tf_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-rotate-270"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "reflect-x"
                        )
                    ) {
                        tf_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-reflect-x"
                        );
                    } else if (
                        tf_drm_property_name_equal(
                            enums[index].name,
                            "reflect-y"
                        )
                    ) {
                        tf_create_presence_marker(
                            "/dev/treeforge-display-orientation-plane-supports-reflect-y"
                        );
                    }
                }
            } else {
                tf_create_presence_marker(
                    "/dev/treeforge-display-orientation-plane-enums-failed"
                );
            }
        } else {
            tf_create_presence_marker(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-orientation-panel-property-absent"
        );
    } else {
        tf_create_presence_marker(
            "/dev/treeforge-display-orientation-panel-property-present"
        );

        if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_NORMAL
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-normal"
            );
        } else if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_BOTTOM_UP
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-bottom-up"
            );
        } else if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_LEFT_UP
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-left-up"
            );
        } else if (
            panel_orientation
            == TF_DRM_PANEL_ORIENTATION_RIGHT_UP
        ) {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-right-up"
            );
        } else {
            tf_create_presence_marker(
                "/dev/treeforge-display-orientation-panel-value-unknown"
            );
        }
    }

    tf_create_presence_marker(
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

    long result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_GET_CAP,
        &dumb_cap
    );

    if (
        result == 0
        && dumb_cap.value != 0
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-dumb-buffer-ok"
        );
    } else {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-dumb-buffer-failed"
        );
    }

    struct tf_drm_set_client_cap atomic_cap;

    atomic_cap.capability = (
        TF_DRM_CLIENT_CAP_ATOMIC
    );

    atomic_cap.value = 1;

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_SET_CLIENT_CAP,
        &atomic_cap
    );

    if (result == 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-ok"
        );
    } else {
        tf_create_presence_marker(
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

    result = tf_ioctl(
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
        tf_create_presence_marker(
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

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (
        result < 0
        || resources.count_crtcs > crtc_count
        || resources.count_connectors > connector_count
    ) {
        tf_create_presence_marker(
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

        result = tf_ioctl(
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

        result = tf_ioctl(
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

            result = tf_ioctl(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-force-probe-ok"
        );
    } else {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-force-probe-failed"
        );
    }

    if (modes_present) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-modes-present"
        );
    }

    if (preferred_mode_present) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-preferred-mode"
        );
    }

    if (encoders_present) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-encoders-present"
        );
    }

    if (encoder_query_ok) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-encoder-query-ok"
        );
    }

    if (compatible_crtc) {
        tf_create_presence_marker(
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

    long result = tf_ioctl(
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
        tf_create_presence_marker(
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

    result = tf_ioctl(
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

        result = tf_ioctl(
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

        result = tf_ioctl(
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

            result = tf_ioctl(
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
        tf_create_presence_marker(
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

    result = tf_ioctl(
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

    result = tf_ioctl(
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

        result = tf_ioctl(
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

        result = tf_ioctl(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-test-primary-plane-failed"
        );

        return 0;
    }

    tf_create_presence_marker(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-properties-failed"
        );

        return 0;
    }

    tf_create_presence_marker(
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

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_CREATEPROPBLOB,
        &blob
    );

    if (result < 0 || blob.blob_id == 0) {
        tf_create_presence_marker(
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

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_CREATE_DUMB,
        &dumb
    );

    if (result < 0 || dumb.handle == 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-dumb-create-failed"
        );

        struct tf_drm_mode_destroy_blob destroy_blob;
        destroy_blob.blob_id = blob.blob_id;

        tf_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_DESTROYPROPBLOB,
            &destroy_blob
        );

        return 0;
    }

    tf_create_presence_marker(
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

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_ADDFB2,
        &framebuffer
    );

    if (
        result < 0
        || framebuffer.fb_id == 0
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-addfb2-failed"
        );

        struct tf_drm_mode_destroy_dumb destroy_dumb;
        destroy_dumb.handle = dumb.handle;

        tf_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_DESTROY_DUMB,
            &destroy_dumb
        );

        struct tf_drm_mode_destroy_blob destroy_blob;
        destroy_blob.blob_id = blob.blob_id;

        tf_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_DESTROYPROPBLOB,
            &destroy_blob
        );

        return 0;
    }

    tf_create_presence_marker(
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

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_ATOMIC,
        &atomic
    );

    if (result == 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-atomic-test-ok"
        );
    } else {
        tf_create_presence_marker(
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

        result = tf_ioctl(
            drm_fd,
            TF_DRM_IOCTL_MODE_MAP_DUMB,
            &map_dumb
        );

        if (result == 0) {
            tf_create_presence_marker(
                "/dev/treeforge-display-drm-map-dumb-ok"
            );

            mapped_address = tf_syscall6(
                SYS_MMAP,
                0,
                (long) dumb.size,
                PROT_READ | PROT_WRITE,
                MAP_SHARED,
                drm_fd,
                (long) map_dumb.offset
            );

            if (mapped_address >= 0) {
                tf_create_presence_marker(
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

                tf_create_presence_marker(
                    "/dev/treeforge-display-drm-pattern-rendered"
                );

                /*
                 * Apply the exact state that already passed TEST_ONLY.
                 */
                atomic.flags = (
                    TF_DRM_MODE_ATOMIC_ALLOW_MODESET
                );

                result = tf_ioctl(
                    drm_fd,
                    TF_DRM_IOCTL_MODE_ATOMIC,
                    &atomic
                );

                if (result == 0) {
                    real_scanout_active = 1;

                    tf_create_presence_marker(
                        "/dev/treeforge-display-drm-real-commit-ok"
                    );

                    /*
                     * The real commit is now retained for the entire
                     * interactive TreeForge menu session.
                     */
                } else {
                    tf_create_presence_marker(
                        "/dev/treeforge-display-drm-real-commit-failed"
                    );
                }
            } else {
                tf_create_presence_marker(
                    "/dev/treeforge-display-drm-mmap-failed"
                );
            }
        } else {
            tf_create_presence_marker(
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

        tf_create_presence_marker(
            "/dev/treeforge-display-drm-menu-session-active"
        );

        return 1;
    }

    /*
     * A failed retained-session start owns no persistent KMS state.
     * Release everything allocated during the attempt.
     */
    if (mapped_address >= 0) {
        tf_syscall2(
            SYS_MUNMAP,
            mapped_address,
            (long) dumb.size
        );
    }

    u32 framebuffer_id = (
        framebuffer.fb_id
    );

    tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_RMFB,
        &framebuffer_id
    );

    struct tf_drm_mode_destroy_dumb destroy_dumb;
    destroy_dumb.handle = dumb.handle;

    tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_DESTROY_DUMB,
        &destroy_dumb
    );

    struct tf_drm_mode_destroy_blob destroy_blob;
    destroy_blob.blob_id = blob.blob_id;

    tf_ioctl(
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

    long result = tf_ioctl(
        tf_drm_menu_fd,
        TF_DRM_IOCTL_MODE_ATOMIC,
        &atomic
    );

    if (result == 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-menu-disable-ok"
        );
    } else {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-menu-disable-failed"
        );
    }

    if (
        tf_drm_menu_mapped_address >= 0
    ) {
        tf_syscall2(
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

        tf_ioctl(
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

        tf_ioctl(
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

        tf_ioctl(
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

    tf_create_presence_marker(
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

    long result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (result < 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-resources-failed"
        );

        return;
    }

    tf_create_presence_marker(
        "/dev/treeforge-display-drm-resources-ok"
    );

    u32 crtc_count = (
        resources.count_crtcs
    );

    u32 connector_count = (
        resources.count_connectors
    );

    if (resources.count_fbs > 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-framebuffers-present"
        );
    }

    if (crtc_count > 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-crtcs-present"
        );
    }

    if (connector_count > 0) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-connectors-present"
        );
    }

    if (
        crtc_count > TF_DRM_RESOURCE_LIMIT
        || connector_count > TF_DRM_RESOURCE_LIMIT
    ) {
        tf_create_presence_marker(
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

    result = tf_ioctl(
        drm_fd,
        TF_DRM_IOCTL_MODE_GETRESOURCES,
        &resources
    );

    if (result < 0) {
        tf_create_presence_marker(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-resource-race"
        );

        return;
    }

    tf_create_presence_marker(
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

        result = tf_ioctl(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-crtc-query-ok"
        );
    }

    if (active_crtc) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-crtc-active"
        );
    }

    if (active_framebuffer) {
        tf_create_presence_marker(
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

        result = tf_ioctl(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-connector-query-ok"
        );
    }

    if (connected_connector) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-connector-connected"
        );
    }

    if (connector_modes) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-connector-modes"
        );
    }

    if (connector_encoder) {
        tf_create_presence_marker(
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

    tf_create_presence_marker(
        "/dev/treeforge-display-probe-v1"
    );

    if (
        tf_probe_readable_path(
            "/sys/class/graphics/fb0/dev"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-fb0-sysfs"
        );
    }

    if (
        tf_probe_readable_path(
            "/dev/fb0"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-fb0-node"
        );
    }

    if (
        tf_probe_readable_path(
            "/dev/graphics/fb0"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-graphics-fb0-node"
        );
    }

    if (
        tf_probe_readable_path(
            "/sys/class/drm/card0/dev"
        )
    ) {
        tf_create_presence_marker(
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
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card0-opened"
        );

        if (created_drm_card0) {
            tf_create_presence_marker(
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
        tf_probe_readable_path(
            "/sys/class/drm/card1/dev"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card1-sysfs"
        );
    }

    if (
        tf_probe_readable_path(
            "/sys/class/drm/card2/dev"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card2-sysfs"
        );
    }

    if (
        tf_probe_readable_path(
            "/sys/class/drm/card3/dev"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card3-sysfs"
        );
    }

    if (
        tf_probe_readable_path(
            "/dev/dri/card0"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card0-node"
        );
    }

    if (
        tf_probe_readable_path(
            "/dev/dri/card1"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card1-node"
        );
    }

    if (
        tf_probe_readable_path(
            "/dev/dri/card2"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card2-node"
        );
    }

    if (
        tf_probe_readable_path(
            "/dev/dri/card3"
        )
    ) {
        tf_create_presence_marker(
            "/dev/treeforge-display-drm-card3-node"
        );
    }
}


__attribute__((noreturn))
static void tf_transition_failure(
    const char *reason
) {
    /*
     * execve() failure may occur after the ordinary TreeForge kmsg
     * descriptor was deliberately closed for Android handoff.
     * Reopen /dev/kmsg best-effort on the failure-only path so the
     * diagnostic descriptor can never leak into successful Android.
     */
    long failure_kmsg = tf_kmsg;
    int close_failure_kmsg = 0;

    if (failure_kmsg < 0) {
        failure_kmsg = tf_open(
            "/dev/kmsg",
            O_WRONLY
            | O_NONBLOCK
        );

        if (failure_kmsg >= 0) {
            close_failure_kmsg = 1;
        }
    }

    tf_write_all(
        failure_kmsg,
        "TreeForge: transition-failure reason="
    );

    tf_write_all(
        failure_kmsg,
        (
            reason
            ? reason
            : "unknown"
        )
    );

    tf_write_all(
        failure_kmsg,
        "\n"
    );

    if (close_failure_kmsg) {
        tf_close(
            failure_kmsg
        );
    }

    tf_record_transition_failure(
        reason
    );

    /*
     * A failed PID 1 transition must remain recoverable.
     */
    tf_reboot_to(
        "bootloader"
    );

    for (;;) {
        tf_sleep_ms(
            1000
        );
    }
}

__attribute__((noreturn))
static void tf_main(
    long argc,
    char **argv,
    char **envp
) {
    /*
     * Second invocation:
     *
     * Canonical Android FirstStageMain reached its normal
     * first-stage -> selinux_setup transition, except the exact
     * transition path was redirected to /proc/self/fd/99.
     *
     * Android first-stage initialization has already established
     * its canonical module/device environment. TreeForge may now
     * consume the resulting Linux input devices without duplicating
     * Android's first-stage module loader.
     */
    if (argc > 1) {
        if (
            !argv[1]
            || !tf_string_equal(
                argv[1],
                "selinux_setup"
            )
        ) {
            tf_transition_failure(
                "invalid-treeforge-reentry"
            );
        }

        /*
         * Post-first-stage TreeForge boot menu.
         *
         * FirstStageMain has already performed Android's canonical
         * first-stage module loading and has established /dev.
         *
         * TreeForge does not load kernel modules here. It discovers
         * whichever Linux evdev nodes expose the canonical button
         * key codes.
         */
        tf_kmsg = tf_open(
            "/dev/kmsg",
            O_WRONLY
            | O_NONBLOCK
        );

        tf_tty = tf_open(
            "/dev/tty0",
            O_WRONLY
            | O_NONBLOCK
        );

        tf_console = tf_open(
            "/dev/console",
            O_WRONLY
            | O_NONBLOCK
        );

        /*
         * One-shot recovery runtime development trigger.
         *
         * /metadata is canonically available at this exact
         * post-FirstStageMain boundary. The marker is removed before
         * attempting exec so a failed runtime can never create an
         * automatic reboot loop.
         */
        if (
            tf_probe_readable_path(
                TREEFORGE_RECOVERY_TEST_MARKER_PATH
            )
        ) {
            long marker_clear_result = tf_syscall3(
                SYS_UNLINKAT,
                AT_FDCWD,
                (long) TREEFORGE_RECOVERY_TEST_MARKER_PATH,
                0
            );

            if (marker_clear_result < 0) {
                tf_log(
                    "recovery-test marker-clear=failed"
                );
            } else {
                tf_syscall1(
                    SYS_SYNC,
                    0
                );

                tf_log(
                    "recovery-test action=runtime"
                );

                if (
                    !tf_realize_recovery_runtime_files()
                ) {
                    tf_transition_failure(
                        "recovery-runtime-materialize"
                    );
                }

                tf_close_recovery_runtime_fds();

                /*
                 * Recovery owns this process from here. Do not carry
                 * Android-root payloads, transition state, or menu
                 * output descriptors into it.
                 */
                tf_close(
                    TREEFORGE_ADB_DEBUG_FD
                );

                tf_close(
                    TREEFORGE_USERDEBUG_SEPOLICY_FD
                );

                tf_close(
                    TREEFORGE_TRANSITION_FD
                );

                tf_close(
                    tf_tty
                );

                tf_tty = -1;

                tf_close(
                    tf_console
                );

                tf_console = -1;

                tf_close(
                    tf_kmsg
                );

                tf_kmsg = -1;

                char *recovery_argv[] = {
                    (char *) "/treeforge-recovery",
                    0
                };

                tf_syscall3(
                    SYS_EXECVE,
                    (long) "/proc/self/fd/96",
                    (long) recovery_argv,
                    (long) envp
                );

                tf_transition_failure(
                    "recovery-runtime-exec"
                );
            }
        }

        /*
         * Keep the separately generated recovery runtime retained
         * through the interactive boot-menu decision.
         *
         * FD 96 is closed below on every non-Recovery path. This
         * preserves the previously accepted Android descriptor-leak
         * invariant while making Recovery a direct menu destination.
         */
        int created_input_directory = 0;

        int created_input_nodes[
            INPUT_COUNT
        ];

        int sysfs_devices_seen = 0;

        tf_realize_input_nodes(
            &created_input_directory,
            created_input_nodes,
            &sysfs_devices_seen
        );

        long inputs[
            INPUT_COUNT
        ];

        for (
            int index = 0;
            index < INPUT_COUNT;
            index++
        ) {
            inputs[index] = -1;
        }

        /*
         * TreeForge runtime identity marker.
         *
         * Android's canonical first-stage /dev tmpfs survives the
         * exec transition. This marker proves that the TreeForge
         * early-menu path was actually consumed on this boot.
         */
        long marker = tf_syscall4(
            SYS_OPENAT,
            AT_FDCWD,
            (long) "/dev/treeforge-early-menu",
            O_WRONLY
            | O_CREAT
            | O_TRUNC,
            0644
        );

        if (marker >= 0) {
            tf_write_all(
                marker,
                "treeforge-early-menu-v1\n"
            );

            tf_close(
                marker
            );
        }

        tf_probe_display_surfaces();

        if (sysfs_devices_seen > 0) {
            tf_log(
                "early-menu input-sysfs=present"
            );
        } else {
            tf_log(
                "early-menu input-sysfs=absent"
            );
        }

        /*
         * Open the current event population and drain any queued
         * events before presenting the menu.
         *
         * This prevents the power press that originally started the
         * device from immediately selecting the default item.
         */
        for (
            int index = 0;
            index < INPUT_COUNT;
            index++
        ) {
            char event_path[32];

            tf_event_path(
                index,
                event_path
            );

            inputs[index] = tf_open(
                event_path,
                O_RDONLY
                | O_NONBLOCK
            );

            if (inputs[index] < 0) {
                continue;
            }

            for (;;) {
                struct tf_input_event event;

                long amount = tf_syscall3(
                    SYS_READ,
                    inputs[index],
                    (long) &event,
                    (long) sizeof(event)
                );

                if (
                    amount
                    != (long) sizeof(event)
                ) {
                    break;
                }
            }
        }

        int menu_page = TREEFORGE_MENU_MAIN;
        int selected = 0;
        int boot_android = 0;
        int boot_rooted_android = 0;
        int install_root = 0;
        int uninstall_root = 0;
        int persistent_root_timeout = 0;

        int persistent_root_installed = (
            tf_root_marker_installed()
        );

        int idle_ticks = 0;
        int displayed_countdown = 10;
        int auto_boot_paused = 0;

        const int idle_limit = (
            MENU_TIMEOUT_MS
            / POLL_INTERVAL_MS
        );

        const int ticks_per_second = (
            1000
            / POLL_INTERVAL_MS
        );

        tf_log(
            "early-menu begin"
        );

        tf_render(
            menu_page,
            selected,
            displayed_countdown,
            persistent_root_installed
        );

        while (
            !boot_android
            && !boot_rooted_android
            && !install_root
            && !uninstall_root
            && (
                auto_boot_paused
                || idle_ticks < idle_limit
            )
        ) {
            for (
                int index = 0;
                index < INPUT_COUNT;
                index++
            ) {
                /*
                 * Retry nodes that were unavailable earlier. A late
                 * device registration must not require a fixed event
                 * number or a dispatcher restart.
                 */
                if (inputs[index] < 0) {
                    char event_path[32];

                    tf_event_path(
                        index,
                        event_path
                    );

                    inputs[index] = tf_open(
                        event_path,
                        O_RDONLY
                        | O_NONBLOCK
                    );

                    if (inputs[index] >= 0) {
                        /*
                         * Drain anything queued before this node became
                         * visible to TreeForge. Only presses arriving
                         * after discovery participate in menu control.
                         */
                        for (;;) {
                            struct tf_input_event event;

                            long amount = tf_syscall3(
                                SYS_READ,
                                inputs[index],
                                (long) &event,
                                (long) sizeof(event)
                            );

                            if (
                                amount
                                != (long) sizeof(event)
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
                    struct tf_input_event event;

                    long amount = tf_syscall3(
                        SYS_READ,
                        inputs[index],
                        (long) &event,
                        (long) sizeof(event)
                    );

                    if (
                        amount
                        != (long) sizeof(event)
                    ) {
                        /*
                         * -11 is EAGAIN for a nonblocking descriptor.
                         * Any other failure causes the node to be
                         * rediscovered on a later poll.
                         */
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
                        event.type != EV_KEY
                        || event.value != 1
                    ) {
                        continue;
                    }

                    if (
                        event.code
                        == KEY_VOLUMEUP
                    ) {
                        int item_count = (
                            tf_menu_item_count(
                                menu_page
                            )
                        );

                        selected = (
                            selected
                            + item_count
                            - 1
                        ) % item_count;

                        idle_ticks = 0;
                        displayed_countdown = 0;
                        auto_boot_paused = 1;

                        tf_log(
                            "early-menu key=volume_up"
                        );

                        tf_log(
                            "early-menu auto-boot=paused"
                        );

                        tf_render(
                            menu_page,
                            selected,
                            displayed_countdown,
                            persistent_root_installed
                        );

                        continue;
                    }

                    if (
                        event.code
                        == KEY_VOLUMEDOWN
                    ) {
                        int item_count = (
                            tf_menu_item_count(
                                menu_page
                            )
                        );

                        selected = (
                            selected
                            + 1
                        ) % item_count;

                        idle_ticks = 0;
                        displayed_countdown = 0;
                        auto_boot_paused = 1;

                        tf_log(
                            "early-menu key=volume_down"
                        );

                        tf_log(
                            "early-menu auto-boot=paused"
                        );

                        tf_render(
                            menu_page,
                            selected,
                            displayed_countdown,
                            persistent_root_installed
                        );

                        continue;
                    }

                    if (
                        event.code
                        == KEY_POWER
                    ) {
                        tf_log(
                            "early-menu key=power"
                        );

                        /*
                         * The TreeForge early menu is intentionally
                         * flat. Every visible row is a direct action.
                         */
                        if (selected == 0) {
                            if (
                                persistent_root_installed
                            ) {
                                boot_rooted_android = 1;
                            } else {
                                boot_android = 1;
                            }

                            break;
                        }

                        if (selected == 1) {
                            if (
                                persistent_root_installed
                            ) {
                                boot_android = 1;
                            } else {
                                boot_rooted_android = 1;
                            }

                            break;
                        }

                        if (selected == 2) {
                            if (
                                persistent_root_installed
                            ) {
                                uninstall_root = 1;
                            } else {
                                install_root = 1;
                            }

                            break;
                        }

                        if (selected == 3) {
                            tf_log(
                                "early-menu action=bootloader"
                            );

                            tf_drm_menu_cleanup();

                            tf_close(
                                TREEFORGE_ADB_DEBUG_FD
                            );

                            tf_close(
                                TREEFORGE_USERDEBUG_SEPOLICY_FD
                            );

                            tf_close_recovery_runtime_fds();

                            tf_close(
                                TREEFORGE_RECOVERY_FD
                            );

                            tf_reboot_to(
                                "bootloader"
                            );

                            tf_transition_failure(
                                "bootloader-reboot-returned"
                            );
                        }

                        if (selected == 4) {
                            tf_log(
                                "early-menu action=treeforge-recovery"
                            );

                            tf_drm_menu_cleanup();

                            tf_close_inputs(
                                inputs
                            );

                            if (
                                !tf_realize_recovery_runtime_files()
                            ) {
                                tf_transition_failure(
                                    "recovery-runtime-materialize"
                                );
                            }

                            /*
                             * Bring Recovery ADB up before replacing the
                             * TreeForge PID-1 dispatcher with the normal
                             * Recovery controller.
                             *
                             * Run the already-generated Recovery executable
                             * as a short-lived preflight child rather than
                             * duplicating configfs/FunctionFS/adbd policy in
                             * the dispatcher.
                             */
                            tf_syscall3(
                                SYS_UNLINKAT,
                                AT_FDCWD,
                                (long)
                                    TREEFORGE_RECOVERY_ADB_HANDOFF_PATH,
                                0
                            );

                            long preflight_marker = tf_syscall4(
                                SYS_OPENAT,
                                AT_FDCWD,
                                (long)
                                    TREEFORGE_RECOVERY_ADB_PREFLIGHT_REQUEST_PATH,
                                O_WRONLY
                                | O_CREAT
                                | O_TRUNC,
                                0600
                            );

                            if (preflight_marker >= 0) {
                                tf_write_all(
                                    preflight_marker,
                                    "1\n"
                                );

                                tf_close(
                                    preflight_marker
                                );

                                long preflight_child = tf_syscall6(
                                    SYS_CLONE,
                                    TREEFORGE_SIGCHLD,
                                    0,
                                    0,
                                    0,
                                    0,
                                    0
                                );

                                if (preflight_child == 0) {
                                    char *preflight_argv[] = {
                                        (char *) "/treeforge-recovery",
                                        0
                                    };

                                    tf_syscall3(
                                        SYS_EXECVE,
                                        (long) "/proc/self/fd/96",
                                        (long) preflight_argv,
                                        (long) envp
                                    );

                                    tf_syscall1(
                                        SYS_EXIT,
                                        127
                                    );

                                    for (;;) {
                                    }
                                }

                                if (preflight_child > 0) {
                                    int preflight_status = 0;

                                    long preflight_wait = tf_syscall4(
                                        SYS_WAIT4,
                                        preflight_child,
                                        (long) &preflight_status,
                                        0,
                                        0
                                    );

                                    if (
                                        preflight_wait
                                        == preflight_child
                                        && (
                                            preflight_status
                                            & 0x7f
                                        ) == 0
                                        && (
                                            (
                                                preflight_status
                                                >> 8
                                            )
                                            & 0xff
                                        ) == 0
                                        && tf_probe_readable_path(
                                            TREEFORGE_RECOVERY_ADB_HANDOFF_PATH
                                        )
                                    ) {
                                        tf_log(
                                            "recovery-adb-preflight=complete"
                                        );
                                    } else {
                                        tf_log(
                                            "recovery-adb-preflight=failed"
                                        );
                                    }
                                } else {
                                    tf_log(
                                        "recovery-adb-preflight=clone-failed"
                                    );
                                }
                            } else {
                                tf_log(
                                    "recovery-adb-preflight=marker-failed"
                                );
                            }

                            /*
                             * Belt-and-suspenders cleanup: the preflight
                             * removes this before initialization, but the
                             * dispatcher also clears it so an exec failure
                             * can never make normal Recovery rerun preflight.
                             */
                            tf_syscall3(
                                SYS_UNLINKAT,
                                AT_FDCWD,
                                (long)
                                    TREEFORGE_RECOVERY_ADB_PREFLIGHT_REQUEST_PATH,
                                0
                            );

                            tf_close_recovery_runtime_fds();

                            /*
                             * Recovery owns PID 1 from this point.
                             * It does not inherit Android root payload
                             * state or the first-stage transition FD.
                             */
                            tf_close(
                                TREEFORGE_ADB_DEBUG_FD
                            );

                            tf_close(
                                TREEFORGE_USERDEBUG_SEPOLICY_FD
                            );

                            tf_close(
                                TREEFORGE_TRANSITION_FD
                            );

                            tf_close(
                                tf_tty
                            );

                            tf_tty = -1;

                            tf_close(
                                tf_console
                            );

                            tf_console = -1;

                            tf_close(
                                tf_kmsg
                            );

                            tf_kmsg = -1;

                            char *recovery_argv[] = {
                                (char *) "/treeforge-recovery",
                                0
                            };

                            tf_syscall3(
                                SYS_EXECVE,
                                (long) "/proc/self/fd/96",
                                (long) recovery_argv,
                                (long) envp
                            );

                            tf_transition_failure(
                                "recovery-runtime-exec"
                            );
                        }
                    }
                }

                if (
                    boot_android
                    || boot_rooted_android
                    || install_root
                    || uninstall_root
                ) {
                    break;
                }
            }

            if (
                boot_android
                || boot_rooted_android
                || install_root
                || uninstall_root
            ) {
                break;
            }

            tf_sleep_ms(
                POLL_INTERVAL_MS
            );

            if (!auto_boot_paused) {
                idle_ticks++;

                int remaining_ticks = (
                    idle_limit
                    - idle_ticks
                );

                int countdown_seconds = (
                    remaining_ticks
                    + ticks_per_second
                    - 1
                ) / ticks_per_second;

                if (
                    countdown_seconds > 0
                    && countdown_seconds
                        != displayed_countdown
                ) {
                    displayed_countdown = (
                        countdown_seconds
                    );

                    tf_render(
                        menu_page,
                        selected,
                        displayed_countdown,
                        persistent_root_installed
                    );
                }
            }
        }

        /*
         * Recovery was not selected. Drop both the retained Recovery
         * executable and its generated dynamic-runtime descriptor
         * population before Android/root/default continuation.
         */
        tf_close_recovery_runtime_fds();

        tf_close(
            TREEFORGE_RECOVERY_FD
        );

        /*
         * Persistent root defines TreeForge's default Android boot
         * state. The idle timeout therefore enters rooted Android
         * whenever the marker is installed. Explicit main-menu
         * selections are resolved earlier, and Root management
         * operations are never overridden by timeout policy.
         */
        if (
            !boot_android
            && !boot_rooted_android
            && !install_root
            && !uninstall_root
            && persistent_root_installed
        ) {
            boot_rooted_android = 1;
            persistent_root_timeout = 1;
        }

        if (uninstall_root) {
            tf_log(
                "early-menu action=uninstall-root"
            );
        } else if (install_root) {
            tf_log(
                "early-menu action=install-root"
            );
        } else if (persistent_root_timeout) {
            tf_log(
                "early-menu timeout=rooted-android"
            );
        } else if (boot_rooted_android) {
            tf_log(
                "early-menu action=rooted-android"
            );
        } else if (boot_android) {
            tf_log(
                "early-menu action=android"
            );
        } else {
            /*
             * Idle timeout always follows the safe/default Android
             * path regardless of which item was merely highlighted.
             */
            tf_log(
                "early-menu timeout=android"
            );
        }

        if (
            install_root
            || uninstall_root
        ) {
            /*
             * Present the operation before mutating persistent state,
             * then replace WORKING with the exact completion result.
             */
            tf_render_root_operation(
                install_root,
                -1,
                -1
            );

            int operation_success = (
                install_root
                ? tf_install_root_marker()
                : tf_uninstall_root_marker()
            );

            if (operation_success) {
                tf_log(
                    install_root
                    ? "root-management result=complete install"
                    : "root-management result=complete uninstall"
                );
            } else {
                tf_log(
                    install_root
                    ? "root-management result=failed install"
                    : "root-management result=failed uninstall"
                );
            }

            tf_root_management_reboot(
                install_root,
                operation_success,
                inputs
            );

            /*
             * Successful reboot does not return.
             */
            tf_transition_failure(
                "root-management-reboot-returned"
            );
        }

        tf_close_inputs(
            inputs
        );

        /*
         * Remove only nodes/directories that TreeForge itself created.
         * Existing Android first-stage /dev state remains untouched.
         */
        tf_cleanup_realized_input_nodes(
            created_input_directory,
            created_input_nodes
        );

        /*
         * Return the display to the inactive state observed before
         * TreeForge's menu, then release only TreeForge-owned DRM
         * resources.
         */
        tf_drm_menu_cleanup();

        tf_close(
            tf_tty
        );

        tf_tty = -1;

        tf_close(
            tf_console
        );

        tf_console = -1;

        tf_close(
            tf_kmsg
        );

        tf_kmsg = -1;

        /*
         * Root management operations complete and reboot before
         * reaching the ordinary Android transition boundary.
         */

        /*
         * A new Android handoff supersedes any previous TreeForge
         * transition-failure evidence. Successful exec leaves the
         * record absent; a failed handoff immediately replaces it.
         */
        tf_clear_transition_failure();

        /*
         * Rooted Android uses the same fully cleaned menu exit as
         * canonical Android, but reconstructs Android's force-debuggable
         * selinux_setup transition before entering second stage.
         */
        if (boot_rooted_android) {
            int rooted_result = tf_exec_rooted_android(
                envp
            );

            if (
                rooted_result
                == TREEFORGE_ROOT_EXEC_ENVIRONMENT_FAILED
            ) {
                tf_transition_failure(
                    "root-environment"
                );
            }

            if (
                rooted_result
                == TREEFORGE_ROOT_EXEC_DEBUG_RAMDISK_FAILED
            ) {
                tf_transition_failure(
                    "root-debug-ramdisk"
                );
            }

            if (
                rooted_result
                == TREEFORGE_ROOT_EXEC_SELINUX_FAILED
            ) {
                tf_transition_failure(
                    "root-selinux-exec"
                );
            }

            tf_transition_failure(
                "root-transition-unknown"
            );
        }

        /*
         * The retained debug-root payloads are not part of canonical
         * Android execution. Do not leak their descriptors into
         * Android second stage.
         */
        tf_close(
            TREEFORGE_ADB_DEBUG_FD
        );

        tf_close(
            TREEFORGE_USERDEBUG_SEPOLICY_FD
        );

        /*
         * The backing executable is already mapped, so fd 99 is no
         * longer required. Do not leak TreeForge's transition FD into
         * Android second stage.
         */
        tf_close(
            TREEFORGE_TRANSITION_FD
        );

        char *next_argv[] = {
            (char *) "/system/bin/init",
            (char *) "selinux_setup",
            0
        };

        tf_syscall3(
            SYS_EXECVE,
            (long) "/system/bin/init",
            (long) next_argv,
            (long) envp
        );

        tf_transition_failure(
            "android-selinux-exec"
        );
    }

    /*
     * Initial invocation from the kernel.
     */

    /*
     * Preserve the bundled debug-root payloads through Android's
     * FreeRamdisk(). These descriptors deliberately remain inherited
     * and non-CLOEXEC until TreeForge re-enters before selinux_setup.
     *
     * Retention failure is non-fatal here: canonical Android must
     * remain bootable even when root realization is unavailable.
     */
    long adb_debug_fd = tf_open(
        "/adb_debug.prop",
        O_RDONLY
    );

    if (
        adb_debug_fd >= 0
        && adb_debug_fd
        != TREEFORGE_ADB_DEBUG_FD
    ) {
        long adb_debug_duplicate = tf_syscall3(
            SYS_DUP3,
            adb_debug_fd,
            TREEFORGE_ADB_DEBUG_FD,
            0
        );

        tf_close(
            adb_debug_fd
        );

        if (adb_debug_duplicate < 0) {
            tf_close(
                TREEFORGE_ADB_DEBUG_FD
            );
        }
    }

    long userdebug_sepolicy_fd = tf_open(
        "/userdebug_plat_sepolicy.cil",
        O_RDONLY
    );

    if (
        userdebug_sepolicy_fd >= 0
        && userdebug_sepolicy_fd
        != TREEFORGE_USERDEBUG_SEPOLICY_FD
    ) {
        long userdebug_sepolicy_duplicate = tf_syscall3(
            SYS_DUP3,
            userdebug_sepolicy_fd,
            TREEFORGE_USERDEBUG_SEPOLICY_FD,
            0
        );

        tf_close(
            userdebug_sepolicy_fd
        );

        if (userdebug_sepolicy_duplicate < 0) {
            tf_close(
                TREEFORGE_USERDEBUG_SEPOLICY_FD
            );
        }
    }

    /*
     * Preserve the exact validated dynamic Recovery runtime through
     * Android's FreeRamdisk().
     *
     * The concrete file population is generated by Bootstrap from the
     * runtime-provider rootfs. Retention remains non-fatal to ordinary
     * Android boot; an incomplete population fails closed if Recovery
     * is explicitly selected.
     */
    for (
        int index = 0;
        index < TREEFORGE_RECOVERY_RUNTIME_FILE_COUNT;
        index++
    ) {
        long runtime_fd = tf_open(
            tf_recovery_runtime_files[
                index
            ].source_path,
            O_RDONLY
        );

        int target_fd = (
            TREEFORGE_RECOVERY_RUNTIME_FD_BASE
            + index
        );

        if (runtime_fd < 0) {
            /*
             * Never allow an unrelated inherited descriptor occupying
             * this reserved slot to masquerade as provider content.
             */
            tf_close(
                target_fd
            );

            continue;
        }

        if (runtime_fd == target_fd) {
            continue;
        }

        long runtime_duplicate = tf_syscall3(
            SYS_DUP3,
            runtime_fd,
            target_fd,
            0
        );

        tf_close(
            runtime_fd
        );

        if (runtime_duplicate < 0) {
            /*
             * Leave this target definitively unavailable. Explicit
             * Recovery realization will detect the incomplete
             * population rather than consuming an unrelated FD.
             */
            tf_close(
                target_fd
            );

            continue;
        }
    }

    /*
     * Preserve the separately generated recovery runtime through
     * Android's FreeRamdisk().
     *
     * Retention failure is deliberately non-fatal for ordinary Android
     * boot. An explicit recovery-test request will simply be unable to
     * enter the runtime.
     */
    long recovery_fd = tf_open(
        "/treeforge-recovery",
        O_RDONLY
    );

    if (
        recovery_fd >= 0
        && recovery_fd
        != TREEFORGE_RECOVERY_FD
    ) {
        long recovery_duplicate = tf_syscall3(
            SYS_DUP3,
            recovery_fd,
            TREEFORGE_RECOVERY_FD,
            0
        );

        tf_close(
            recovery_fd
        );

        if (recovery_duplicate < 0) {
            tf_close(
                TREEFORGE_RECOVERY_FD
            );
        }
    }

    /*
     * Preserve this exact TreeForge executable through Android's
     * FreeRamdisk() by holding an inherited non-CLOEXEC descriptor.
     */
    long self_fd = tf_open(
        "/init",
        O_RDONLY
    );

    if (self_fd < 0) {
        tf_transition_failure(
            "transition-fd-open"
        );
    }

    if (
        self_fd
        != TREEFORGE_TRANSITION_FD
    ) {
        long duplicated = tf_syscall3(
            SYS_DUP3,
            self_fd,
            TREEFORGE_TRANSITION_FD,
            0
        );

        if (duplicated < 0) {
            tf_close(
                self_fd
            );

            tf_transition_failure(
                "transition-fd-duplicate"
            );
        }

        tf_close(
            self_fd
        );
    }

    /*
     * Run the canonical Android init with only its unique final
     * /system/bin/init transition literal redirected.
     */
    char *first_stage_argv[] = {
        (char *) "/init",
        0
    };

    tf_syscall3(
        SYS_EXECVE,
        (long) "/init.treeforge-first-stage",
        (long) first_stage_argv,
        (long) envp
    );

    tf_transition_failure(
        "first-stage-exec"
    );
}

__attribute__((used, noreturn))
static void tf_entry(
    usize *initial_stack
) {
    long argc = (
        (long) initial_stack[0]
    );

    char **argv = (
        (char **) (
            initial_stack
            + 1
        )
    );

    char **envp = (
        argv
        + argc
        + 1
    );

    tf_main(
        argc,
        argv,
        envp
    );
}

__attribute__((naked, noreturn))
void _start(void) {
    __asm__ volatile(
        "mov x0, sp\n"
        "b tf_entry\n"
    );
}

'''

    @classmethod
    def _elf_machine(
        cls,
        data: bytes,
    ) -> int:
        if (
            not isinstance(
                data,
                bytes,
            )
            or len(data) < 20
        ):
            raise AndroidBootstrapEarlyDispatcherError(
                "canonical init payload is too small to be ELF"
            )

        if data[:4] != b"\x7fELF":
            raise AndroidBootstrapEarlyDispatcherError(
                "canonical init payload is not ELF"
            )

        if data[4] != 2:
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge early dispatcher currently requires "
                "a canonical ELF64 init"
            )

        if data[5] != 1:
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge early dispatcher currently requires "
                "a little-endian canonical init"
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
                raise AndroidBootstrapEarlyDispatcherError(
                    "TREEFORGE_CLANG does not reference an existing file: "
                    f"{candidate}"
                )

            return candidate

        discovered = shutil.which(
            "clang"
        )

        if discovered is None:
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge early dispatcher requires clang. "
                "Install clang or set TREEFORGE_CLANG."
            )

        return Path(
            discovered
        ).resolve()

    @staticmethod
    def _project_version() -> str:
        project_root = (
            Path(__file__)
            .resolve()
            .parents[3]
        )

        pyproject_path = (
            project_root
            / "pyproject.toml"
        )

        if not pyproject_path.is_file():
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge early dispatcher requires the canonical "
                "project version from pyproject.toml"
            )

        project = tomllib.loads(
            pyproject_path.read_text(
                encoding="utf-8",
            )
        )

        version = (
            project
            .get("project", {})
            .get("version")
        )

        if (
            not isinstance(version, str)
            or not version
        ):
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge project version must be a non-empty string"
            )

        if not all(
            character.isalnum()
            or character in ".+-_"
            for character
            in version
        ):
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge project version contains characters that "
                "cannot be embedded in the early dispatcher"
            )

        return version


    @classmethod
    def build(
        cls,
        *,
        canonical_init: bytes,
        retained_runtime_files: tuple[
            tuple[
                str,
                str,
                int,
            ],
            ...,
        ] = (),
        output_root: Path,
    ) -> AndroidBootstrapEarlyDispatcherBuild:
        if not isinstance(
            output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        if not isinstance(
            retained_runtime_files,
            tuple,
        ):
            raise TypeError(
                "retained_runtime_files must be a tuple"
            )

        if (
            len(retained_runtime_files)
            > 32
        ):
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge retained Recovery runtime exceeds the "
                "32-descriptor reserved capacity: "
                f"{len(retained_runtime_files)}"
            )

        normalized_runtime_files = []

        for value in retained_runtime_files:
            if (
                not isinstance(value, tuple)
                or len(value) != 3
            ):
                raise TypeError(
                    "retained runtime entries must be "
                    "(source_path, destination_path, mode) tuples"
                )

            (
                source_path_value,
                destination_path_value,
                mode,
            ) = value

            if (
                not isinstance(source_path_value, str)
                or not source_path_value.startswith("/")
                or "/../" in source_path_value
                or source_path_value.endswith("/..")
            ):
                raise AndroidBootstrapEarlyDispatcherError(
                    "invalid retained Recovery runtime source path: "
                    f"{source_path_value!r}"
                )

            if (
                not isinstance(destination_path_value, str)
                or not destination_path_value.startswith(
                    "/dev/treeforge-recovery-runtime/"
                )
                or "/../" in destination_path_value
                or destination_path_value.endswith("/..")
            ):
                raise AndroidBootstrapEarlyDispatcherError(
                    "invalid retained Recovery runtime destination path: "
                    f"{destination_path_value!r}"
                )

            if (
                not isinstance(mode, int)
                or mode <= 0
                or mode > 0o777
            ):
                raise AndroidBootstrapEarlyDispatcherError(
                    "invalid retained Recovery runtime mode: "
                    f"{mode!r}"
                )

            for path_value in (
                source_path_value,
                destination_path_value,
            ):
                if any(
                    ord(character) < 0x20
                    or ord(character) > 0x7e
                    for character in path_value
                ):
                    raise AndroidBootstrapEarlyDispatcherError(
                        "retained Recovery runtime paths must be "
                        "printable ASCII"
                    )

            normalized_runtime_files.append(
                (
                    source_path_value,
                    destination_path_value,
                    mode,
                )
            )

        machine = cls._elf_machine(
            canonical_init
        )

        if (
            machine
            != cls.ELF_MACHINE_AARCH64
        ):
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge early dispatcher does not yet have a "
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
            / "treeforge-early-dispatch.c"
        )

        executable_path = (
            output_root
            / "treeforge-early-dispatch"
        )

        project_version = (
            cls._project_version()
        )

        if (
            cls._SOURCE.count(
                "__TREEFORGE_VERSION__"
            )
            != 1
        ):
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge early dispatcher version placeholder "
                "must occur exactly once"
            )

        source_text = (
            cls._SOURCE.replace(
                "__TREEFORGE_VERSION__",
                project_version,
                1,
            )
        )

        def c_string_literal(
            value: str,
        ) -> str:
            escaped = (
                value
                .replace(
                    "\\",
                    "\\\\",
                )
                .replace(
                    '"',
                    '\\\"',
                )
            )

            return (
                '"'
                + escaped
                + '"'
            )

        runtime_table_lines = []

        for (
            source_runtime_path,
            destination_runtime_path,
            mode,
        ) in normalized_runtime_files:
            runtime_table_lines.append(
                (
                    "    { "
                    + c_string_literal(
                        source_runtime_path
                    )
                    + ", "
                    + c_string_literal(
                        destination_runtime_path
                    )
                    + ", "
                    + f"0{mode:o}"
                    + " },"
                )
            )

        if not runtime_table_lines:
            runtime_table_lines.append(
                "    { 0, 0, 0 },"
            )

        generated_source = source_text

        count_token = (
            "__TREEFORGE_RECOVERY_RUNTIME_FILE_COUNT__"
        )

        table_token = (
            "__TREEFORGE_RECOVERY_RUNTIME_FILE_TABLE__"
        )

        if generated_source.count(
            count_token
        ) != 1:
            raise AndroidBootstrapEarlyDispatcherError(
                "retained Recovery runtime count token is not unique"
            )

        if generated_source.count(
            table_token
        ) != 1:
            raise AndroidBootstrapEarlyDispatcherError(
                "retained Recovery runtime table token is not unique"
            )

        generated_source = generated_source.replace(
            count_token,
            str(
                len(
                    normalized_runtime_files
                )
            ),
            1,
        )

        generated_source = generated_source.replace(
            table_token,
            "\n".join(
                runtime_table_lines
            ),
            1,
        )

        source_path.write_text(
            generated_source,
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
            raise AndroidBootstrapEarlyDispatcherError(
                "unable to build TreeForge early dispatcher:\n"
                + completed.stderr.decode(
                    "utf-8",
                    errors="replace",
                )
            )

        if not executable_path.is_file():
            raise AndroidBootstrapEarlyDispatcherError(
                "clang completed without producing the "
                "TreeForge early dispatcher"
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
            raise AndroidBootstrapEarlyDispatcherError(
                "TreeForge early dispatcher architecture does not "
                "match canonical init architecture"
            )

        executable_path.chmod(
            0o755
        )

        return AndroidBootstrapEarlyDispatcherBuild(
            source_path=source_path,
            executable_path=executable_path,
            compiler_path=compiler,
            elf_machine=machine,
            target_triple=target_triple,
        )


__all__ = (
    "AndroidBootstrapEarlyDispatcherBuild",
    "AndroidBootstrapEarlyDispatcherBuilder",
    "AndroidBootstrapEarlyDispatcherError",
)
