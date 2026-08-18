#!/usr/bin/env bash
#
# Install the panel for local development on macOS.
#
# Unsigned extensions only load when PlayerDebugMode is on, so this sets that
# flag for every CSXS version Premiere might be using, then copies the panel
# into the per-user CEP extensions folder.

set -euo pipefail

BUNDLE="com.thinksharper.talkinghead"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/Library/Application Support/Adobe/CEP/extensions/$BUNDLE"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "This script is macOS only. On Windows run install.ps1 instead." >&2
  exit 1
fi

echo "Enabling PlayerDebugMode..."
for v in 9 10 11 12; do
  defaults write "com.adobe.CSXS.$v" PlayerDebugMode 1
done
# Premiere reads these at launch, and the prefs daemon caches them.
killall cfprefsd 2>/dev/null || true

echo "Installing to $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$SRC/CSXS" "$SRC/css" "$SRC/js" "$SRC/jsx" "$SRC/index.html" "$SRC/.debug" "$DEST/"

echo
echo "Done. Restart Premiere Pro, then open:"
echo "  Window > Extensions > Talking Head Overlay"
echo
echo "To debug the panel UI, browse to http://localhost:8088 while it is open."
