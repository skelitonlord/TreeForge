#!/usr/bin/env bash
#
# TreeForge setup
#
# Self-contained guided installer/updater for Ubuntu/Debian hosts.
# Android 15 r36 AOSP build dependencies are based on Google's current
# AOSP setup requirements, using current direct Ubuntu package names where
# Google still documents transitional aliases.
#

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    printf '%s\n' \
        "TreeForge setup must be executed, not sourced." \
        "Run:" \
        "  ./setup.sh" \
        >&2
    return 1
fi

set -Eeuo pipefail

PROGRAM_NAME="$(basename "$0")"
DEFAULT_INSTALL_DIR="${TREEFORGE_INSTALL_DIR:-${HOME}/development/treeforge}"
DEFAULT_DEV_BRANCH="${TREEFORGE_DEV_BRANCH:-development}"

TREEFORGE_PUBLIC_REPO_URL="${TREEFORGE_PUBLIC_REPO_URL:-https://github.com/skelitonlord/TreeForge}"
TREEFORGE_PRIVATE_REPO_URL="${TREEFORGE_PRIVATE_REPO_URL:-git@github.com:Skellyaosp/TreeForge.git}"
DEFAULT_REPO_URL="${TREEFORGE_REPO_URL:-}"
DEFAULT_REPO_SOURCE="${TREEFORGE_REPO_SOURCE:-public}"

TREEFORGE_PUBLIC_AOSP_MANIFEST_URL="${TREEFORGE_PUBLIC_AOSP_MANIFEST_URL:-https://github.com/skelitonlord/treeforge_platform_manifest}"
TREEFORGE_PRIVATE_AOSP_MANIFEST_URL="${TREEFORGE_PRIVATE_AOSP_MANIFEST_URL:-git@github.com:Skellyaosp/treeforge_platform_manifest.git}"
GOOGLE_AOSP_MANIFEST_URL="${GOOGLE_AOSP_MANIFEST_URL:-https://android.googlesource.com/platform/manifest}"
GOOGLE_VENDOR_BINARIES_URL="${GOOGLE_VENDOR_BINARIES_URL:-https://developers.google.com/android/drivers}"
DEFAULT_AOSP_MANIFEST_URL="${TREEFORGE_AOSP_MANIFEST_URL:-}"
DEFAULT_AOSP_MANIFEST_SOURCE="${TREEFORGE_AOSP_MANIFEST_SOURCE:-public}"
AOSP_SYNC_JOBS="${TREEFORGE_AOSP_SYNC_JOBS:-8}"
AOSP_SYNC_RETRY_FETCHES="${TREEFORGE_AOSP_SYNC_RETRY_FETCHES:-10}"
AOSP_REMOVAL_LEDGER_RELATIVE_PATH="local_manifests/00-treeforge-removed-projects.xml"
AOSP_SLIM_V1_MARKER_RELATIVE_PATH=".repo/treeforge-slim-checkout-v1"
AOSP_SLIM_MARKER_RELATIVE_PATH=".repo/treeforge-slim-checkout-v2"

ANDROID_15_NAME="Android 15"
ANDROID_15_TAG="android-15.0.0_r36"
ANDROID_15_MANIFEST_BRANCH="${TREEFORGE_ANDROID_15_MANIFEST_BRANCH:-development}"
ANDROID_15_MANIFEST_NAME="default.xml"
ANDROID_15_GOOGLE_MANIFEST_REVISION="${TREEFORGE_ANDROID_15_GOOGLE_MANIFEST_REVISION:-android-15.0.0_r36}"
ANDROID_15_LUNCH_TARGET="aosp_tangorpro-trunk_staging-userdebug"

# setup.sh itself may call these commands before TreeForge exists.
BOOTSTRAP_APT_PACKAGES=(
    bash
    sudo
    coreutils
    util-linux
    grep
    sed
    gawk
    xdg-utils
    hostname
    systemd
    libc-bin
    dpkg
    ca-certificates
    curl
    git
    openssh-client
    openssl
    python3
    python3-pip
    python3-venv
)

# TreeForge runtime/build-host dependencies which are not Android provider
# artifacts. Android-derived host tools such as adb, fastboot, mkbootimg,
# lpdump, avbtool, and mkdtimg remain TreeForge-owned providers.
TREEFORGE_USER_APT_PACKAGES=(
    clang
    lld
    e2fsprogs
)

TREEFORGE_MAINTAINER_APT_PACKAGES=(
    python3-dev
    build-essential
    git-lfs
    pkgconf
    unzip
    zip
    7zip
    xz-utils
    cpio
    lz4
    zstd
    file
    erofs-utils
)

TREEFORGE_DEVELOPER_PYTHON_PACKAGES=(
    pytest
    pytest-cov
    ruff
    black
    mypy
    types-lxml
    build
)

# Google's current AOSP package set for Ubuntu 18.04+ (docs updated 2026-06-17)
# uses the historical names git-core and x11proto-core-dev. On current Ubuntu,
# git is the actual Git package and x11proto-core-dev is only a transitional
# dummy package depending on x11proto-dev, so TreeForge installs the direct
# current names instead.
AOSP_BUILD_APT_PACKAGES=(
    gnupg
    flex
    bison
    build-essential
    zip
    curl
    zlib1g-dev
    libc6-dev-i386
    x11proto-dev
    libx11-dev
    lib32z1-dev
    libgl-dev
    libglvnd-dev
    libxml2-utils
    xsltproc
    unzip
    fontconfig
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

usage() {
    cat <<EOF
TreeForge setup

Usage:
  ${PROGRAM_NAME}

Installation modes:
  User        Supported-device/downstream TreeForge use.
  Maintainer  Adds reconstruction/new-device bring-up tooling.
  Developer   Adds TreeForge source-development/test/packaging tooling.

TreeForge repository sources:
  Public:   ${TREEFORGE_PUBLIC_REPO_URL}
  Private:  ${TREEFORGE_PRIVATE_REPO_URL}
  Custom:   Maintainer/Developer only; HTTPS or SSH.

Android 15 / ${ANDROID_15_TAG} AOSP manifest choices:
  TreeForge public:   ${TREEFORGE_PUBLIC_AOSP_MANIFEST_URL}
  TreeForge private:  ${TREEFORGE_PRIVATE_AOSP_MANIFEST_URL}
  Google canonical:  ${GOOGLE_AOSP_MANIFEST_URL}
  Custom:             Maintainer/Developer only.

Google canonical uses revision ${ANDROID_15_GOOGLE_MANIFEST_REVISION}.
TreeForge manifests use revision ${ANDROID_15_MANIFEST_BRANCH}.

TreeForge-specific removal-ledger/no-upstream-device validation applies only
when a TreeForge manifest is selected. Google canonical/custom manifests are
left structurally intact and receive generic AOSP validation.

AOSP build-host packages are installed when an AOSP checkout is configured.
The current direct Ubuntu package set is used rather than obsolete/transitional
aliases such as git-core and x11proto-core-dev.

TreeForge-owned Android host providers remain independent of AOSP and PATH.

After TreeForge itself is installed, setup resolves and verifies its exact
pinned Android provider releases from TreeForge's public toolchain repository.
The verified provider-backed adb and fastboot binaries can optionally be copied
to ~/.local/bin. Distro adb/fastboot packages are never required.

Environment overrides:
  TREEFORGE_INSTALL_DIR=PATH
  TREEFORGE_REPO_SOURCE=public|private
  TREEFORGE_REPO_URL=URL
  TREEFORGE_PUBLIC_REPO_URL=URL
  TREEFORGE_PRIVATE_REPO_URL=URL
  TREEFORGE_AOSP_MANIFEST_SOURCE=public|private|google
  TREEFORGE_AOSP_MANIFEST_URL=URL
  TREEFORGE_PUBLIC_AOSP_MANIFEST_URL=URL
  TREEFORGE_PRIVATE_AOSP_MANIFEST_URL=URL
  GOOGLE_AOSP_MANIFEST_URL=URL
  TREEFORGE_ANDROID_15_MANIFEST_BRANCH=REVISION
  TREEFORGE_ANDROID_15_GOOGLE_MANIFEST_REVISION=REVISION
  TREEFORGE_AOSP_SYNC_JOBS=N
  TREEFORGE_AOSP_SYNC_RETRY_FETCHES=N
  TREEFORGE_DEV_BRANCH=NAME
  TREEFORGE_PYTHON=COMMAND
  NO_COLOR=1
EOF
}

prompt_value() {
    local result_variable="$1"
    local label="$2"
    local default_value="${3:-}"
    local input_value=""

    if [[ -n "${default_value}" ]]; then
        read -r -p "${label} [${default_value}]: " input_value
        input_value="${input_value:-${default_value}}"
    else
        while [[ -z "${input_value}" ]]; do
            read -r -p "${label}: " input_value
            [[ -n "${input_value}" ]] || warn "A value is required."
        done
    fi

    printf -v "${result_variable}" '%s' "${input_value}"
}

prompt_yes_no() {
    local result_variable="$1"
    local label="$2"
    local default_answer="$3"
    local -n result_ref="${result_variable}"
    local response=""
    local suffix=""

    case "${default_answer}" in
        yes) suffix="Y/n" ;;
        no) suffix="y/N" ;;
        *) fail "Invalid prompt default: ${default_answer}" ;;
    esac

    while true; do
        read -r -p "${label} (${suffix}): " response
        response="${response,,}"
        response="${response:-${default_answer}}"
        case "${response}" in
            y|yes) result_ref=true; return ;;
            n|no) result_ref=false; return ;;
            *) warn "Please enter y or n." ;;
        esac
    done
}

prompt_choice() {
    local result_variable="$1"
    local label="$2"
    local default_choice="$3"
    local -n result_ref="${result_variable}"
    shift 3
    local valid_choices=("$@")
    local response=""
    local valid=""

    while true; do
        read -r -p "${label} [${default_choice}]: " response
        response="${response:-${default_choice}}"
        for valid in "${valid_choices[@]}"; do
            if [[ "${response}" == "${valid}" ]]; then
                result_ref="${response}"
                return
            fi
        done
        warn "Please choose one of: ${valid_choices[*]}"
    done
}

expand_path() {
    local value="$1"
    case "${value}" in
        "~") printf '%s\n' "${HOME}" ;;
        "~/"*) printf '%s/%s\n' "${HOME}" "${value#~/}" ;;
        *) printf '%s\n' "${value}" ;;
    esac
}

apt_package_installed() {
    local package="$1"
    [[ "$(dpkg-query -W -f='${Status}' "${package}" 2>/dev/null || true)" == "install ok installed" ]]
}

apt_package_available() {
    local package="$1"
    apt-cache show "${package}" >/dev/null 2>&1
}

require_apt_platform() {
    command -v apt-get >/dev/null 2>&1 || fail "TreeForge automatic setup requires apt-get."
    command -v dpkg-query >/dev/null 2>&1 || fail "TreeForge automatic setup requires dpkg-query."
}

run_apt() {
    if [[ "${EUID}" -eq 0 ]]; then
        apt-get "$@"
    else
        command -v sudo >/dev/null 2>&1 || fail "sudo is required to install system packages."
        sudo apt-get "$@"
    fi
}

