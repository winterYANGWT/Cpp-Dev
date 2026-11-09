#!/bin/sh
# Installs the tools for the CPP-DEV quality gate on a Debian or Ubuntu system,
# such as the debian:13-slim image that CI uses. Run it as root or as a user
# with sudo:
#
#   scripts/install_linux_tools.sh [--doxygen] VENV_DIR
#
# Then add VENV_DIR/bin to PATH. The script has two parts. The distribution
# packages (compiler, Python, git, GoogleTest) can come from any recent
# release; on another distribution, replace that part with its package
# manager. The tools whose version affects results come from PyPI or from a
# pinned Doxygen release and are the same on every image.
set -eu

# Pinned Doxygen release, with the SHA-256 that GitHub lists for the asset.
doxygen_version=1.15.0
doxygen_sha256=0ec2e5b2c3cd82b7106d19cb42d8466450730b8cb7a9e85af712be38bf4523a1

with_doxygen=false
if [ "${1:-}" = "--doxygen" ]; then
  with_doxygen=true
  shift
fi
if [ "$#" -ne 1 ]; then
  echo "usage: $0 [--doxygen] VENV_DIR" >&2
  exit 2
fi
venv_dir=$1
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

sudo=""
if [ "$(id -u)" -ne 0 ]; then
  sudo=sudo
fi

# Distribution packages.
$sudo env DEBIAN_FRONTEND=noninteractive apt-get update
$sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ca-certificates curl g++ git libgtest-dev python3 python3-venv

# Tools with recommended versions; see docs/tool-versions.md.
python3 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --disable-pip-version-check --quiet \
  -r "$script_dir/tool-requirements.txt"

if [ "$with_doxygen" = true ]; then
  archive="$venv_dir/doxygen-$doxygen_version.linux.bin.tar.gz"
  tag=Release_$(echo "$doxygen_version" | tr . _)
  curl -fsSL -o "$archive" \
    "https://github.com/doxygen/doxygen/releases/download/$tag/doxygen-$doxygen_version.linux.bin.tar.gz"
  echo "$doxygen_sha256  $archive" | sha256sum -c -
  tar -xzf "$archive" -C "$venv_dir"
  ln -sf "$venv_dir/doxygen-$doxygen_version/bin/doxygen" "$venv_dir/bin/doxygen"
  rm "$archive"
fi

echo "Installed the tools in $venv_dir/bin; add it to PATH."
