#!/bin/bash
set -o pipefail
set -e

name="plugin.video.torrest"
username="i96751414"
repository="torrest-cpp"
release="latest"
bin_path="${name}/resources/bin"

declare -A platform_types=([android]=lib)
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
    case "${1}" in
    "${p}"*)
      case "${2}" in
      "${platform_types["${p}"]}"*) return 0 ;;
      esac
      return 1
      ;;
    esac
  done
  # Default type is torrest
  [ "${2}" = "torrest" ]
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
  (cd "${build_path}/${binary_path}" && curl -sSL "${url}" >tmp.zip && unzip -o tmp.zip && rm tmp.zip)
  # generate the zip file
  zip_name="${name}-${version}.${platform}.zip"
  info "Creating ${zip_name}"
  createBaseZip "${build_path}/${zip_name}"
  (cd "${build_path}" && zip -9 -r -g "${zip_name}" "${binary_path}")
done

if [ "${all}" = true ] && [ -d "${build_path}/${bin_path}" ] && [ -n "$(ls -A "${build_path}/${bin_path}")" ]; then
  info "Generating zip with all binaries"
  zip_name="${name}-${version}.all.zip"
  createBaseZip "${build_path}/${zip_name}"
  (cd "${build_path}" && zip -9 -r -g "${zip_name}" "${bin_path}")
fi

info "Cleaning build artifacts"
rm -rf "${build_path:?}/${name}"