install_missing_packages() {
    local label="$1"
    shift
    local requested=("$@")
    local missing=()
    local package

    for package in "${requested[@]}"; do
        if ! apt_package_installed "${package}"; then
            if ! apt_package_available "${package}"; then
                fail "Required ${label} package is unavailable from configured apt repositories: ${package}"
            fi
            missing+=("${package}")
        fi
    done

    if (( ${#missing[@]} == 0 )); then
        success "${label} packages are already installed."
        return
    fi

    printf '\n%sRequired %s packages%s\n\n' "${BOLD}" "${label}" "${RESET}"
    printf '  %s\n' "${missing[@]}"
    printf '\n'

    run_apt update
    run_apt install -y "${missing[@]}"

    for package in "${missing[@]}"; do
        apt_package_installed "${package}" || fail "Package installation did not complete: ${package}"
    done

    success "${label} packages installed."
}

ensure_setup_bootstrap_dependencies() {
    require_apt_platform

    if [[ "${EUID}" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
        # sudo itself may be absent on a minimal install, but without root we cannot bootstrap it.
        fail "sudo is unavailable. Run setup as root once or install sudo first."
    fi

    install_missing_packages "TreeForge setup prerequisite" "${BOOTSTRAP_APT_PACKAGES[@]}"

    local command_name
    for command_name in \
        bash curl git ssh ssh-keygen ssh-add openssl python3 grep sed awk hostname \
        xdg-open findmnt lsblk blkid swapon swapoff mkswap df dd install mktemp \
        script systemctl getconf
    do
        command -v "${command_name}" >/dev/null 2>&1 || fail "Required setup command is unavailable: ${command_name}"
    done
}

install_optional_package_if_available() {
    local package="$1"
    if apt_package_installed "${package}"; then
        return
    fi
    if apt_package_available "${package}"; then
        run_apt install -y "${package}"
    else
        warn "Optional package is not available on this distribution: ${package}"
    fi
}

install_treeforge_mode_dependencies() {
    local mode="$1"

    install_missing_packages "TreeForge runtime" "${TREEFORGE_USER_APT_PACKAGES[@]}"

    case "${mode}" in
        user)
            ;;
        maintainer|developer)
            install_missing_packages "TreeForge bring-up" "${TREEFORGE_MAINTAINER_APT_PACKAGES[@]}"
            ;;
        *) fail "Unknown installation mode: ${mode}" ;;
    esac
}

check_aosp_host_architecture() {
    local machine
    machine="$(uname -m)"
    case "${machine}" in
        x86_64|amd64) ;;
        *) fail "Google's supported AOSP build workstation architecture is 64-bit x86; detected ${machine}." ;;
    esac
}

ensure_aosp_build_dependencies() {
    check_aosp_host_architecture

    printf '\n%sAOSP build host dependencies%s\n\n' "${BOLD}" "${RESET}"
    printf '%s\n' \
        "TreeForge will install Google's current Android 11+ Ubuntu build package set," \
        "using current direct package names on modern Ubuntu." \
        "" \
        "Notably:" \
        "  git               replaces the historical git-core package name" \
        "  x11proto-dev      replaces the transitional x11proto-core-dev alias" \
        "  libgl-dev + libglvnd-dev replace the transitional libgl1-mesa-dev alias" \
        "" \
        "AOSP supplies its versioned OpenJDK/Make/Python prebuilts; TreeForge does" \
        "not install an arbitrary host JDK for Android 15 r36."

    install_missing_packages "AOSP build" "${AOSP_BUILD_APT_PACKAGES[@]}"
    ensure_repo_tool

    success "AOSP build host dependencies are ready."
}

repo_launcher_version() {
    local launcher="$1"

    [[ -x "${launcher}" ]] \
        || return 0

    "${launcher}" \
        --version \
        2>/dev/null \
        | awk '
            /repo launcher version/ {
                print $4
                exit
            }
        ' \
        || true
}


ensure_repo_tool() {
    local bindir="${HOME}/.local/bin"
    local user_repo="${bindir}/repo"
    local latest_tmp
    local current_path=""
    local current_version=""
    local latest_version=""
    local installed_version=""

    mkdir -p \
        "${bindir}"

    #
    # TreeForge owns Repo at the per-user level so a distro-owned
    # /usr/bin/repo never blocks launcher updates.
    #
    export PATH="${bindir}:${PATH}"
    hash -r

    current_path="$(
        command -v repo \
            2>/dev/null \
            || true
    )"

    if [[ -n "${current_path}" ]]; then
        current_version="$(
            repo_launcher_version \
                "${current_path}"
        )"
    fi

    latest_tmp="$(
        mktemp
    )"

    info \
        "Checking Google's current Repo launcher"

    curl \
        -fsSL \
        https://storage.googleapis.com/git-repo-downloads/repo \
        -o "${latest_tmp}"

    chmod 0755 \
        "${latest_tmp}"

    latest_version="$(
        repo_launcher_version \
            "${latest_tmp}"
    )"

    [[ -n "${latest_version}" ]] \
        || fail \
            "Could not determine the version of Google's downloaded Repo launcher."

    if [[ -x "${user_repo}" ]] \
        && cmp -s \
            "${latest_tmp}" \
            "${user_repo}"; then

        rm -f \
            "${latest_tmp}"

        installed_version="$(
            repo_launcher_version \
                "${user_repo}"
        )"

        success \
            "Repo launcher is current: ${installed_version} (${user_repo})"

        hash -r

        return 0
    fi

    if [[ -n "${current_version}" ]]; then
        if [[ "${current_version}" == "${latest_version}" ]]; then
            info \
                "Installing Google Repo launcher ${latest_version} as a TreeForge-managed per-user command"
        else
            info \
                "Repo launcher update available: ${current_version} -> ${latest_version}"
        fi
    else
        info \
            "Installing Google Repo launcher ${latest_version}"
    fi

    install \
        -m 0755 \
        "${latest_tmp}" \
        "${user_repo}"

    rm -f \
        "${latest_tmp}"

    hash -r

    [[ "$(command -v repo)" == "${user_repo}" ]] \
        || fail \
            "TreeForge-managed Repo launcher is not first on PATH: $(command -v repo)"

    installed_version="$(
        repo_launcher_version \
            "${user_repo}"
    )"

    [[ "${installed_version}" == "${latest_version}" ]] \
        || fail \
            "Repo launcher update verification failed: expected ${latest_version}, found ${installed_version:-unknown}."

    success \
        "TreeForge-managed Repo launcher ready: ${installed_version} (${user_repo})"
}


validate_repo_url() {
    local repo_url="$1"
    case "${repo_url}" in
        https://*|git@*:*|ssh://*) ;;
        *) fail "Repository sources must use HTTPS or SSH: ${repo_url}" ;;
    esac
}

repository_url_is_ssh() {
    case "$1" in
        git@*:*|ssh://*) return 0 ;;
        *) return 1 ;;
    esac
}

repository_url_is_github() {
    case "$1" in
        https://github.com/*|git@github.com:*|ssh://github.com/*|ssh://git@github.com/*) return 0 ;;
        *) return 1 ;;
    esac
}

validate_repository_source() {
    case "$1" in
        public|private) ;;
        *) fail "Repository source must be public or private." ;;
    esac
}

prompt_installation_mode() {
    local current_mode="${1:-}"
    local default_choice=1
    case "${current_mode}" in
        user) default_choice=1 ;;
        maintainer) default_choice=2 ;;
        developer) default_choice=3 ;;
        "") ;;
        *) warn "Ignoring invalid saved installation mode: ${current_mode}" ;;
    esac

    cat <<EOF

${BOLD}Installation mode${RESET}

  1) User
     Supported-device/downstream TreeForge use.

  2) Maintainer
     Adds factory-image reconstruction and new-device bring-up tooling.

  3) Developer
     Adds TreeForge source-development, testing, packaging, and maintenance.

EOF

    prompt_choice MODE_CHOICE "Select installation mode" "${default_choice}" 1 2 3
    case "${MODE_CHOICE}" in
        1) SELECTED_INSTALL_MODE=user ;;
        2) SELECTED_INSTALL_MODE=maintainer ;;
        3) SELECTED_INSTALL_MODE=developer ;;
    esac
}

installation_mode_file() {
    local config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
    printf '%s\n' "${TREEFORGE_MODE_FILE:-${config_home}/treeforge/install-mode}"
}

installation_mode_schema_file() {
    local mode_file
    mode_file="$(installation_mode_file)"
    printf '%s\n' "${TREEFORGE_MODE_SCHEMA_FILE:-$(dirname "${mode_file}")/install-mode-schema}"
}

write_install_mode() {
    local mode="$1"
    local mode_file schema_file
    mode_file="$(installation_mode_file)"
    schema_file="$(installation_mode_schema_file)"
    mkdir -p "$(dirname "${mode_file}")"
    printf '%s\n' "${mode}" > "${mode_file}"
    printf '%s\n' 2 > "${schema_file}"
}

read_install_mode() {
    local mode_file mode
    mode_file="$(installation_mode_file)"
    if [[ -f "${mode_file}" ]]; then
        mode="$(head -n1 "${mode_file}" | tr -d '[:space:]')"
        case "${mode}" in
            user|maintainer|developer) printf '%s\n' "${mode}"; return ;;
        esac
    fi
    printf '%s\n' user
}

prompt_repository_source() {
    local result_variable="$1"
    local label="$2"
    local public_url="$3"
    local private_url="$4"
    local default_source="$5"
    local override_url="${6:-}"
    local current_url="${7:-}"
    local mode="$8"
    local -n result_ref="${result_variable}"
    local allow_custom=false
    local choice default_choice=1 custom_url=""

    validate_repository_source "${default_source}"
    [[ "${mode}" == maintainer || "${mode}" == developer ]] && allow_custom=true

    if [[ -n "${current_url}" ]]; then
        printf '\n%s%s repository source%s\n\n' "${BOLD}" "${label}" "${RESET}"
        printf '  1) Keep current\n     %s\n\n' "${current_url}"
        printf '  2) Public\n     %s\n\n' "${public_url}"
        printf '  3) Private\n     %s\n\n' "${private_url}"
        if [[ "${allow_custom}" == true ]]; then
            printf '  4) Custom HTTPS/SSH URL\n\n'
            prompt_choice choice "Select source" 1 1 2 3 4
        else
            prompt_choice choice "Select source" 1 1 2 3
        fi
        case "${choice}" in
            1) result_ref="${current_url}"; return ;;
            2) result_ref="${public_url}"; return ;;
            3) result_ref="${private_url}"; return ;;
            4) ;;
        esac
    else
        [[ "${default_source}" == private ]] && default_choice=2
        if [[ -n "${override_url}" ]]; then
            if [[ "${override_url}" == "${public_url}" ]]; then
                default_choice=1
            elif [[ "${override_url}" == "${private_url}" ]]; then
                default_choice=2
            elif [[ "${allow_custom}" == true ]]; then
                default_choice=3
            else
                warn "Ignoring custom ${label} URL because User mode accepts predefined sources only."
                override_url=""
            fi
        fi

        printf '\n%s%s repository source%s\n\n' "${BOLD}" "${label}" "${RESET}"
        printf '  1) Public\n     %s\n\n' "${public_url}"
        printf '  2) Private\n     %s\n\n' "${private_url}"
        if [[ "${allow_custom}" == true ]]; then
            printf '  3) Custom HTTPS/SSH URL\n\n'
            prompt_choice choice "Select source" "${default_choice}" 1 2 3
        else
            prompt_choice choice "Select source" "${default_choice}" 1 2
        fi
        case "${choice}" in
            1) result_ref="${public_url}"; return ;;
            2) result_ref="${private_url}"; return ;;
            3) ;;
        esac
    fi

    [[ "${allow_custom}" == true ]] || fail "Custom repository URLs are unavailable in User mode."
    prompt_value custom_url "Repository URL" "${override_url}"
    validate_repo_url "${custom_url}"
    result_ref="${custom_url}"
}

