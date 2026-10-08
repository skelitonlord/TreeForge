#!/usr/bin/env bash
#
# TreeForge non-interactive setup
#
# Intended for CI, containers, automation, and advanced users.
# The interactive setup.sh script delegates installation work to this file.
#

set -Eeuo pipefail

PROGRAM_NAME="$(basename "$0")"

DEFAULT_INSTALL_DIR="${HOME}/development/treeforge"
DEFAULT_PYTHON="python3"

TREEFORGE_PUBLIC_REPO_URL="${TREEFORGE_PUBLIC_REPO_URL:-https://github.com/skelitonlord/TreeForge}"
TREEFORGE_PRIVATE_REPO_URL="${TREEFORGE_PRIVATE_REPO_URL:-git@github.com:Skellyaosp/TreeForge.git}"

REPO_SOURCE="${TREEFORGE_REPO_SOURCE:-public}"
REPO_URL="${TREEFORGE_REPO_URL:-}"
REPO_URL_EXPLICIT=false
INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
PYTHON_BIN="${DEFAULT_PYTHON}"

INSTALL_MODE="user"
DETECTED_DISTRO=""
SKIP_SYSTEM=false
SKIP_UPDATE=false
RUN_TESTS=false
QUIET=false

CURRENT_STEP=0
TOTAL_STEPS=7

# Installation profiles are cumulative:
#
#   user
#     Runtime required to use an existing TreeForge-supported tree and
#     downstream/end-user functionality.
#
#   maintainer
#     Everything in user, plus the complete device bring-up pipeline:
#     factory-image intake, extraction, parsing, reconstruction, Device Tree,
#     and AOSP integration.
#
#   developer
#     Everything in maintainer, plus tooling required to develop, validate,
#     package, and maintain TreeForge itself.
#
# Downgrading a mode never removes already-installed system packages.

COMMON_APT_PACKAGES=(
    bash
    sudo
    coreutils
    util-linux
    grep
    sed
    gawk
    xdg-utils
    hostname

    git
    openssh-client
    ca-certificates
    curl
    gh
    repo

    openssl

    python3
    python3-pip
    python3-venv
)

USER_APT_PACKAGES=(
    clang
    lld
)

MAINTAINER_APT_PACKAGES=(
    python3-dev
    build-essential
    git-lfs
    pkg-config

    unzip
    zip
    p7zip-full
    xz-utils
    cpio
    lz4
    zstd
    file

    e2fsprogs
    erofs-utils

    git-core
    gnupg
    flex
    bison
    zlib1g-dev
    libc6-dev-i386
    x11proto-core-dev
    libx11-dev
    lib32z1-dev
    libgl1-mesa-dev
    libxml2-utils
    xsltproc
    fontconfig
)

DEVELOPER_APT_PACKAGES=(
)

# -------------------------------------------------------------------------
# Alpine apk package equivalents
#
# Each array mirrors its apt counterpart above. Package names differ
# between Debian/Ubuntu and Alpine; the mapping is documented inline.
#
# Packages with no Alpine equivalent:
#   libc6-dev-i386  -- glibc 32-bit multilib; Alpine uses musl.
#   lib32z1-dev     -- 32-bit zlib for glibc multilib.
# These are omitted. Full AOSP source builds requiring 32-bit host
# support need a glibc-based container.
# -------------------------------------------------------------------------

COMMON_APK_PACKAGES=(
    bash
    sudo
    coreutils
    util-linux
    grep
    sed
    gawk
    xdg-utils
    # hostname is provided by busybox on Alpine.

    git
    openssh-client
    ca-certificates
    curl
    github-cli          # Debian: gh
    # repo is not packaged; installed manually below.

    openssl

    python3
    py3-pip             # Debian: python3-pip
    # python3-venv is included in Alpine's python3 package.
)

USER_APK_PACKAGES=(
    clang
    lld
    gcompat             # glibc compatibility for pre-built Android host binaries.
)

