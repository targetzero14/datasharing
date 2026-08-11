#!/bin/bash
# Installs the Talking Head Toolkit panel for the current user (macOS).
set -e

SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/Application Support/Adobe/CEP/extensions/com.talkingheadtoolkit.panel"

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -R "$SRC" "$DEST"
# Don't ship the install helpers into the extension itself
rm -rf "$DEST/install"

# Allow unsigned (debug) extensions for the CSXS runtimes recent Premiere
# versions use. Harmless if a version isn't installed.
for v in 9 10 11 12; do
  defaults write "com.adobe.CSXS.$v" PlayerDebugMode 1
done

echo "Installed to: $DEST"
echo "Restart Premiere Pro, then open Window > Extensions > Talking Head Toolkit."