git_global_value() {
    git config --global --get "$1" 2>/dev/null || true
}

configure_git_identity() {
    local current_name current_email git_name git_email change=false
    current_name="$(git_global_value user.name)"
    current_email="$(git_global_value user.email)"

    if [[ -n "${current_name}" && -n "${current_email}" ]]; then
        printf '\nGit identity: %s <%s>\n' "${current_name}" "${current_email}"
        prompt_yes_no change "Change the existing Git identity" no
        if [[ "${change}" != true ]]; then
            return 0
        fi
    fi

    prompt_value git_name "Git user.name" "${current_name}"
    prompt_value git_email "Git user.email" "${current_email}"
    git config --global user.name "${git_name}"
    git config --global user.email "${git_email}"
}

find_existing_ssh_public_key() {
    local key
    for key in "${HOME}/.ssh/id_ed25519.pub" "${HOME}/.ssh/id_ecdsa.pub" "${HOME}/.ssh/id_rsa.pub"; do
        [[ -f "${key}" ]] && { printf '%s\n' "${key}"; return 0; }
    done
    return 1
}

github_ssh_authenticated() {
    local output status
    set +e
    output="$(ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1)"
    status=$?
    set -e
    grep -qi 'successfully authenticated' <<<"${output}" && return 0
    [[ "${status}" -eq 1 ]] && grep -qi github <<<"${output}" && grep -qi authenticated <<<"${output}"
}

ensure_github_cli() {
    if command -v gh >/dev/null 2>&1; then
        return
    fi
    if apt_package_available gh; then
        run_apt install -y gh
        return
    fi
    fail "GitHub CLI (gh) is required for guided private GitHub SSH setup but is unavailable from configured repositories."
}

configure_github_ssh() {
    github_ssh_authenticated && { success "GitHub SSH authentication already works."; return; }

    mkdir -p "${HOME}/.ssh"
    chmod 700 "${HOME}/.ssh"

    local public_key private_key
    public_key="$(find_existing_ssh_public_key || true)"

    if [[ -z "${public_key}" ]]; then
        public_key="${HOME}/.ssh/id_ed25519.pub"
        private_key="${HOME}/.ssh/id_ed25519"
        info "Generating an Ed25519 SSH key for GitHub"
        ssh-keygen -t ed25519 -f "${private_key}" -N "" -C "$(git_global_value user.email)"
    else
        private_key="${public_key%.pub}"
    fi

    ensure_github_cli
    if ! gh auth status --hostname github.com >/dev/null 2>&1; then
        gh auth login --hostname github.com --git-protocol ssh --web
    fi

    local title
    title="TreeForge $(hostname) $(date +%Y-%m-%d)"
    if ! gh ssh-key list 2>/dev/null | grep -Fq "$(awk '{print $2}' "${public_key}")"; then
        gh ssh-key add "${public_key}" --title "${title}"
    fi

    if [[ -n "${SSH_AUTH_SOCK:-}" ]]; then
        ssh-add "${private_key}" >/dev/null 2>&1 || true
    fi

    github_ssh_authenticated || fail "GitHub SSH authentication is still unavailable after key setup."
    success "GitHub SSH authentication configured."
}

configure_repository_access() {
    local repo_url="$1"
    configure_git_identity
    if repository_url_is_ssh "${repo_url}" && repository_url_is_github "${repo_url}"; then
        configure_github_ssh
    fi
}

is_treeforge_checkout() {
    local install_dir="$1"
    [[ -d "${install_dir}/.git" && -f "${install_dir}/pyproject.toml" && -d "${install_dir}/treeforge" ]]
}

repository_is_dirty() {
    [[ -n "$(git -C "$1" status --porcelain 2>/dev/null)" ]]
}

clone_treeforge() {
    local repo_url="$1" install_dir="$2" mode="$3"
    mkdir -p "$(dirname "${install_dir}")"
    info "Cloning TreeForge"

    if [[ "${mode}" == developer ]] && git ls-remote --exit-code --heads "${repo_url}" "${DEFAULT_DEV_BRANCH}" >/dev/null 2>&1; then
        git clone --branch "${DEFAULT_DEV_BRANCH}" "${repo_url}" "${install_dir}"
    else
        git clone "${repo_url}" "${install_dir}"
    fi
}

update_existing_treeforge() {
    local install_dir="$1"
    if repository_is_dirty "${install_dir}"; then
        warn "Local TreeForge changes are present; automatic source update skipped."
        return
    fi

    local update=true
    prompt_yes_no update "Update the existing TreeForge checkout" yes
    if [[ "${update}" != true ]]; then
        return 0
    fi

    git -C "${install_dir}" pull --ff-only
}

resolve_base_python() {
    if [[ -n "${TREEFORGE_PYTHON:-}" ]]; then
        command -v "${TREEFORGE_PYTHON}" >/dev/null 2>&1 || fail "TREEFORGE_PYTHON cannot be resolved: ${TREEFORGE_PYTHON}"
        printf '%s\n' "${TREEFORGE_PYTHON}"
        return
    fi
    printf '%s\n' python3
}

install_treeforge_python_environment() {
    local install_dir="$1" mode="$2"
    local python_bin venv_python
    python_bin="$(resolve_base_python)"
    venv_python="${install_dir}/.venv/bin/python"

    if [[ ! -x "${venv_python}" ]]; then
        "${python_bin}" -m venv "${install_dir}/.venv"
    fi

    "${venv_python}" -m pip install --upgrade pip setuptools wheel
    "${venv_python}" -m pip install -e "${install_dir}"

    if [[ "${mode}" == developer ]]; then
        "${venv_python}" -m pip install "${TREEFORGE_DEVELOPER_PYTHON_PACKAGES[@]}"
    fi

    "${venv_python}" -m treeforge.setup.host_providers

    (
        cd "${install_dir}"
        "${install_dir}/.venv/bin/treeforge" doctor
    )

    write_install_mode "${mode}"
}


install_optional_treeforge_android_transport_tools() {
    local install_dir="$1"
    local install_transport=false
    local venv_python="${install_dir}/.venv/bin/python"
    local user_bin="${HOME}/.local/bin"
    local adb_source=""
    local fastboot_source=""
    local resolved=()

    [[ -x "${venv_python}" ]] \
        || fail \
            "TreeForge must be installed before its provider-backed adb/fastboot can be exposed as host commands."

    cat <<EOF

${BOLD}Optional ADB / Fastboot host commands${RESET}

TreeForge resolves exact pinned adb and fastboot provider releases through its
verified local cache and TreeForge's public toolchain releases. No distro
adb/fastboot packages are needed.

Setup can also copy those verified TreeForge-provided binaries to:
  ${user_bin}/adb
  ${user_bin}/fastboot

This is optional and only makes adb/fastboot convenient to invoke directly
from your shell. TreeForge itself does not require this step.

EOF

    prompt_yes_no install_transport \
        "Install TreeForge-provided adb and fastboot as per-user commands" \
        no

    if [[ "${install_transport}" != true ]]; then
        printf '\nTreeForge adb/fastboot shell-command installation skipped.\n'
        return
    fi

    mapfile -t resolved < <(
        "${venv_python}" - <<'TREEFORGE_RESOLVE_TRANSPORT_TOOLS'
from treeforge.android.host_tools import (
    treeforge_adb_executable,
    treeforge_fastboot_executable,
)

print(treeforge_adb_executable())
print(treeforge_fastboot_executable())
TREEFORGE_RESOLVE_TRANSPORT_TOOLS
    )

    if (( ${#resolved[@]} != 2 )); then
        fail \
            "TreeForge provider resolution did not return exactly adb and fastboot."
    fi

    adb_source="${resolved[0]}"
    fastboot_source="${resolved[1]}"

    [[ -x "${adb_source}" ]] \
        || fail \
            "TreeForge-provided adb is unavailable or not executable: ${adb_source}"

    [[ -x "${fastboot_source}" ]] \
        || fail \
            "TreeForge-provided fastboot is unavailable or not executable: ${fastboot_source}"

    mkdir -p \
        "${user_bin}"

    install -m 0755 \
        "${adb_source}" \
        "${user_bin}/adb"

    install -m 0755 \
        "${fastboot_source}" \
        "${user_bin}/fastboot"

    cmp -s \
        "${adb_source}" \
        "${user_bin}/adb" \
        || fail \
            "Installed adb does not match the TreeForge provider binary."

    cmp -s \
        "${fastboot_source}" \
        "${user_bin}/fastboot" \
        || fail \
            "Installed fastboot does not match the TreeForge provider binary."

    success \
        "TreeForge-provided adb installed at ${user_bin}/adb"

    success \
        "TreeForge-provided fastboot installed at ${user_bin}/fastboot"

    case ":${PATH}:" in
        *":${user_bin}:"*)
            ;;
        *)
            warn \
                "${user_bin} is not currently on PATH. Add it to your shell PATH to invoke adb/fastboot directly."
            ;;
    esac
}

android_source_config_file() {
    local config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
    printf '%s\n' "${TREEFORGE_ANDROID_SOURCE_CONFIG:-${config_home}/treeforge/android-source.conf}"
}

write_android_source_config() {
    local source_kind="$1" aosp_root="$2" config_file
    config_file="$(android_source_config_file)"
    mkdir -p "$(dirname "${config_file}")"
    cat > "${config_file}" <<EOF
schema=1
version_name=${ANDROID_VERSION_NAME}
version_tag=${ANDROID_VERSION_TAG}
manifest_kind=${ANDROID_MANIFEST_KIND}
manifest_url=${ANDROID_MANIFEST_URL}
manifest_revision=${ANDROID_MANIFEST_REVISION}
manifest_name=${ANDROID_MANIFEST_NAME}
lunch_target=${ANDROID_LUNCH_TARGET}
source_kind=${source_kind}
aosp_root=${aosp_root}
EOF
    ANDROID_AOSP_SOURCE_KIND="${source_kind}"
    ANDROID_AOSP_ROOT="${aosp_root}"
    success "Android/AOSP selection saved: ${config_file}"
}

load_android_source_config() {
    local config_file key value schema=""
    config_file="$(android_source_config_file)"
    [[ -f "${config_file}" ]] || return 1

    ANDROID_VERSION_NAME=""
    ANDROID_VERSION_TAG=""
    ANDROID_MANIFEST_KIND=""
    ANDROID_MANIFEST_URL=""
    ANDROID_MANIFEST_REVISION=""
    ANDROID_MANIFEST_NAME=""
    ANDROID_LUNCH_TARGET=""
    ANDROID_AOSP_SOURCE_KIND=""
    ANDROID_AOSP_ROOT=""

    while IFS='=' read -r key value; do
        case "${key}" in
            schema) schema="${value}" ;;
            version_name) ANDROID_VERSION_NAME="${value}" ;;
            version_tag) ANDROID_VERSION_TAG="${value}" ;;
            manifest_kind) ANDROID_MANIFEST_KIND="${value}" ;;
            manifest_url) ANDROID_MANIFEST_URL="${value}" ;;
            manifest_revision) ANDROID_MANIFEST_REVISION="${value}" ;;
            manifest_name) ANDROID_MANIFEST_NAME="${value}" ;;
            lunch_target) ANDROID_LUNCH_TARGET="${value}" ;;
            source_kind) ANDROID_AOSP_SOURCE_KIND="${value}" ;;
            aosp_root) ANDROID_AOSP_ROOT="${value}" ;;
            "") ;;
            *) fail "Unknown Android source configuration field: ${key}" ;;
        esac
    done < "${config_file}"

    [[ "${schema}" == 1 ]] || fail "Unsupported Android source configuration schema: ${schema:-missing}"
}