MAINTAINER_APK_PACKAGES=(
    python3-dev
    build-base          # Debian: build-essential
    git-lfs
    pkgconf             # Debian: pkg-config

    unzip
    zip
    7zip                # Debian: p7zip-full
    xz                  # Debian: xz-utils
    cpio
    lz4
    zstd
    file

    e2fsprogs
    erofs-utils

    # git-core is redundant; git is already in COMMON.
    gnupg
    flex
    bison
    zlib-dev            # Debian: zlib1g-dev
    xorgproto           # Debian: x11proto-core-dev
    libx11-dev
    mesa-dev            # Debian: libgl1-mesa-dev
    libxml2-utils
    libxslt             # Debian: xsltproc (provides xsltproc binary)
    fontconfig
)

DEVELOPER_APK_PACKAGES=(
)

DEVELOPER_PYTHON_PACKAGES=(
    pytest
    pytest-cov
    ruff
    black
    mypy
    types-lxml
    build
)

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    BOLD=$'\033[1m'
    BLUE=$'\033[1;34m'
    GREEN=$'\033[1;32m'
    YELLOW=$'\033[1;33m'
    RED=$'\033[1;31m'
    RESET=$'\033[0m'
else
    BOLD=""
    BLUE=""
    GREEN=""
    YELLOW=""
    RED=""
    RESET=""
fi

info() {
    printf '%s%s==>%s %s\n' "${BOLD}" "${BLUE}" "${RESET}" "$*"
}

success() {
    printf '%s✓%s %s\n' "${GREEN}" "${RESET}" "$*"
}

warn() {
    printf '%s!%s %s\n' "${YELLOW}" "${RESET}" "$*" >&2
}

fail() {
    printf '%sERROR:%s %s\n' "${RED}" "${RESET}" "$*" >&2
    exit 1
}

step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    printf '\n%s[%d/%d]%s %s\n' \
        "${BLUE}" \
        "${CURRENT_STEP}" \
        "${TOTAL_STEPS}" \
        "${RESET}" \
        "$*"
}

run() {
    if "${QUIET}"; then
        "$@" >/dev/null
    else
        "$@"
    fi
}

usage() {
    cat <<EOF
TreeForge non-interactive setup

Usage:
  ${PROGRAM_NAME} [options]

Repository source:

  --repo-source SOURCE
      TreeForge predefined source: public or private.
      Default: public

  --repo-url URL
      Explicit HTTPS/SSH TreeForge repository URL.

      User mode:
        Must equal a predefined TreeForge public/private source.

      Maintainer/Developer:
        Arbitrary HTTPS/SSH repository URLs are allowed.

Options:

  --install-dir PATH
      Installation directory.
      Default: ${DEFAULT_INSTALL_DIR}

  --python COMMAND
      Python interpreter.
      Default: ${DEFAULT_PYTHON}

  --mode MODE
      user, maintainer, or developer.
      Default: user

  --dev
      Legacy alias for --mode developer.

  --skip-system
      Do not install operating-system packages.

  --skip-update
      Do not update an existing clean checkout.

  --run-tests
      Run pytest -q after installation.

  --quiet
      Reduce apt, pip, and repository output.

  -h, --help
      Show this help.

ADB, Fastboot, and other Android-derived host tools are TreeForge provider
artifacts and are not installed through apt.

Interactive Android/AOSP source selection is handled by setup.sh.
EOF
}


validate_install_mode() {
    case "${INSTALL_MODE}" in
        user|maintainer|developer)
            ;;
        *)
            fail \
                "Invalid installation mode '${INSTALL_MODE}'. Expected: user, maintainer, or developer."
            ;;
    esac
}


