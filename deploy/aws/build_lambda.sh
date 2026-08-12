#!/usr/bin/env bash
# Build and package the GIE Bedrock Agents Lambda zip.
# Usage: ./build_lambda.sh [--clean]
#
# Produces: ../../dist/gie_bedrock_agents.zip
# The zip contains all handler modules in the root (no sub-directory) so that
# Lambda can import them directly, e.g. handler = "dispatcher.lambda_handler".

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HANDLERS_DIR="$SCRIPT_DIR/lambda_handlers"
DIST_DIR="$SCRIPT_DIR/../../dist"
BUILD_DIR="$DIST_DIR/lambda_build"
ZIP_OUT="$DIST_DIR/gie_bedrock_agents.zip"

if [[ "${1:-}" == "--clean" ]]; then
  echo "Cleaning previous build..."
  rm -rf "$BUILD_DIR" "$ZIP_OUT"
fi

echo "Creating build directory: $BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "Copying Lambda handler modules..."
cp "$HANDLERS_DIR"/*.py "$BUILD_DIR/"

echo "Installing runtime dependencies into build directory..."
# boto3 is provided by the Lambda runtime (AWS SDK layer) — no need to bundle it.
# If you add other deps, pip install them here:
# pip install --quiet --target "$BUILD_DIR" somepackage

echo "Creating zip archive: $ZIP_OUT"
mkdir -p "$DIST_DIR"
(cd "$BUILD_DIR" && zip -r "$ZIP_OUT" . -x "*.pyc" -x "__pycache__/*")

echo "Build complete: $ZIP_OUT ($(du -sh "$ZIP_OUT" | cut -f1))"