android_version_selection() {
    cat <<EOF

${BOLD}Android version${RESET}

  1) ${ANDROID_15_NAME}
     Platform revision: ${ANDROID_15_TAG}

EOF
    prompt_choice ANDROID_VERSION_CHOICE "Select Android version" 1 1
    ANDROID_VERSION_NAME="${ANDROID_15_NAME}"
    ANDROID_VERSION_TAG="${ANDROID_15_TAG}"
    ANDROID_TREEFORGE_MANIFEST_REVISION="${ANDROID_15_MANIFEST_BRANCH}"
    ANDROID_GOOGLE_MANIFEST_REVISION="${ANDROID_15_GOOGLE_MANIFEST_REVISION}"
    ANDROID_MANIFEST_NAME_DEFAULT="${ANDROID_15_MANIFEST_NAME}"
    ANDROID_LUNCH_TARGET="${ANDROID_15_LUNCH_TARGET}"
}

select_android_manifest_source() {
    local mode="$1"
    local current_kind="${2:-}"
    local allow_custom=false choice default_choice=1 custom_url custom_revision custom_name
    [[ "${mode}" == maintainer || "${mode}" == developer ]] && allow_custom=true

    case "${current_kind}" in
        treeforge-public) default_choice=1 ;;
        treeforge-private) default_choice=2 ;;
        google) default_choice=3 ;;
        custom) [[ "${allow_custom}" == true ]] && default_choice=4 ;;
        "")
            case "${DEFAULT_AOSP_MANIFEST_SOURCE}" in
                public) default_choice=1 ;;
                private) default_choice=2 ;;
                google) default_choice=3 ;;
                *) fail "TREEFORGE_AOSP_MANIFEST_SOURCE must be public, private, or google." ;;
            esac
            ;;
    esac

    printf '\n%sAOSP manifest source%s\n\n' "${BOLD}" "${RESET}"
    printf '  1) TreeForge public\n     %s\n     Revision: %s\n\n' "${TREEFORGE_PUBLIC_AOSP_MANIFEST_URL}" "${ANDROID_TREEFORGE_MANIFEST_REVISION}"
    printf '  2) TreeForge private\n     %s\n     Revision: %s\n\n' "${TREEFORGE_PRIVATE_AOSP_MANIFEST_URL}" "${ANDROID_TREEFORGE_MANIFEST_REVISION}"
    printf '  3) Google canonical Android %s\n     %s\n     Revision: %s\n\n' "${ANDROID_VERSION_TAG}" "${GOOGLE_AOSP_MANIFEST_URL}" "${ANDROID_GOOGLE_MANIFEST_REVISION}"

    if [[ "${allow_custom}" == true ]]; then
        printf '  4) Custom HTTPS/SSH manifest\n\n'
        prompt_choice choice "Select AOSP manifest" "${default_choice}" 1 2 3 4
    else
        prompt_choice choice "Select AOSP manifest" "${default_choice}" 1 2 3
    fi

    case "${choice}" in
        1)
            ANDROID_MANIFEST_KIND=treeforge-public
            ANDROID_MANIFEST_URL="${TREEFORGE_PUBLIC_AOSP_MANIFEST_URL}"
            ANDROID_MANIFEST_REVISION="${ANDROID_TREEFORGE_MANIFEST_REVISION}"
            ANDROID_MANIFEST_NAME="${ANDROID_MANIFEST_NAME_DEFAULT}"
            ;;
        2)
            ANDROID_MANIFEST_KIND=treeforge-private
            ANDROID_MANIFEST_URL="${TREEFORGE_PRIVATE_AOSP_MANIFEST_URL}"
            ANDROID_MANIFEST_REVISION="${ANDROID_TREEFORGE_MANIFEST_REVISION}"
            ANDROID_MANIFEST_NAME="${ANDROID_MANIFEST_NAME_DEFAULT}"
            ;;
        3)
            ANDROID_MANIFEST_KIND=google
            ANDROID_MANIFEST_URL="${GOOGLE_AOSP_MANIFEST_URL}"
            ANDROID_MANIFEST_REVISION="${ANDROID_GOOGLE_MANIFEST_REVISION}"
            ANDROID_MANIFEST_NAME="${ANDROID_MANIFEST_NAME_DEFAULT}"
            ;;
        4)
            [[ "${allow_custom}" == true ]] || fail "Custom AOSP manifests are unavailable in User mode."
            prompt_value custom_url "Custom manifest HTTPS/SSH URL" "${DEFAULT_AOSP_MANIFEST_URL}"
            validate_repo_url "${custom_url}"
            prompt_value custom_revision "Custom manifest revision/branch/tag" "${ANDROID_VERSION_TAG}"
            prompt_value custom_name "Custom manifest file" "${ANDROID_MANIFEST_NAME_DEFAULT}"
            ANDROID_MANIFEST_KIND=custom
            ANDROID_MANIFEST_URL="${custom_url}"
            ANDROID_MANIFEST_REVISION="${custom_revision}"
            ANDROID_MANIFEST_NAME="${custom_name}"
            ;;
    esac

    if repository_url_is_ssh "${ANDROID_MANIFEST_URL}" && repository_url_is_github "${ANDROID_MANIFEST_URL}"; then
        configure_github_ssh
    fi
}

configure_android_source_selection() {
    local install_dir="$1" mode="$2"
    local current_kind=""

    if load_android_source_config; then
        current_kind="${ANDROID_MANIFEST_KIND}"
        cat <<EOF

${BOLD}Current Android/AOSP selection${RESET}
  Android:       ${ANDROID_VERSION_NAME} (${ANDROID_VERSION_TAG})
  Manifest kind: ${ANDROID_MANIFEST_KIND}
  Manifest:      ${ANDROID_MANIFEST_URL}
  Revision:      ${ANDROID_MANIFEST_REVISION}
  Source state:  ${ANDROID_AOSP_SOURCE_KIND}
  AOSP root:     ${ANDROID_AOSP_ROOT}

EOF
    fi

    android_version_selection
    select_android_manifest_source "${mode}" "${current_kind}"
    write_android_source_config deferred "${install_dir}/aosp"
}

current_aosp_manifest_url() {
    local source_root="$1"
    local manifest_git="${source_root}/.repo/manifests.git"
    [[ -d "${manifest_git}" ]] || { printf '%s\n' ""; return; }
    git --git-dir="${manifest_git}" remote get-url origin 2>/dev/null || true
}

aosp_checkout_looks_valid() {
    local root="$1"
    [[ -d "${root}/.repo" && -d "${root}/build" && -f "${root}/build/envsetup.sh" ]]
}

normalize_repo_url() {
    local value="${1%/}"
    value="${value%.git}"
    printf '%s\n' "${value}"
}

configure_aosp_manifest_overlays() {
    local source_root="$1"
    local destination_dir="${source_root}/.repo/local_manifests"
    local destination_path="${destination_dir}/$(basename "${AOSP_REMOVAL_LEDGER_RELATIVE_PATH}")"

    case "${ANDROID_MANIFEST_KIND}" in
        treeforge-public|treeforge-private)
            local source_path="${source_root}/.repo/manifests/${AOSP_REMOVAL_LEDGER_RELATIVE_PATH}"
            [[ -f "${source_path}" ]] || fail "TreeForge removal ledger is missing: ${source_path}"
            mkdir -p "${destination_dir}"
            cp "${source_path}" "${destination_path}"
            ;;
        google|custom)
            rm -f "${destination_path}"
            ;;
        *) fail "Unknown AOSP manifest kind: ${ANDROID_MANIFEST_KIND}" ;;
    esac
}

verify_aosp_manifest() {
    local install_dir="$1" source_root="$2" resolved="${3:-false}"
    local active expected manifest_file
    active="$(normalize_repo_url "$(current_aosp_manifest_url "${source_root}")")"
    expected="$(normalize_repo_url "${ANDROID_MANIFEST_URL}")"
    [[ "${active}" == "${expected}" ]] || fail "Active AOSP manifest differs from selected source. Active: ${active}; selected: ${expected}"

    mkdir -p "${install_dir}/.smoke"
    manifest_file="${install_dir}/.smoke/setup-aosp-manifest.xml"
    if [[ "${resolved}" == true ]]; then
        (cd "${source_root}" && repo manifest -r > "${manifest_file}")
    else
        (cd "${source_root}" && repo manifest > "${manifest_file}")
    fi

    python3 - "${manifest_file}" "${source_root}" "${ANDROID_MANIFEST_KIND}" <<'TREEFORGE_VERIFY_MANIFEST_PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

manifest = Path(sys.argv[1])
source_root = Path(sys.argv[2])
kind = sys.argv[3]
root = ET.parse(manifest).getroot()
projects = root.findall('project')
paths = {(p.get('path') or p.get('name') or '').strip() for p in projects}
required = ('build/make', 'build/soong', 'frameworks/base', 'system/core', 'hardware/interfaces')
missing = [p for p in required if p not in paths]
if missing:
    raise SystemExit('AOSP manifest missing required platform roots: ' + ', '.join(missing))

device_projects = sorted(p for p in paths if p.startswith('device/'))
ledger = source_root / '.repo/local_manifests/00-treeforge-removed-projects.xml'
if kind in {'treeforge-public', 'treeforge-private'}:
    if device_projects:
        raise SystemExit('TreeForge manifest still contains upstream device/* projects: ' + ', '.join(device_projects))
    if not ledger.is_file():
        raise SystemExit(f'TreeForge removal ledger is missing: {ledger}')
else:
    if ledger.exists():
        raise SystemExit(f'TreeForge removal ledger must be absent for {kind}: {ledger}')
print(f'AOSP manifest verification passed: {len(projects)} projects, kind={kind}')
TREEFORGE_VERIFY_MANIFEST_PY
}

