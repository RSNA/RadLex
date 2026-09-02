#!/bin/bash
set -euo pipefail

#
# install ROBOT (https://robot.obolibrary.org/) for local development or CI
#
# Downloads the pinned ROBOT_VERSION jar and the official `robot` launcher
# script from the ontodev/robot GitHub repo, verifying both against pinned
# checksums, into ROBOT_INSTALL_DIR. Add that directory to your PATH to run
# `robot` directly, e.g.:
#   export PATH="$PWD/tests/scripts/.robot:$PATH"
#

ROBOT_VERSION="${ROBOT_VERSION:-1.9.10}"
ROBOT_JAR_SHA256="${ROBOT_JAR_SHA256:-16a73c074f3df359a7338a84b4e0788785fe06117f931bb9796e9619ea776105}"
ROBOT_SCRIPT_SHA256="${ROBOT_SCRIPT_SHA256:-0f2c4bb7dc25be9fb1dad37f2b8c07336d0e2c0ef3d3983e952c23d8b180a5b0}"
ROBOT_INSTALL_DIR="${ROBOT_INSTALL_DIR:-tests/scripts/.robot}"

sha256_check() {
  local file="$1" expected="$2" actual
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$file" | awk '{print $1}')"
  else
    actual="$(shasum -a 256 "$file" | awk '{print $1}')"
  fi
  if [ "$actual" != "$expected" ]; then
    echo "Checksum mismatch for $file: expected $expected, got $actual" >&2
    return 1
  fi
}

mkdir -p "$ROBOT_INSTALL_DIR"
ROBOT_INSTALL_DIR="$(cd "$ROBOT_INSTALL_DIR" && pwd)"

if [ "$(cat "$ROBOT_INSTALL_DIR/VERSION" 2>/dev/null)" != "$ROBOT_VERSION" ]; then
  echo "Downloading ROBOT v${ROBOT_VERSION}..." >&2

  curl -fsSL "https://github.com/ontodev/robot/releases/download/v${ROBOT_VERSION}/robot.jar" \
    --output "$ROBOT_INSTALL_DIR/robot.jar"
  sha256_check "$ROBOT_INSTALL_DIR/robot.jar" "$ROBOT_JAR_SHA256"

  curl -fsSL "https://raw.githubusercontent.com/ontodev/robot/v${ROBOT_VERSION}/bin/robot" \
    --output "$ROBOT_INSTALL_DIR/robot"
  sha256_check "$ROBOT_INSTALL_DIR/robot" "$ROBOT_SCRIPT_SHA256"
  chmod +x "$ROBOT_INSTALL_DIR/robot"

  echo "$ROBOT_VERSION" > "$ROBOT_INSTALL_DIR/VERSION"
fi

if [ -n "${GITHUB_PATH:-}" ]; then
  echo "$ROBOT_INSTALL_DIR" >> "$GITHUB_PATH"
else
  echo "ROBOT installed to $ROBOT_INSTALL_DIR/robot" >&2
  echo "Add it to your PATH: export PATH=\"$ROBOT_INSTALL_DIR:\$PATH\"" >&2
fi