resolve_apt_packages() {
    APT_PACKAGES=(
        "${COMMON_APT_PACKAGES[@]}"
        "${USER_APT_PACKAGES[@]}"
    )

    case "${INSTALL_MODE}" in
        user)
            ;;
        maintainer)
            APT_PACKAGES+=(
                "${MAINTAINER_APT_PACKAGES[@]}"
            )
            ;;
        developer)
            APT_PACKAGES+=(
                "${MAINTAINER_APT_PACKAGES[@]}"
                "${DEVELOPER_APT_PACKAGES[@]}"
            )
            ;;
        *)
            fail \
                "Cannot resolve packages for unknown mode: ${INSTALL_MODE}"
            ;;
    esac
}


resolve_apk_packages() {
    APK_PACKAGES=(
        "${COMMON_APK_PACKAGES[@]}"
        "${USER_APK_PACKAGES[@]}"
    )

    case "${INSTALL_MODE}" in
        user)
            ;;
        maintainer)
            APK_PACKAGES+=(
                "${MAINTAINER_APK_PACKAGES[@]}"
            )
            ;;
        developer)
            APK_PACKAGES+=(
                "${MAINTAINER_APK_PACKAGES[@]}"
                "${DEVELOPER_APK_PACKAGES[@]}"
            )
            ;;
        *)
            fail \
                "Cannot resolve packages for unknown mode: ${INSTALL_MODE}"
            ;;
    esac
}


mode_supports_bringup() {
    [[ "${INSTALL_MODE}" == "maintainer" \
        || "${INSTALL_MODE}" == "developer" ]]
}


mode_supports_maintenance() {
    [[ "${INSTALL_MODE}" == "developer" ]]
}


command_exists() {
    command -v "$1" >/dev/null 2>&1
}

version_at_least() {
    local actual="$1"
    local required="$2"

    printf '%s\n%s\n' "${required}" "${actual}" | sort -V -C
}

expand_path() {
    local path="$1"

    case "${path}" in
        "~")
            printf '%s\n' "${HOME}"
            ;;
        "~/"*)
            printf '%s/%s\n' "${HOME}" "${path#~/}"
            ;;
        *)
            printf '%s\n' "${path}"
            ;;
    esac
}

detect_platform() {
    [[ -r /etc/os-release ]] \
        || fail "Cannot identify this Linux distribution."

    # shellcheck disable=SC1091
    source /etc/os-release

    case "${ID:-}" in
        alpine)
            DETECTED_DISTRO="alpine"
            ;;
        ubuntu|debian)
            DETECTED_DISTRO="debian"
            ;;
        *)
            if [[ "${ID_LIKE:-}" == *debian* ]]; then
                DETECTED_DISTRO="debian"
            else
                fail \
                    "Unsupported distribution. Expected: Alpine, Ubuntu, or Debian-compatible. Detected: ${PRETTY_NAME:-unknown}"
            fi
            ;;
    esac

    success "Detected ${PRETTY_NAME:-Linux} (${DETECTED_DISTRO} family)"
}

# Resolved at runtime in require_priv_esc(); exported so subshells inherit it.
_PRIV=""

require_priv_esc() {
    if [[ "${EUID}" -eq 0 ]]; then
        warn "Running the complete setup as root is not recommended."
        _PRIV=""
        return
    fi

    if command_exists doas; then
        _PRIV="doas"
    elif command_exists sudo; then
        _PRIV="sudo"
    else
        fail "Neither doas nor sudo found; one is required to install system packages."
    fi

    # Validate credentials early so later steps do not prompt mid-run.
    ${_PRIV} true
}

install_system_packages_apt() {
    export DEBIAN_FRONTEND=noninteractive

    info \
        "Updating apt package metadata"

    run \
        ${_PRIV} apt-get update

    resolve_apt_packages

    info \
        "Installing ${INSTALL_MODE} mode system dependencies"

    run \
        ${_PRIV} apt-get install -y \
        "${APT_PACKAGES[@]}"
}