validate_aosp_sync_settings() {
    case "${AOSP_SYNC_JOBS}" in
        ''|*[!0-9]*|0)
            fail \
                "TREEFORGE_AOSP_SYNC_JOBS must be a positive integer."
            ;;
    esac

    case "${AOSP_SYNC_RETRY_FETCHES}" in
        ''|*[!0-9]*)
            fail \
                "TREEFORGE_AOSP_SYNC_RETRY_FETCHES must be a non-negative integer."
            ;;
    esac
}

print_aosp_source_warning() {
    local destination="$1"
    cat <<EOF

${YELLOW}${BOLD}AOSP SOURCE / BUILD HOST WARNING${RESET}

Android:          ${ANDROID_VERSION_NAME} (${ANDROID_VERSION_TAG})
Manifest kind:    ${ANDROID_MANIFEST_KIND}
Manifest:         ${ANDROID_MANIFEST_URL}
Revision:         ${ANDROID_MANIFEST_REVISION}
AOSP root:        ${destination}

Google's current AOSP workstation guidance calls for a 64-bit x86 Linux host,
at least 400 GB free disk for checkout + build, and recommends 64 GB RAM for
practical full builds. TreeForge's optional memory/swap workflow remains
available at the end of setup for lower-memory development hosts.

TreeForge-owned Android host providers remain independent of this checkout.

EOF
}

prompt_aosp_sync_jobs() {
    local entered=""

    while true; do
        prompt_value entered \
            "repo sync parallel jobs (-j)" \
            "${AOSP_SYNC_JOBS}"

        case "${entered}" in
            ''|*[!0-9]*|0)
                warn \
                    "repo sync parallel jobs must be a positive integer."
                ;;
            *)
                AOSP_SYNC_JOBS="${entered}"
                return 0
                ;;
        esac
    done
}


google_vendor_binaries_ready() {
    local source_root="$1"

    [[ -f "${source_root}/vendor/google_devices/tangorpro/proprietary/BoardConfigVendor.mk" ]]
}


configure_google_vendor_binaries() {
    local source_root="$1"
    local ignored=""

    if google_vendor_binaries_ready \
        "${source_root}"; then

        success \
            "Google Pixel Tablet vendor binaries are already present."

        return 0
    fi

    cat <<EOF

${BOLD}Google Pixel Tablet vendor binaries${RESET}

AOSP source synchronization is complete.

Google's Pixel vendor binaries are a separate manual download/install step.
TreeForge will not download, open, or extract them for you.

Use this link:

  ${GOOGLE_VENDOR_BINARIES_URL}

For this Pixel Tablet (tangorpro) Android 15 setup, choose the Pixel Tablet
vendor image for build BP1A.250505.005 and follow Google's instructions.

Run Google's extraction instructions from the AOSP source root:

  ${source_root}

When Google's instructions are completely finished, return to this terminal.

EOF

    read -r -p \
        "Press Enter when you have finished Google's vendor binary instructions: " \
        ignored

    if ! google_vendor_binaries_ready \
        "${source_root}"; then

        fail \
            "Google Pixel Tablet vendor binaries were not detected. Expected: ${source_root}/vendor/google_devices/tangorpro/proprietary/BoardConfigVendor.mk"
    fi

    success \
        "Google Pixel Tablet vendor binaries verified."
}


managed_aosp_slim_marker() {
    local source_root="$1"
    printf '%s\n' "${source_root}/${AOSP_SLIM_MARKER_RELATIVE_PATH}"
}


managed_aosp_checkout_is_slim() {
    local source_root="$1"
    [[ -f "$(managed_aosp_slim_marker "${source_root}")" ]]
}


managed_aosp_legacy_partial_marker() {
    local source_root="$1"
    printf '%s\n' "${source_root}/${AOSP_SLIM_V1_MARKER_RELATIVE_PATH}"
}

managed_aosp_checkout_is_legacy_partial() {
    local source_root="$1"
    [[ -f "$(managed_aosp_legacy_partial_marker "${source_root}")" ]]
}

mark_managed_aosp_checkout_slim() {
    local source_root="$1"
    local marker legacy_marker

    marker="$(managed_aosp_slim_marker "${source_root}")"
    legacy_marker="$(managed_aosp_legacy_partial_marker "${source_root}")"

    mkdir -p "$(dirname "${marker}")"
    rm -f "${legacy_marker}"

    cat > "${marker}" <<EOF
schema=2
depth=1
manifest_depth=1
partial_clone=false
tags=false
clone_bundle=false
EOF
}


sync_managed_aosp_source() {
    local install_dir="$1"
    local source_root="${install_dir}/aosp"
    local confirm=false
    local resume=false
    local slim_checkout=true
    local legacy_partial_clone=false
    local storage_action=""
    local sync_log=""

    ensure_aosp_build_dependencies
    print_aosp_source_warning "${source_root}"

    if [[ -d "${source_root}/.repo" ]]; then
        if managed_aosp_checkout_is_slim "${source_root}"; then
            resume=true
            slim_checkout=true

            cat <<EOF

${BOLD}Existing TreeForge slim v2 AOSP checkout detected${RESET}

  ${source_root}

Storage mode:
  depth=1, no tags, no partial clone

EOF
            prompt_yes_no confirm \
                "Resume/synchronize the existing TreeForge slim v2 checkout now" \
                yes

            if [[ "${confirm}" != true ]]; then
                write_android_source_config deferred "${source_root}"
                return 0
            fi

        elif managed_aosp_checkout_is_legacy_partial "${source_root}"; then
            cat <<EOF

${YELLOW}${BOLD}Legacy TreeForge slim v1 partial-clone checkout detected${RESET}

  ${source_root}

The v1 mode used depth=1 plus partial clone blob:none. TreeForge no longer
uses blob:none for managed AOSP build checkouts because worktree checkout can
trigger additional on-demand blob fetches and fail while materializing files.

Choose what to do:

  1) Recreate as TreeForge slim v2
     depth=1, no tags, no partial clone

  2) Continue/resume the existing v1 partial-clone checkout

  3) Defer AOSP synchronization

EOF
            prompt_choice storage_action "Select" 1 1 2 3

            case "${storage_action}" in
                1)
                    cat <<EOF

${RED}${BOLD}AOSP CHECKOUT RECREATION${RESET}

This will permanently delete:

  ${source_root}

Any local AOSP edits or manually extracted vendor files inside that directory
will also be deleted.

EOF
                    prompt_yes_no confirm \
                        "Delete the v1 checkout and recreate it as TreeForge slim v2" \
                        no

                    if [[ "${confirm}" != true ]]; then
                        write_android_source_config deferred "${source_root}"
                        return 0
                    fi

                    rm -rf "${source_root}"
                    resume=false
                    slim_checkout=true
                    legacy_partial_clone=false
                    ;;
                2)
                    resume=true
                    slim_checkout=false
                    legacy_partial_clone=true
                    ;;
                3)
                    write_android_source_config deferred "${source_root}"
                    return 0
                    ;;
            esac

        else
            cat <<EOF

${YELLOW}${BOLD}Existing legacy/full AOSP checkout detected${RESET}

  ${source_root}

Choose what to do:

  1) Recreate as TreeForge slim v2
  2) Continue/resume existing checkout
  3) Defer AOSP synchronization

EOF
            prompt_choice storage_action "Select" 1 1 2 3

            case "${storage_action}" in
                1)
                    cat <<EOF

${RED}${BOLD}AOSP CHECKOUT RECREATION${RESET}

This will permanently delete:

  ${source_root}

EOF
                    prompt_yes_no confirm \
                        "Delete the existing checkout and recreate it as TreeForge slim v2" \
                        no

                    if [[ "${confirm}" != true ]]; then
                        write_android_source_config deferred "${source_root}"
                        return 0
                    fi

                    rm -rf "${source_root}"
                    resume=false
                    slim_checkout=true
                    legacy_partial_clone=false
                    ;;
                2)
                    resume=true
                    slim_checkout=false
                    legacy_partial_clone=false
                    ;;
                3)
                    write_android_source_config deferred "${source_root}"
                    return 0
                    ;;
            esac
        fi
    else
        prompt_yes_no confirm \
            "Initialize and synchronize the TreeForge slim v2 managed AOSP checkout now" \
            yes

        if [[ "${confirm}" != true ]]; then
            write_android_source_config deferred "${source_root}"
            return 0
        fi
    fi

    prompt_aosp_sync_jobs
    validate_aosp_sync_settings
    mkdir -p "${source_root}"

    if [[ "${slim_checkout}" == true ]]; then
        info "Initializing ${ANDROID_VERSION_NAME} TreeForge slim v2 AOSP checkout"
        (
            cd "${source_root}"
            repo init \
                -u "${ANDROID_MANIFEST_URL}" \
                -b "${ANDROID_MANIFEST_REVISION}" \
                -m "${ANDROID_MANIFEST_NAME}" \
                --depth=1 \
                --manifest-depth=1 \
                --no-partial-clone \
                --no-tags \
                --no-clone-bundle
        )
        mark_managed_aosp_checkout_slim "${source_root}"

    elif [[ "${legacy_partial_clone}" == true ]]; then
        info "Refreshing legacy TreeForge slim v1 manifest configuration"
        (
            cd "${source_root}"
            repo init \
                -u "${ANDROID_MANIFEST_URL}" \
                -b "${ANDROID_MANIFEST_REVISION}" \
                -m "${ANDROID_MANIFEST_NAME}" \
                --depth=1 \
                --manifest-depth=1 \
                --partial-clone \
                --clone-filter=blob:none \
                --no-tags \
                --no-clone-bundle
        )

    else
        info "Refreshing ${ANDROID_VERSION_NAME} manifest configuration"
        (
            cd "${source_root}"
            repo init \
                -u "${ANDROID_MANIFEST_URL}" \
                -b "${ANDROID_MANIFEST_REVISION}" \
                -m "${ANDROID_MANIFEST_NAME}"
        )
    fi

    configure_aosp_manifest_overlays "${source_root}"
    verify_aosp_manifest "${install_dir}" "${source_root}" false

    cat <<EOF

${BOLD}AOSP synchronization${RESET}

Checkout:
  ${source_root}

Storage mode:
  $(if [[ "${slim_checkout}" == true ]]; then
        printf '%s' 'TreeForge slim v2 (depth=1, no tags, no partial clone)'
    elif [[ "${legacy_partial_clone}" == true ]]; then
        printf '%s' 'TreeForge slim v1 legacy partial clone (depth=1, blob:none)'
    else
        printf '%s' 'existing legacy/full checkout'
    fi)

Parallel jobs:
  -j${AOSP_SYNC_JOBS}

Fetch retries:
  ${AOSP_SYNC_RETRY_FETCHES}

