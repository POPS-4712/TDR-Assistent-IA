#!/bin/sh
set -eu

ARCHITECTURE="${1:-arm64}"
VALIDATE_ONLY="${VALIDATE_ONLY:-0}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VERSION=$(tr -d '\r\n' < "$ROOT/VERSION")
HOST_ARCH=$(uname -m)
case "$HOST_ARCH" in
  x86_64) HOST_ARCH="x64" ;;
  arm64) HOST_ARCH="arm64" ;;
esac

case "$ARCHITECTURE" in
  x64|arm64) ;;
  *) echo "Unsupported target architecture: $ARCHITECTURE" >&2; exit 2 ;;
esac
if [ "$HOST_ARCH" != "$ARCHITECTURE" ]; then
  echo "PLATFORM UNAVAILABLE: macOS $ARCHITECTURE packages must be built on a matching macOS $ARCHITECTURE host. Current host is $HOST_ARCH." >&2
  exit 3
fi
for path in "$ROOT/docker-compose.prod.yml" "$ROOT/packaging/common/service_manager.py" "$ROOT/packaging/common/scan_artifact.py" "$ROOT/packaging/common/release_manifest.py"; do
  [ -f "$path" ] || { echo "Required packaging file is missing: $path" >&2; exit 2; }
done
if [ "$VALIDATE_ONLY" = "1" ]; then
  echo "BUILD VALIDATED: macOS $ARCHITECTURE package definition $VERSION"
  exit 0
fi
command -v pyinstaller >/dev/null 2>&1 || { echo "NOT BUILT: PyInstaller is required for a native macOS launcher." >&2; exit 4; }
command -v hdiutil >/dev/null 2>&1 || { echo "NOT BUILT: hdiutil is required to build a DMG." >&2; exit 4; }
command -v pkgbuild >/dev/null 2>&1 || { echo "NOT BUILT: pkgbuild is required to create the application bundle payload." >&2; exit 4; }
command -v codesign >/dev/null 2>&1 || { echo "NOT BUILT: codesign is required to verify the macOS bundle." >&2; exit 4; }
command -v file >/dev/null 2>&1 || { echo "NOT BUILT: file is required to verify the launcher architecture." >&2; exit 4; }

BUILD="$ROOT/packaging/.build/macos-$ARCHITECTURE"
APP="$BUILD/Automation Center.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources/app"
VERIFY_MOUNT="$BUILD/verify-mounted"
OUTPUT="$ROOT/dist/macos-$ARCHITECTURE"
DMG_PATH="$OUTPUT/AutomationCenter-${VERSION}-macos-${ARCHITECTURE}.dmg"
rm -rf "$BUILD"
mkdir -p "$MACOS" "$RESOURCES" "$OUTPUT"
rm -f "$DMG_PATH"

tar -C "$ROOT" --exclude=.git --exclude=.env --exclude='.env.*' --exclude=dist --exclude=node_modules --exclude=output --exclude=postgres-data --exclude=.n8n --exclude=__pycache__ --exclude=.build --exclude=tests --exclude=test --exclude='*.log' --exclude='*.pem' --exclude='*.key' --exclude='*.p12' --exclude='*.pfx' --exclude='playwright/linkedin.json' --exclude='playwright/jobs.json' --exclude='playwright/jobs-history.json' -cf - . | tar -C "$RESOURCES" -xf -
pyinstaller --noconfirm --clean --onefile --name AutomationCenter --distpath "$BUILD/launcher" --workpath "$BUILD/pyinstaller-work" --specpath "$BUILD" "$ROOT/packaging/common/service_manager.py"
cp "$BUILD/launcher/AutomationCenter" "$MACOS/AutomationCenter"
chmod 0755 "$MACOS/AutomationCenter"
printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>' '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' '<plist version="1.0"><dict><key>CFBundleExecutable</key><string>AutomationCenter</string><key>CFBundleIdentifier</key><string>local.automationcenter.app</string><key>CFBundleName</key><string>Automation Center</string><key>CFBundleShortVersionString</key><string>'"$VERSION"'</string><key>CFBundleVersion</key><string>'"$VERSION"'</string><key>LSMinimumSystemVersion</key><string>12.0</string></dict></plist>' > "$CONTENTS/Info.plist"
file "$MACOS/AutomationCenter" | grep -Eq "$( [ "$ARCHITECTURE" = x64 ] && echo 'x86_64|64-bit x86_64' || echo 'arm64|64-bit arm64' )"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
python3 "$ROOT/packaging/common/scan_artifact.py" "$APP"
hdiutil create -volname "Automation Center" -srcfolder "$APP" -ov -format UDZO "$DMG_PATH"
python3 "$ROOT/packaging/common/scan_artifact.py" "$DMG_PATH"
mkdir -p "$VERIFY_MOUNT"
ATTACH_OUTPUT=$(hdiutil attach -nobrowse -readonly -mountpoint "$VERIFY_MOUNT" "$DMG_PATH")
python3 "$ROOT/packaging/common/scan_artifact.py" "$VERIFY_MOUNT"
file "$VERIFY_MOUNT/Automation Center.app/Contents/MacOS/AutomationCenter" | grep -Eq "$( [ "$ARCHITECTURE" = x64 ] && echo 'x86_64|64-bit x86_64' || echo 'arm64|64-bit arm64' )"
hdiutil detach "$VERIFY_MOUNT" >/dev/null
python3 "$ROOT/packaging/common/release_manifest.py" record --artifact "$DMG_PATH" --platform "macos-$ARCHITECTURE" --architecture "$ARCHITECTURE" --format dmg
python3 "$ROOT/packaging/common/release_manifest.py" verify
echo "PASS: macOS $ARCHITECTURE genuine artifact written to $DMG_PATH"