enable_alpine_community_repo() {
    if grep -q '^[^#].*community' /etc/apk/repositories 2>/dev/null; then
        return
    fi

    local mirror
    mirror="$(grep -m1 '^http' /etc/apk/repositories | sed 's|/main.*|/community|')"
    if [[ -n "${mirror}" ]]; then
        info "Enabling Alpine community repository"
        printf '%s\n' "${mirror}" | ${_PRIV} tee -a /etc/apk/repositories >/dev/null
    fi
}


install_repo_tool() {
    local repo_bin="/usr/local/bin/repo"

    if [[ -x "${repo_bin}" ]]; then
        success "Android repo tool already installed"
        return
    fi

    info "Installing Android repo tool"
    ${_PRIV} curl -fsSL -o "${repo_bin}" \
        https://storage.googleapis.com/git-repo-downloads/repo
    ${_PRIV} chmod 755 "${repo_bin}"
    success "Android repo tool installed"
}


install_system_packages_apk() {
    enable_alpine_community_repo

    info \
        "Updating apk package index"

    run \
        ${_PRIV} apk update

    resolve_apk_packages

    info \
        "Installing ${INSTALL_MODE} mode system dependencies"

    run \
        ${_PRIV} apk add --no-cache \
        "${APK_PACKAGES[@]}"

    # The Google repo tool is not packaged in Alpine repositories.
    install_repo_tool
}


install_system_packages() {
    if "${SKIP_SYSTEM}"; then
        warn \
            "System package installation skipped."

        return
    fi

    detect_platform
    require_priv_esc

    case "${DETECTED_DISTRO}" in
        alpine)
            install_system_packages_apk
            ;;
        debian)
            install_system_packages_apt
            ;;
        *)
            fail "No package installation path for distro: ${DETECTED_DISTRO}"
            ;;
    esac
}


check_python() {
    command_exists "${PYTHON_BIN}" \
        || fail "Python interpreter not found: ${PYTHON_BIN}"

    local python_version
    python_version="$(
        "${PYTHON_BIN}" -c \
            'import sys; print(".".join(map(str, sys.version_info[:3])))'
    )"

    version_at_least "${python_version}" "3.11" \
        || fail "TreeForge requires Python 3.11 or newer. Found ${python_version}."

    success "Using ${PYTHON_BIN} ${python_version}"
}

validate_repo_source() {
    case "${REPO_SOURCE}" in
        public|private)
            ;;
        *)
            fail \
                "Invalid repository source '${REPO_SOURCE}'. Expected: public or private."
            ;;
    esac
}


resolve_repo_url() {
    if "${REPO_URL_EXPLICIT}" || [[ -n "${REPO_URL}" ]]; then
        return
    fi

    case "${REPO_SOURCE}" in
        public)
            REPO_URL="${TREEFORGE_PUBLIC_REPO_URL}"
            ;;
        private)
            REPO_URL="${TREEFORGE_PRIVATE_REPO_URL}"
            ;;
        *)
            fail \
                "Cannot resolve repository URL for source: ${REPO_SOURCE}"
            ;;
    esac
}


validate_repo_url() {
    [[ -n "${REPO_URL}" ]] \
        || fail \
            "--repo-url is required."

    case "${REPO_URL}" in
        https://*|ssh://*|git@*:*)
            ;;
        *)
            fail \
                "TreeForge repository URLs must use HTTPS or SSH: ${REPO_URL}"
            ;;
    esac

    if [[ "${INSTALL_MODE}" == "user" \
        && "${REPO_URL}" != "${TREEFORGE_PUBLIC_REPO_URL}" \
        && "${REPO_URL}" != "${TREEFORGE_PRIVATE_REPO_URL}" ]]; then

        fail \
            "User mode accepts only TreeForge-defined public/private repository sources."
    fi
}