EOF

    sync_log="$(mktemp)"

    #
    # Repo suppresses its normal live progress display when stdout/stderr are
    # piped through tee because it no longer sees a terminal.
    #
    # util-linux script(1) gives repo a pseudo-terminal while also preserving
    # a transcript for post-failure diagnostics such as HTTP 429 detection.
    #
    local repo_sync_command=""

    printf -v repo_sync_command \
        '%q ' \
        repo \
        sync \
        -c \
        "-j${AOSP_SYNC_JOBS}" \
        --optimized-fetch \
        --no-tags \
        "--retry-fetches=${AOSP_SYNC_RETRY_FETCHES}" \
        --fail-fast

    if ! (
        cd "${source_root}"

        script \
            --quiet \
            --return \
            --flush \
            --command "${repo_sync_command}" \
            "${sync_log}"
    ); then
        printf '\n'
        warn "AOSP repo sync did not complete."

        if grep -Eqi \
            'RESOURCE_EXHAUSTED|rate limit exceeded|error: 429|HTTP[^0-9]*429|returned error: 429' \
            "${sync_log}"; then
            warn \
                "Google rate-limited the sync. Resume later with a lower job count such as 2-4."
        fi

        if grep -Eqi \
            'checkout [0-9a-f]{7,}|Cannot initialize work tree' \
            "${sync_log}"; then
            warn \
                "Repo failed while materializing a project worktree."

            if [[ "${legacy_partial_clone}" == true ]]; then
                warn \
                    "This is a v1 blob:none checkout; recreate it as TreeForge slim v2 on the next run."
            fi
        fi

        rm -f "${sync_log}"
        warn "The partial Repo checkout has been preserved at ${source_root}."
        warn "Run setup.sh again and choose the managed AOSP resume path to continue."
        write_android_source_config deferred "${source_root}"
        return 0
    fi

    rm -f "${sync_log}"

    verify_aosp_manifest "${install_dir}" "${source_root}" true
    configure_google_vendor_binaries "${source_root}"
    write_android_source_config managed "${source_root}"

    success \
        "AOSP checkout and Pixel Tablet vendor binaries are ready: ${source_root}"
}


configure_existing_aosp_source() {
    local install_dir="$1" root active expected
    ensure_aosp_build_dependencies
    prompt_value root "Existing AOSP source root"
    root="$(expand_path "${root}")"
    aosp_checkout_looks_valid "${root}" || fail "Not a complete Repo-managed AOSP checkout: ${root}"

    active="$(normalize_repo_url "$(current_aosp_manifest_url "${root}")")"
    expected="$(normalize_repo_url "${ANDROID_MANIFEST_URL}")"
    [[ "${active}" == "${expected}" ]] || fail "Existing AOSP checkout uses ${active}; selected manifest is ${expected}."

    configure_aosp_manifest_overlays "${root}"
    verify_aosp_manifest "${install_dir}" "${root}" true
    write_android_source_config existing "${root}"
}

configure_aosp_checkout() {
    local install_dir="$1"
    local source_root="${install_dir}/aosp"

    cat <<EOF

${BOLD}AOSP build/validation checkout${RESET}

EOF

    if [[ -d "${source_root}/.repo" ]]; then
        if managed_aosp_checkout_is_slim "${source_root}"; then
            cat <<EOF
1) Resume/synchronize existing TreeForge slim v2 checkout
2) Use another existing AOSP checkout
3) Save selection and defer checkout

EOF
        elif managed_aosp_checkout_is_legacy_partial "${source_root}"; then
            cat <<EOF
1) Review existing TreeForge slim v1 partial-clone checkout
   (recreate as slim v2 recommended)
2) Use another existing AOSP checkout
3) Save selection and defer checkout

EOF
        else
            cat <<EOF
1) Review existing legacy/full managed AOSP checkout
2) Use another existing AOSP checkout
3) Save selection and defer checkout

EOF
        fi
    else
        cat <<EOF
1) Initialize/synchronize a TreeForge slim v2 managed AOSP checkout
2) Use an existing AOSP checkout
3) Save selection and defer checkout

EOF
    fi

    prompt_choice AOSP_SOURCE_ACTION "Select" 1 1 2 3

    case "${AOSP_SOURCE_ACTION}" in
        1) sync_managed_aosp_source "${install_dir}" ;;
        2) configure_existing_aosp_source "${install_dir}" ;;
        3) write_android_source_config deferred "${source_root}" ;;
    esac
}


configure_avb_bringup_keys() {
    local install_dir="$1" mode="$2" provision=false
    case "${mode}" in
        user) return ;;
        maintainer|developer) ;;
        *) fail "Unknown installation mode: ${mode}" ;;
    esac

    prompt_yes_no provision "Provision/reuse TreeForge AVB development signing keys" yes
    if [[ "${provision}" != true ]]; then
        return 0
    fi

    local python_bin="${install_dir}/.venv/bin/python"
    [[ -x "${python_bin}" ]] || fail "TreeForge virtual-environment Python is unavailable."
    "${python_bin}" -m treeforge.setup.avb_keys \
        --repository-root "${install_dir}" \
        --aosp-root "${ANDROID_AOSP_ROOT:-${install_dir}/aosp}" \
        --device tangorpro
}

physical_memory_kib() {
    awk \
        '/^MemTotal:/ { print $2; exit }' \
        /proc/meminfo
}


physical_memory_gib() {
    local kib

    kib="$(
        physical_memory_kib
    )"

    awk \
        -v kib="${kib}" \
        'BEGIN { printf "%.1f\n", kib / 1024 / 1024 }'
}


physical_memory_whole_gib() {
    local kib

    kib="$(
        physical_memory_kib
    )"

    awk \
        -v kib="${kib}" \
        'BEGIN { printf "%d\n", (kib / 1024 / 1024) + 0.5 }'
}


required_disk_swap_gib() {
    local ram_gib="$1"

    if (( ram_gib < 32 )); then
        printf '%s\n' "64"
        return
    fi

    if (( ram_gib < 64 )); then
        printf '%s\n' "32"
        return
    fi

    printf '%s\n' "0"
}


active_disk_swap() {
    # Kernel-authoritative active disk-backed swap inventory.
    #
    # /proc/swaps columns:
    #   Filename Type Size(KiB) Used(KiB) Priority
    #
    # Emit NAME TYPE SIZE(bytes), excluding ZRAM.
    awk '
        NR > 1 && $1 !~ /^\/dev\/zram/ {
            printf "%s %s %.0f\n", $1, $2, $3 * 1024
        }
    ' \
        /proc/swaps \
        2>/dev/null \
        || true
}


active_disk_swap_total_gib() {
    active_disk_swap \
        | awk '
            {
                total += $3
            }

            END {
                gib = total / 1073741824

                if (gib == int(gib)) {
                    printf "%d\n", gib
                } else {
                    printf "%d\n", int(gib) + 1
                }
            }
        '
}


active_zram_swap() {
    # Kernel-authoritative active ZRAM inventory.
    #
    # /proc/swaps columns:
    #   Filename Type Size(KiB) Used(KiB) Priority
    #
    # Emit a compact human-readable line for each active zram device.
    awk '
        NR > 1 && $1 ~ /^\/dev\/zram/ {
            printf "%s %s %.1fG\n", $1, $2, $3 / 1024 / 1024
        }
    ' \
        /proc/swaps \
        2>/dev/null \
        || true
}


root_storage_device() {
    findmnt \
        -no SOURCE \
        / \
        2>/dev/null \
        || true
}


root_storage_rotational_state() {
    local source
    local parent

    source="$(
        root_storage_device
    )"

    if [[ -z "${source}" ]]; then
        return 0
    fi

    parent="$(
        lsblk \
            -ndo PKNAME \
            "${source}" \
            2>/dev/null \
            | head -n 1 \
            || true
    )"

    if [[ -z "${parent}" ]]; then
        parent="$(
            lsblk \
                -ndo KNAME \
                "${source}" \
                2>/dev/null \
                | head -n 1 \
                || true
        )"
    fi

    if [[ -z "${parent}" ]]; then
        return 0
    fi

    lsblk \
        -ndo ROTA \
        "/dev/${parent}" \
        2>/dev/null \
        | head -n 1 \
        || true
}


print_android_build_host_warning() {
    local ram_display="$1"
    local minimum_swap="$2"
    local rotational

    rotational="$(
        root_storage_rotational_state
    )"

    cat <<EOF

${YELLOW}${BOLD}ANDROID BUILD HOST MEMORY / STORAGE${RESET}

Physical RAM detected:
  ${ram_display} GiB

EOF

    if (( minimum_swap > 0 )); then
        cat <<EOF
Minimum disk-backed swap for this RAM tier:
  ${minimum_swap} GiB

This is a minimum supported TreeForge build-host value. If disk-backed swap
is configured for this RAM tier, setup will not allow the total to remain
below ${minimum_swap} GiB.

EOF
    else
        cat <<EOF
This host has at least 64 GiB of physical RAM.

TreeForge does not require additional disk-backed swap for this RAM tier.

EOF
    fi

    cat <<EOF
Large Android builds can exceed available physical memory. Without sufficient
swap, the kernel may terminate build processes because of an out-of-memory
condition.

Disk-backed swap can prevent that failure, but it is not additional RAM.
Under severe memory pressure the system can spend most of its time moving
pages between RAM and storage instead of compiling. This is commonly called
memory or drive thrashing.

The Android build workload also generates substantial parallel filesystem I/O.

TreeForge's supported Android build-host profile therefore expects SSD or
NVMe storage. A mechanical HDD can technically be used, but it is considered
unsupported for normal build performance and may become dramatically slower,
especially when paging occurs.

A swapfile reserves real filesystem capacity:
  32 GiB swap = approximately 32 GiB of storage
  64 GiB swap = approximately 64 GiB of storage

EOF

    case "${rotational}" in
        1)
            warn \
                "The filesystem containing / appears to be on rotational storage (HDD)."
            warn \
                "Android builds and swap-backed memory pressure may be extremely slow."
            ;;
        0)
            success \
                "The filesystem containing / appears to use non-rotational SSD/NVMe storage."
            ;;
        *)
            warn \
                "TreeForge could not determine whether the filesystem containing / uses SSD/NVMe storage."
            ;;
    esac

    cat <<EOF

${BOLD}TreeForge tested reference hosts${RESET}

Lenovo Legion Go:
  Auto VRAM
  Approximately 15.4 GiB RAM available to the operating system
  64 GiB disk-backed swap
  Observed Android build time: approximately 5 hours

Dell XPS 14 (2023):
  32 GiB RAM
  Fastest observed Android build time: 1 hour 48 minutes

These are observed TreeForge development results, not guarantees.
CPU performance, storage, thermals, ccache state, source state, parallelism,
and memory pressure can substantially change build duration.

EOF
}


persistent_swap_tokens_for_source() {
    local source="$1"
    local uuid=""
    local partuuid=""

    printf '%s\n' "${source}"

    if [[ -b "${source}" ]] \
        && command -v blkid >/dev/null 2>&1; then

        uuid="$(
            blkid \
                -s UUID \
                -o value \
                "${source}" \
                2>/dev/null \
                || true
        )"

        partuuid="$(
            blkid \
                -s PARTUUID \
                -o value \
                "${source}" \
                2>/dev/null \
                || true
        )"
    fi

    if [[ -n "${uuid}" ]]; then
        printf 'UUID=%s\n' "${uuid}"
    fi

    if [[ -n "${partuuid}" ]]; then
        printf 'PARTUUID=%s\n' "${partuuid}"
    fi
}


