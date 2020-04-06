#!/bin/bash

set -ex

name="plugin.video.torrest"
username="i96751414"
repository="torrest"
release="latest"

script_path="$(dirname "$(realpath "${0}")")"
build_path="${script_path}/build"
version=$(git describe --tags | cut -c2-)
if [ -z "${version}" ]; then
  version=dev
fi

cd "${script_path}"

function createBaseZip() {
  git archive --format zip --prefix "${name}/" --output "${1}" HEAD
}

# More one https://developer.github.com/v3/repos/releases/
response=$(curl -s -X GET "https://api.github.com/repos/${username}/${repository}/releases/${release}")
for url in $(jq -r ".assets | .[] | .browser_download_url" <<<"${response}"); do
  platform=$(echo "${url}" | awk -F. '{print $(NF-1)}')
  binary_path="${name}/resources/bin/${platform}"
  mkdir -p "${build_path}/${binary_path}"
  (cd "${build_path}/${binary_path}" && curl -sSL "${url}" >tmp.zip && unzip -o tmp.zip && rm tmp.zip)
  # generate the zip file
  zip_name="${name}-${version}.${platform}.zip"
  createBaseZip "${build_path}/${zip_name}"
  (cd "${build_path}" && zip -9 -r -g "${zip_name}" "${binary_path}")
done