clone_or_update_repository() {
    local parent_dir
    parent_dir="$(dirname "${INSTALL_DIR}")"
    mkdir -p "${parent_dir}"

    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        success "Existing checkout found at ${INSTALL_DIR}"

        local current_remote
        current_remote="$(
            git -C "${INSTALL_DIR}" remote get-url origin 2>/dev/null || true
        )"

        if [[ -n "${current_remote}" && "${current_remote}" != "${REPO_URL}" ]]; then
            warn "Existing origin differs from the supplied repository URL."
            warn "Existing: ${current_remote}"
            warn "Supplied: ${REPO_URL}"
        fi

        if "${SKIP_UPDATE}"; then
            warn "Repository update skipped."
            return
        fi

        if [[ -n "$(git -C "${INSTALL_DIR}" status --porcelain)" ]]; then
            warn "Local changes detected; git pull was skipped."
            return
        fi

        info "Updating the existing checkout"
        run git -C "${INSTALL_DIR}" pull --ff-only
        success "Repository updated"
        return
    fi

    [[ ! -e "${INSTALL_DIR}" ]] \
        || fail "Install path exists but is not a Git repository: ${INSTALL_DIR}"

    info "Cloning ${REPO_URL}"
    run git clone "${REPO_URL}" "${INSTALL_DIR}"
    success "Repository cloned"
}

create_virtual_environment() {
    local venv_dir="${INSTALL_DIR}/.venv"

    if [[ -d "${venv_dir}" ]]; then
        [[ -x "${venv_dir}/bin/python" ]] \
            || fail "Existing virtual environment is incomplete: ${venv_dir}"

        success "Existing virtual environment found"
        return
    fi

    run "${PYTHON_BIN}" -m venv "${venv_dir}"
    success "Virtual environment created"
}

install_treeforge() {
    local venv_python="${INSTALL_DIR}/.venv/bin/python"

    info "Upgrading packaging tools"
    run "${venv_python}" -m pip install --upgrade pip setuptools wheel

    info "Installing TreeForge"
    run "${venv_python}" -m pip install -e "${INSTALL_DIR}"

    if mode_supports_maintenance; then
        info "Installing TreeForge developer Python tools"
        run "${venv_python}" -m pip install "${DEVELOPER_PYTHON_PACKAGES[@]}"
    fi

    success "Python packages installed"
}

create_working_directories() {
    mkdir -p \
        "${INSTALL_DIR}/images" \
        "${INSTALL_DIR}/logs" \
        "${INSTALL_DIR}/workspace" \
        "${INSTALL_DIR}/output" \
        "${INSTALL_DIR}/aosp" \
        "${HOME}/treeforge-input" \
        "${HOME}/treeforge-output"

    success "Working directories created"
}

check_required_command() {
    local command_name="$1"
    local guidance="$2"

    if command_exists "${command_name}"; then
        success "Found ${command_name}: $(command -v "${command_name}")"
        return
    fi

    fail "${command_name} not found. ${guidance}"
}


check_optional_command() {
    local command_name="$1"
    local guidance="$2"

    if command_exists "${command_name}"; then
        success "Found ${command_name}: $(command -v "${command_name}")"
    else
        warn "${command_name} not found. ${guidance}"
    fi
}

verify_installation() {
    local venv_python="${INSTALL_DIR}/.venv/bin/python"
    local treeforge_bin="${INSTALL_DIR}/.venv/bin/treeforge"

    "${venv_python}" -c \
        "import treeforge; print('TreeForge Python import OK')"

    [[ -x "${treeforge_bin}" ]] \
        || fail \
            "TreeForge CLI was not installed."

    "${treeforge_bin}" version
    "${treeforge_bin}" doctor

    printf '\nTreeForge-owned Android host providers:\n'

    "${venv_python}" \
        -m treeforge.setup.host_providers

    printf '\nNative host prerequisites:\n'

    check_required_command \
        clang \
        "Install clang; TreeForge builds freestanding arm64 runtime helpers with Clang."

    check_required_command \
        ld.lld \
        "Install lld; TreeForge invokes Clang with -fuse-ld=lld."

    check_required_command \
        openssl \
        "Install openssl for selected signing-key generation."

    printf '\nFilesystem inspection tools:\n'

    check_optional_command \
        debugfs \
        "Install e2fsprogs for ext filesystem inspection."

    check_optional_command \
        dumpe2fs \
        "Install e2fsprogs for ext filesystem inspection."

    check_optional_command \
        dump.erofs \
        "Install erofs-utils for EROFS inspection."

    check_optional_command \
        fsck.erofs \
        "Install erofs-utils for EROFS inspection."

    success \
        "TreeForge verification completed"
}