backup_fstab_once() {
    [[ -f /etc/fstab ]] \
        || return

    if [[ -f /etc/fstab.treeforge-backup ]]; then
        return
    fi

    if [[ "${EUID}" -eq 0 ]]; then
        cp \
            -a \
            /etc/fstab \
            /etc/fstab.treeforge-backup
    else
        sudo cp \
            -a \
            /etc/fstab \
            /etc/fstab.treeforge-backup
    fi
}


disable_persistent_swap_entry() {
    local source="$1"
    local tokens
    local temp_file

    [[ -f /etc/fstab ]] \
        || return

    backup_fstab_once

    tokens="$(
        persistent_swap_tokens_for_source \
            "${source}"
    )"

    temp_file="$(
        mktemp
    )"

    awk \
        -v tokens="${tokens}" '
        BEGIN {
            count = split(tokens, values, "\n")

            for (i = 1; i <= count; i++) {
                if (values[i] != "") {
                    targets[values[i]] = 1
                }
            }
        }

        /^[[:space:]]*#/ {
            print
            next
        }

        NF >= 3 && $3 == "swap" && ($1 in targets) {
            print "# TreeForge disabled replaced swap: " $0
            next
        }

        {
            print
        }
        ' \
        /etc/fstab \
        > "${temp_file}"

    if [[ "${EUID}" -eq 0 ]]; then
        cat "${temp_file}" \
            > /etc/fstab
    else
        sudo sh -c \
            'cat "$1" > /etc/fstab' \
            sh \
            "${temp_file}"
    fi

    rm -f "${temp_file}"
}


disable_existing_disk_swap() {
    local source
    local type
    local size
    local candidate
    local candidate_type
    local remaining_active_files=""

    #
    # Called only after the user explicitly chose replacement.
    #
    # Remove every ACTIVE swap file. Swap partitions are disabled and removed
    # from persistent activation, but are never erased or reformatted.
    #
    while read -r source type size; do
        [[ -n "${source}" ]] \
            || continue

        info \
            "Disabling disk-backed swap: ${source}"

        if [[ "${EUID}" -eq 0 ]]; then
            swapoff "${source}"
        else
            sudo swapoff "${source}"
        fi

        disable_persistent_swap_entry \
            "${source}"

        if [[ "${type}" == "file" \
            && -f "${source}" ]]; then

            info \
                "Removing replaced swapfile: ${source}"

            if [[ "${EUID}" -eq 0 ]]; then
                rm -f \
                    "${source}"
            else
                sudo rm -f \
                    "${source}"
            fi

            [[ ! -e "${source}" ]] \
                || fail \
                    "Replaced swapfile still exists after removal: ${source}"

            success \
                "Removed replaced swapfile: ${source}"
        else
            info \
                "Swap partition ${source} was disabled but left physically intact."
        fi
    done < <(
        active_disk_swap
    )

    #
    # Catch known inactive legacy swap files that are not present in
    # /proc/swaps. Only remove them when blkid confirms TYPE=swap.
    #
    for candidate in \
        /swap.img \
        /swapfile \
        /swapfile[0-9]*
    do
        [[ -f "${candidate}" ]] \
            || continue

        candidate_type="$(
            blkid \
                -p \
                -s TYPE \
                -o value \
                "${candidate}" \
                2>/dev/null \
                || true
        )"

        [[ "${candidate_type}" == "swap" ]] \
            || continue

        info \
            "Removing inactive replaced swapfile: ${candidate}"

        disable_persistent_swap_entry \
            "${candidate}"

        if [[ "${EUID}" -eq 0 ]]; then
            rm -f \
                "${candidate}"
        else
            sudo rm -f \
                "${candidate}"
        fi

        [[ ! -e "${candidate}" ]] \
            || fail \
                "Replaced swapfile still exists after removal: ${candidate}"

        success \
            "Removed replaced swapfile: ${candidate}"
    done

    #
    # Do not silently create /swapfileN if an old active swap file survived.
    #
    remaining_active_files="$(
        active_disk_swap \
            | awk '$2 == "file" { print $1 }'
    )"

    if [[ -n "${remaining_active_files}" ]]; then
        fail \
            "Active swap files remain after replacement cleanup: ${remaining_active_files//$'\n'/, }"
    fi

    success \
        "Previous disk-backed swap files have been removed."
}


available_root_storage_gib() {
    df \
        -Pk \
        / \
        | awk '
            NR == 2 {
                printf "%d\n", $4 / 1024 / 1024
            }
        '
}


next_swapfile_path() {
    local candidate="/swapfile"
    local number=2

    while [[ -e "${candidate}" ]]; do
        candidate="/swapfile${number}"
        number=$(( number + 1 ))
    done

    printf '%s\n' "${candidate}"
}


create_swapfile() {
    local size_gib="$1"
    local swapfile="$2"
    local available_gib

    available_gib="$(
        available_root_storage_gib
    )"

    printf '\nAvailable filesystem space on /:\n'
    printf '  approximately %s GiB\n' \
        "${available_gib}"

    printf 'Requested new swapfile:\n'
    printf '  %s GiB at %s\n\n' \
        "${size_gib}" \
        "${swapfile}"

    if (( available_gib <= size_gib )); then
        fail \
            "Insufficient free storage for a ${size_gib} GiB swapfile."
    fi

    info \
        "Allocating ${size_gib} GiB swapfile at ${swapfile}"

    # dd is intentionally used instead of fallocate for broad swapfile
    # filesystem compatibility and to avoid sparse/hole-backed files.
    if [[ "${EUID}" -eq 0 ]]; then
        dd \
            if=/dev/zero \
            of="${swapfile}" \
            bs=1M \
            count="$(( size_gib * 1024 ))" \
            status=progress

        chmod 600 "${swapfile}"
        mkswap "${swapfile}"
        swapon "${swapfile}"
    else
        sudo dd \
            if=/dev/zero \
            of="${swapfile}" \
            bs=1M \
            count="$(( size_gib * 1024 ))" \
            status=progress

        sudo chmod 600 "${swapfile}"
        sudo mkswap "${swapfile}"
        sudo swapon "${swapfile}"
    fi

    backup_fstab_once

    if ! awk -v swapfile="${swapfile}" '
        /^[[:space:]]*#/ {
            next
        }

        NF >= 3 && $1 == swapfile && $3 == "swap" {
            found = 1
            exit
        }

        END {
            exit found ? 0 : 1
        }
    ' /etc/fstab; then

        if [[ "${EUID}" -eq 0 ]]; then
            printf '%s none swap sw 0 0\n' \
                "${swapfile}" \
                >> /etc/fstab
        else
            printf '%s none swap sw 0 0\n' \
                "${swapfile}" \
                | sudo tee \
                    -a /etc/fstab \
                    >/dev/null
        fi
    fi

    success \
        "Swapfile ${swapfile} created and enabled."
}


prompt_swapfile_size() {
    local minimum="$1"
    local requested

    while true; do
        read -r -p \
            "New swapfile size in GiB [${minimum}]: " \
            requested

        requested="${requested:-${minimum}}"

        if [[ "${requested}" =~ ^[0-9]+$ ]] \
            && (( requested >= minimum )); then
            printf '%s\n' "${requested}"
            return
        fi

        warn \
            "The swapfile cannot be smaller than ${minimum} GiB for this configuration."
    done
}


configure_disk_swap() {
    local minimum="$1"
    local current_total
    local shortfall
    local action
    local new_minimum
    local size
    local swapfile
    local confirm=false

    current_total="$(
        active_disk_swap_total_gib
    )"

    printf '\n%sDisk-backed swap%s\n\n' \
        "${BOLD}" \
        "${RESET}"

    printf 'Current active disk-backed swap:\n'

    if active_disk_swap | grep -q .; then
        swapon \
            --show \
            --noheadings \
            --output=NAME,TYPE,SIZE \
            | grep -v '/dev/zram' \
            || true
    else
        printf '  none\n'
    fi

    printf '\nCurrent disk-backed total:\n'
    printf '  approximately %s GiB\n\n' \
        "${current_total}"

    if (( minimum == 0 )); then
        if (( current_total > 0 )); then
            success \
                "No additional disk-backed swap is required for this RAM tier."

            prompt_yes_no confirm \
                "Would you like to replace all current disk-backed swap files with one new swapfile" \
                no

            if [[ "${confirm}" != "true" ]]; then
                return 0
            fi

            new_minimum=32

            size="$(
                prompt_swapfile_size \
                    "${new_minimum}"
            )"

            disable_existing_disk_swap

            swapfile="$(
                next_swapfile_path
            )"

            create_swapfile \
                "${size}" \
                "${swapfile}"

            return 0
        fi

        prompt_yes_no confirm \
            "Would you like to create an optional disk-backed swapfile" \
            no

        if [[ "${confirm}" != "true" ]]; then
            return 0
        fi

        size="$(
            prompt_swapfile_size 32
        )"

        swapfile="$(
            next_swapfile_path
        )"

        create_swapfile \
            "${size}" \
            "${swapfile}"

        return 0
    fi

    if (( current_total >= minimum )); then
        success \
            "Existing disk-backed swap meets the ${minimum} GiB suggested minimum."

        prompt_yes_no confirm \
            "Would you like to replace all current disk-backed swap files with one new swapfile" \
            no

        if [[ "${confirm}" != "true" ]]; then
            return 0
        fi

        size="$(
            prompt_swapfile_size \
                "${minimum}"
        )"

        cat <<EOF

${YELLOW}${BOLD}SWAP REPLACEMENT${RESET}

TreeForge will:
  - disable every active disk-backed swap FILE;
  - remove those swap files;
  - remove/disable their persistent /etc/fstab swap entries;
  - leave swap PARTITIONS physically intact;
  - create one new swapfile.

EOF

        prompt_yes_no confirm \
            "Continue with replacing the current disk-backed swap files" \
            no

        if [[ "${confirm}" != "true" ]]; then
            return 0
        fi

        disable_existing_disk_swap

        swapfile="$(
            next_swapfile_path
        )"

        create_swapfile \
            "${size}" \
            "${swapfile}"

        return 0
    fi

    shortfall=$(( minimum - current_total ))

    warn \
        "This host is below the ${minimum} GiB suggested disk-backed swap value."

    warn \
        "Approximately ${shortfall} GiB more disk-backed swap would reach it."

    cat <<EOF

Choose what TreeForge should do:

  1) Keep the current disk-backed swap and add another swapfile
  2) Replace ALL current disk-backed swap files with one new swapfile
  3) Leave swap unchanged

Replacing existing swap:
  - removes active swap FILES such as /swap.img, /swapfile, /swapfile2;
  - disables swap PARTITIONS but does not erase them;
  - removes/disables matching persistent /etc/fstab swap entries.

