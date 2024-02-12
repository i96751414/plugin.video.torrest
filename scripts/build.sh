#!/bin/bash
set -o pipefail
set -e

name="plugin.video.torrest"
username="i96751414"
repository="torrest-cpp"
release="latest"
bin_path="${name}/resources/bin"
lib_path="${name}/lib"

declare -A platform_types=(["android.*"]=".*")
declare -A shared_lib_extensions=([linux]=".so" [android]=".so" [darwin]=".dylib" [windows]=".dll")
declare -A executable_extensions=([windows]=".exe")

repo_path="$(dirname "$(dirname "$(realpath "${0}")")")"
build_path="${repo_path}/build"
version=$(git describe --tags | cut -c2-)
if [ -z "${version}" ]; then
  version=dev
fi

function printUsage() {
  cat <<EOF
Usage: $(basename "${0}") [OPTIONS]

Script for building ${name} addon zips with the desired
version of the torrest binary (see https://github.com/${username}/${repository}).

optional arguments:
  -v <version>  Build version (default: ${version})
  -r <version>  Torrest binary version (default: ${release})
  -p <platform> Only build specified platform
  -a            Also build zip with all binaries
  -c            Clean build directory
  -h            Show this message
EOF
}

all=false
clean=false
platforms=()

while getopts "r:v:p:ach" flag; do
  case "${flag}" in
  r) release="${OPTARG}" ;;
  v) version="${OPTARG}" ;;
  p) platforms+=("${OPTARG}") ;;
  a) all=true ;;
  c) clean=true ;;
  h)
    printUsage
    exit 0
    ;;
  ?)
    printUsage
    exit 1
    ;;
  esac
done

cd "${repo_path}"

function elementIn() {
  local e match="$1"
  shift
  for e; do [ "${e}" == "${match}" ] && return 0; done
  return 1
}

function createBaseZip() {
  git archive --format zip -9 --prefix "${name}/" --output "${1}" HEAD
}

function checkPlatformType() {
  for p in "${!platform_types[@]}"; do
    if grep -Eq -- "^${p}" <<<"${1}"; then
      if grep -Eq -- "^${platform_types["${p}"]}" <<<"${2}"; then
        return 0
      fi
      return 1
    fi
  done
  # Default type is torrest
  [ "${2}" = "torrest" ]
}

function generatePlatformConstants() {
  local platform="${1}"
  local system="${platform%%_*}"
  cat <<EOF
# Automatically generated file, do not edit.

PLATFORM = "${platform}"
LIB_NAME = "libtorrest${shared_lib_extensions["${system}"]}"
EXE_NAME = "torrest${executable_extensions["${system}"]}"
EOF
}

function info() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ${1}"
}

if [ "${clean}" == true ]; then
  info "Cleaning build directory"
  rm -rf "${build_path}"
fi

# More on https://developer.github.com/v3/repos/releases/
info "Getting ${release} release from ${username}/${repository}"
response=$(curl -s -X GET "https://api.github.com/repos/${username}/${repository}/releases/${release}")
for url in $(jq -er ".assets | .[] | .browser_download_url" <<<"${response}"); do
  file_name="$(basename "${url}")"
  platform=$(awk -F. '{print $(NF-1)}' <<<"${file_name}")
  type=$(awk -F. '{print $1}' <<<"${file_name}")
  if [ ${#platforms[@]} -gt 0 ] && ! elementIn "${platform}" "${platforms[@]}" || ! checkPlatformType "${platform}" "${type}"; then
    continue
  fi

  binary_path="${bin_path}/${platform}"
  mkdir -p "${build_path}/${binary_path}"
  info "Downloading ${type} (${platform}) : ${url}"
  (cd "${build_path}/${binary_path}" && curl -sSL "${url}" >tmp.zip && unzip -q -o tmp.zip && rm tmp.zip)

  zip_name="${name}-${version}.${platform}.zip"
  if [ ! -f "${build_path}/${zip_name}" ]; then
    info "Creating ${zip_name}"
    createBaseZip "${build_path}/${zip_name}"
  fi

  mkdir -p "${build_path}/${lib_path}"
  info "Generating platform (${platform}) constants"
  (cd "${build_path}/${lib_path}" && generatePlatformConstants "${platform}" >"constants.py")

  info "Updating ${zip_name} with (${platform}) binary and constants"
  (cd "${build_path}" && zip -9 -r -u "${zip_name}" "${binary_path}" "${lib_path}")
done

if [ "${all}" = true ] && [ -d "${build_path}/${bin_path}" ] && [ -n "$(ls -A "${build_path}/${bin_path}")" ]; then
  info "Generating zip with all binaries"
  zip_name="${name}-${version}.all.zip"
  createBaseZip "${build_path}/${zip_name}"
  (cd "${build_path}" && zip -9 -r -g "${zip_name}" "${bin_path}")
fi

info "Cleaning build artifacts"
rm -rf "${build_path:?}/${name}"