run_test_suite() {
    if ! "${RUN_TESTS}"; then
        success "Test run not requested"
        return
    fi

    if [[ ! -x "${INSTALL_DIR}/.venv/bin/pytest" ]]; then
        fail "--run-tests requires --mode developer so pytest is installed."
    fi

    (
        cd "${INSTALL_DIR}"
        "${INSTALL_DIR}/.venv/bin/pytest" -q
    )

    success "Test suite passed"
}

print_summary() {
    cat <<EOF

${GREEN}${BOLD}=====================================
 TreeForge Setup Complete
=====================================${RESET}

Repository:
  ${INSTALL_DIR}

Installation mode:
  ${INSTALL_MODE}

Activate TreeForge:
  cd "${INSTALL_DIR}"
  source .venv/bin/activate

Check the CLI:
  treeforge --help
  treeforge version
  treeforge doctor

Android host tooling:
  TreeForge-owned provider bundles

Android/AOSP source selection:
  Use interactive setup.sh when build/validation checkout configuration is needed.
EOF

    if mode_supports_maintenance; then
        cat <<EOF

Development checks:
  pytest -q
  ruff check .
  black --check .
  mypy treeforge
EOF
    fi
}


on_error() {
    local exit_code=$?
    local line_number="${1:-unknown}"

    printf '\n%sSetup failed%s at line %s with exit code %s.\n' \
        "${RED}" \
        "${RESET}" \
        "${line_number}" \
        "${exit_code}" >&2

    exit "${exit_code}"
}

trap 'on_error "$LINENO"' ERR

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-source)
            [[ $# -ge 2 ]] || fail "--repo-source requires a value."
            REPO_SOURCE="$2"
            shift 2
            ;;
        --repo-url)
            [[ $# -ge 2 ]] || fail "--repo-url requires a value."
            REPO_URL="$2"
            REPO_URL_EXPLICIT=true
            shift 2
            ;;
        --install-dir)
            [[ $# -ge 2 ]] || fail "--install-dir requires a value."
            INSTALL_DIR="$2"
            shift 2
            ;;
        --python)
            [[ $# -ge 2 ]] || fail "--python requires a value."
            PYTHON_BIN="$2"
            shift 2
            ;;
        --mode)
            [[ $# -ge 2 ]] || fail "--mode requires a value."
            INSTALL_MODE="$2"
            shift 2
            ;;
        --dev)
            warn "--dev is deprecated; treating it as --mode developer."
            INSTALL_MODE="developer"
            shift
            ;;
        --skip-system)
            SKIP_SYSTEM=true
            shift
            ;;
        --skip-update)
            SKIP_UPDATE=true
            shift
            ;;
        --run-tests)
            RUN_TESTS=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "Unknown argument: $1"
            ;;
    esac
done

INSTALL_DIR="$(expand_path "${INSTALL_DIR}")"

validate_install_mode
validate_repo_source
resolve_repo_url
validate_repo_url

step "Checking host environment"
check_python

step "Installing system dependencies"
install_system_packages
check_python

step "Preparing the TreeForge repository"
clone_or_update_repository

step "Creating the Python environment"
create_virtual_environment

step "Installing TreeForge"
install_treeforge

step "Creating directories and verifying tools"
create_working_directories
verify_installation

step "Running requested tests"
run_test_suite

print_summary