EOF

    prompt_choice action \
        "Select" \
        "2" \
        1 \
        2 \
        3

    case "${action}" in
        1)
            new_minimum="${shortfall}"
            ;;
        2)
            new_minimum="${minimum}"

            prompt_yes_no confirm \
                "Confirm replacement of all current disk-backed swap files" \
                no

            if [[ "${confirm}" != "true" ]]; then
                warn \
                    "Disk-backed swap replacement cancelled."
                return 0
            fi
            ;;
        3)
            warn \
                "Disk-backed swap was left unchanged."
            return 0
            ;;
    esac

    size="$(
        prompt_swapfile_size \
            "${new_minimum}"
    )"

    cat <<EOF

${YELLOW}${BOLD}SSD SPACE WARNING${RESET}

The new swapfile will reserve approximately ${size} GiB of real filesystem
space.

EOF

    prompt_yes_no confirm \
        "Continue with this swapfile allocation" \
        no

    if [[ "${confirm}" != "true" ]]; then
        warn \
            "Swapfile configuration cancelled."
        return 0
    fi

    if [[ "${action}" == "2" ]]; then
        disable_existing_disk_swap
    fi

    swapfile="$(
        next_swapfile_path
    )"

    create_swapfile \
        "${size}" \
        "${swapfile}"
}


configure_zram() {
    local configure=false
    local percent
    local temp_file
    local config_percent
    local expected_bytes
    local actual_bytes
    local actual_percent

    printf '\n%sZRAM%s\n\n' \
        "${BOLD}" \
        "${RESET}"

    cat <<EOF
ZRAM uses compressed physical RAM as swap.

It can sometimes reduce disk paging, but it consumes CPU and physical memory
and often makes little practical difference on systems with sufficient RAM.

ZRAM is optional and does NOT count toward TreeForge's disk-backed swap
minimum.

EOF

    printf 'Current ZRAM:\n'

    if active_zram_swap | grep -q .; then
        active_zram_swap
    else
        printf '  none active\n'
    fi

    printf '\n'

    prompt_yes_no configure \
        "Would you like to configure ZRAM" \
        no

    if [[ "${configure}" != "true" ]]; then
        return 0
    fi

    while true; do
        read -r -p \
            "ZRAM size as percentage of physical RAM [50]: " \
            percent

        percent="${percent:-50}"

        case "${percent}" in
            ''|*[!0-9]*)
                warn \
                    "ZRAM percentage must be between 1 and 100."
                ;;
            *)
                if (( percent >= 1 && percent <= 100 )); then
                    break
                fi

                warn \
                    "ZRAM percentage must be between 1 and 100."
                ;;
        esac
    done

    if ! command -v apt-get >/dev/null 2>&1; then
        warn \
            "Automatic ZRAM configuration currently requires Ubuntu/Debian with apt-get."
        return 0
    fi

    info "Installing ZRAM support"

    if [[ "${EUID}" -eq 0 ]]; then
        apt-get update
        apt-get install -y zram-tools
    else
        sudo apt-get update
        sudo apt-get install -y zram-tools
    fi

    temp_file="$(
        mktemp
    )"

    cat > "${temp_file}" <<EOF
# Managed by TreeForge setup.
PERCENT=${percent}
EOF

    if [[ "${EUID}" -eq 0 ]]; then
        if [[ -f /etc/default/zramswap \
            && ! -f /etc/default/zramswap.treeforge-backup ]]; then
            cp \
                -a \
                /etc/default/zramswap \
                /etc/default/zramswap.treeforge-backup
        fi

        cat "${temp_file}" \
            > /etc/default/zramswap
    else
        if [[ -f /etc/default/zramswap \
            && ! -f /etc/default/zramswap.treeforge-backup ]]; then
            sudo cp \
                -a \
                /etc/default/zramswap \
                /etc/default/zramswap.treeforge-backup
        fi

        sudo sh -c \
            'cat "$1" > /etc/default/zramswap' \
            sh \
            "${temp_file}"
    fi

    rm -f "${temp_file}"

    # zram-tools can leave the previous size in place if zram0 is already
    # initialized. Stop the service and reset a surviving zram0 before start.
    if [[ "${EUID}" -eq 0 ]]; then
        systemctl stop zramswap.service \
            2>/dev/null \
            || true

        if [[ -e /sys/block/zram0/reset ]]; then
            swapoff /dev/zram0 \
                2>/dev/null \
                || true

            printf '1\n' \
                > /sys/block/zram0/reset
        fi

        systemctl start zramswap.service
    else
        sudo systemctl stop zramswap.service \
            2>/dev/null \
            || true

        if [[ -e /sys/block/zram0/reset ]]; then
            sudo swapoff /dev/zram0 \
                2>/dev/null \
                || true

            printf '1\n' \
                | sudo tee \
                    /sys/block/zram0/reset \
                    >/dev/null
        fi

        sudo systemctl start zramswap.service
    fi

    config_percent="$(
        awk \
            -F= \
            '$1 == "PERCENT" { print $2; exit }' \
            /etc/default/zramswap \
            2>/dev/null \
            || true
    )"

    if [[ "${config_percent}" != "${percent}" ]]; then
        fail \
            "ZRAM configuration file does not contain the requested ${percent}% value."
    fi

    expected_bytes="$(
        awk \
            -v percent="${percent}" \
            '/^MemTotal:/ {
                printf "%.0f\n", $2 * 1024 * percent / 100
                exit
            }' \
            /proc/meminfo
    )"

    actual_bytes="$(
        cat \
            /sys/block/zram0/disksize \
            2>/dev/null \
            || true
    )"

    if [[ -z "${actual_bytes}" ]]; then
        fail \
            "ZRAM service started but the active zram0 disk size could not be read."
    fi

    if ! awk \
        -v expected="${expected_bytes}" \
        -v actual="${actual_bytes}" \
        'BEGIN {
            delta = actual - expected
            if (delta < 0) {
                delta = -delta
            }

            tolerance = expected * 0.01
            exit(delta <= tolerance ? 0 : 1)
        }'; then

        actual_percent="$(
            awk \
                -v actual="${actual_bytes}" \
                '/^MemTotal:/ {
                    total = $2 * 1024
                    printf "%.1f\n", (actual / total) * 100
                    exit
                }' \
                /proc/meminfo
        )"

        fail \
            "ZRAM requested ${percent}% but the active zram0 size is approximately ${actual_percent}% of physical RAM."
    fi

    success \
        "ZRAM configured and verified at ${percent}% of physical RAM."
}


configure_optional_host_memory() {
    local configure=false
    local ram_display
    local ram_gib
    local minimum_swap

    printf '\n%sOptional Android build host memory settings%s\n\n' \
        "${BOLD}" \
        "${RESET}"

    prompt_yes_no configure \
        "Would you like to set up optional Android build host memory settings" \
        no

    if [[ "${configure}" != "true" ]]; then
        return
    fi

    ram_display="$(
        physical_memory_gib
    )"

    ram_gib="$(
        physical_memory_whole_gib
    )"

    minimum_swap="$(
        required_disk_swap_gib \
            "${ram_gib}"
    )"

    print_android_build_host_warning \
        "${ram_display}" \
        "${minimum_swap}"

    if (( ram_gib < 12 )); then
        cat <<EOF
${RED}${BOLD}LOW MEMORY HOST WARNING${RESET}

This host has less than 12 GiB of physical RAM.

TreeForge does not consider less than 12 GiB RAM a practical Android build
host. The 64 GiB disk-backed swap profile will still be offered to reduce the
chance of an immediate OOM failure, but severe thrashing may make builds
impractically slow.

EOF
    fi

    configure_disk_swap \
        "${minimum_swap}"

    configure_zram

    printf '\n%sFinal swap configuration%s\n\n' \
        "${BOLD}" \
        "${RESET}"

    swapon --show \
        || true
}


print_header() {
    cat <<EOF
${BLUE}${BOLD}=====================================
 TreeForge Setup
=====================================${RESET}

Fresh installation, update/repair, Android 15 source configuration, and AOSP
build-host preparation.

Press Ctrl+C at any time to cancel.

EOF
}

configure_treeforge_installation() {
    local install_dir="$1"
    local existing=false current_mode selected_repo current_repo="" install_system=true

    if is_treeforge_checkout "${install_dir}"; then
        existing=true
        current_mode="$(read_install_mode)"
    else
        current_mode=""
    fi

    prompt_installation_mode "${current_mode}"
    local mode="${SELECTED_INSTALL_MODE}"

    if [[ "${existing}" == true ]]; then
        current_repo="$(git -C "${install_dir}" remote get-url origin 2>/dev/null || true)"
        [[ -n "${current_repo}" ]] || fail "Existing TreeForge checkout has no origin remote."
    fi

    prompt_repository_source \
        selected_repo \
        "TreeForge" \
        "${TREEFORGE_PUBLIC_REPO_URL}" \
        "${TREEFORGE_PRIVATE_REPO_URL}" \
        "${DEFAULT_REPO_SOURCE}" \
        "${DEFAULT_REPO_URL}" \
        "${current_repo}" \
        "${mode}"

    validate_repo_url "${selected_repo}"
    configure_repository_access "${selected_repo}"

    if [[ "${existing}" == true ]]; then
        if [[ "${selected_repo}" != "${current_repo}" ]]; then
            git -C "${install_dir}" remote set-url origin "${selected_repo}"
        fi
        update_existing_treeforge "${install_dir}"
    else
        if [[ -e "${install_dir}" ]]; then
            fail "Install path exists but is not a TreeForge checkout: ${install_dir}"
        fi
        clone_treeforge "${selected_repo}" "${install_dir}" "${mode}"
    fi

    prompt_yes_no install_system "Check/install required ${mode} mode system dependencies" yes
    if [[ "${install_system}" == true ]]; then
        install_treeforge_mode_dependencies "${mode}"
    fi

    install_treeforge_python_environment "${install_dir}" "${mode}"

    install_optional_treeforge_android_transport_tools "${install_dir}"

    configure_android_source_selection "${install_dir}" "${mode}"
    configure_avb_bringup_keys "${install_dir}" "${mode}"
    configure_aosp_checkout "${install_dir}"
    configure_optional_host_memory
}


print_installation_complete() {
    local install_dir="$1"

    cat <<EOF

${GREEN}${BOLD}=====================================
 TreeForge Installation Complete
=====================================${RESET}

TreeForge is installed and configured successfully.

Repository:
  ${install_dir}

To start using TreeForge:

  cd "${install_dir}"
  source .venv/bin/activate

Then verify or explore the CLI with:

  treeforge doctor
  treeforge --help

Your Android/AOSP, AVB, host-tool, and optional build-host settings from this
setup run have been saved or applied according to the choices you made.

EOF
}


[[ $# -eq 0 || "${1:-}" == -h || "${1:-}" == --help ]] || fail "setup.sh is interactive."

if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then
    usage
    exit 0
fi

print_header
ensure_setup_bootstrap_dependencies

prompt_value INSTALL_DIR \
    "TreeForge installation directory (press Enter for default)" \
    "${DEFAULT_INSTALL_DIR}"

INSTALL_DIR="$(expand_path "${INSTALL_DIR}")"

configure_treeforge_installation "${INSTALL_DIR}"

print_installation_complete "${INSTALL_DIR}"
