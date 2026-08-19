#!/usr/bin/env sh
set -eu

ARCHITECTURE="${1:-amd64}"
VALIDATE_ONLY="${VALIDATE_ONLY:-0}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VERSION=$(tr -d '\r\n' < "$ROOT/VERSION")
HOST_RAW=$(uname -m)
case "$HOST_RAW" in
  x86_64|amd64) HOST_ARCH="amd64"; RELEASE_ARCH="x64" ;;
  aarch64|arm64) HOST_ARCH="arm64"; RELEASE_ARCH="arm64" ;;
  *) HOST_ARCH="$HOST_RAW"; RELEASE_ARCH="$HOST_RAW" ;;
esac
case "$ARCHITECTURE" in
  amd64) RELEASE_ARCH="x64" ;;
  arm64) RELEASE_ARCH="arm64" ;;
  *) echo "Unsupported target architecture: $ARCHITECTURE" >&2; exit 2 ;;
esac

if [ "$HOST_ARCH" != "$ARCHITECTURE" ]; then
  echo "PLATFORM UNAVAILABLE: Linux $ARCHITECTURE packages must be built on a matching Linux $ARCHITECTURE host. Current host is $HOST_ARCH." >&2
  exit 3
fi
for path in "$ROOT/docker-compose.prod.yml" "$ROOT/packaging/common/service_manager.py" "$ROOT/packaging/common/scan_artifact.py" "$ROOT/packaging/common/release_manifest.py"; do
  [ -f "$path" ] || { echo "Required packaging file is missing: $path" >&2; exit 2; }
done
if [ "$VALIDATE_ONLY" = "1" ]; then
  echo "BUILD VALIDATED: Linux $ARCHITECTURE package definition $VERSION"
  exit 0
fi
command -v pyinstaller >/dev/null 2>&1 || { echo "NOT BUILT: PyInstaller is required for a native Linux launcher." >&2; exit 4; }
command -v dpkg-deb >/dev/null 2>&1 || { echo "NOT BUILT: dpkg-deb is required to build the DEB package." >&2; exit 4; }
command -v python3 >/dev/null 2>&1 || { echo "NOT BUILT: python3 is required for artifact verification." >&2; exit 4; }
command -v file >/dev/null 2>&1 || { echo "NOT BUILT: file is required to verify the launcher architecture." >&2; exit 4; }

BUILD="$ROOT/packaging/.build/linux-$ARCHITECTURE"
STAGE="$BUILD/app"
PACKAGE_ROOT="$BUILD/deb"
VERIFY_DEB="$BUILD/verify-deb"
VERIFY_TAR="$BUILD/verify-tar"
OUTPUT="$ROOT/dist/linux-$RELEASE_ARCH"
DEB_PATH="$OUTPUT/AutomationCenter-${VERSION}-linux-${RELEASE_ARCH}.deb"
TAR_PATH="$OUTPUT/AutomationCenter-${VERSION}-linux-${RELEASE_ARCH}.tar.gz"
rm -rf "$BUILD"
mkdir -p "$STAGE" "$PACKAGE_ROOT/DEBIAN" "$PACKAGE_ROOT/opt/automation-center" "$PACKAGE_ROOT/usr/bin" "$PACKAGE_ROOT/usr/share/applications" "$OUTPUT"
rm -f "$DEB_PATH" "$TAR_PATH"

tar -C "$ROOT" --exclude=.git --exclude=.env --exclude='.env.*' --exclude=dist --exclude=node_modules --exclude=output --exclude=postgres-data --exclude=.n8n --exclude=__pycache__ --exclude=.build --exclude=tests --exclude=test --exclude='*.log' --exclude='*.pem' --exclude='*.key' --exclude='*.p12' --exclude='*.pfx' --exclude='playwright/linkedin.json' --exclude='playwright/jobs.json' --exclude='playwright/jobs-history.json' -cf - . | tar -C "$STAGE" -xf -
pyinstaller --noconfirm --clean --onefile --name automation-center --distpath "$BUILD/launcher" --workpath "$BUILD/pyinstaller-work" --specpath "$BUILD" "$ROOT/packaging/common/service_manager.py"
cp "$BUILD/launcher/automation-center" "$STAGE/automation-center"
EXPECTED_ELF_ARCH=$( [ "$ARCHITECTURE" = amd64 ] && echo 'x86-64|x86_64' || echo 'aarch64|ARM aarch64' )
file "$STAGE/automation-center" | grep -Eq "$EXPECTED_ELF_ARCH"
python3 "$ROOT/packaging/common/scan_artifact.py" "$STAGE"

cp -a "$STAGE/." "$PACKAGE_ROOT/opt/automation-center/"
printf '%s\n' '#!/bin/sh' 'exec /opt/automation-center/automation-center "$@"' > "$PACKAGE_ROOT/usr/bin/automation-center"
chmod 0755 "$PACKAGE_ROOT/usr/bin/automation-center" "$PACKAGE_ROOT/opt/automation-center/automation-center"
printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Automation Center' 'Comment=Local automation workspace' 'Exec=automation-center start' 'Terminal=false' 'Categories=Utility;' > "$PACKAGE_ROOT/usr/share/applications/automation-center.desktop"
printf 'Package: automation-center\nVersion: %s\nSection: utils\nPriority: optional\nArchitecture: %s\nMaintainer: Automation Center\nDescription: Local Automation Center runtime\n' "$VERSION" "$ARCHITECTURE" > "$PACKAGE_ROOT/DEBIAN/control"

dpkg-deb --build "$PACKAGE_ROOT" "$DEB_PATH"
python3 "$ROOT/packaging/common/scan_artifact.py" "$DEB_PATH"
dpkg-deb --info "$DEB_PATH" | grep -q "Architecture: $ARCHITECTURE"
dpkg-deb --contents "$DEB_PATH" >/dev/null
rm -rf "$VERIFY_DEB" "$VERIFY_TAR"
dpkg-deb --extract "$DEB_PATH" "$VERIFY_DEB"
file "$VERIFY_DEB/opt/automation-center/automation-center" | grep -Eq "$EXPECTED_ELF_ARCH"
python3 "$ROOT/packaging/common/scan_artifact.py" "$VERIFY_DEB"
tar -C "$STAGE" -czf "$TAR_PATH" .
python3 "$ROOT/packaging/common/scan_artifact.py" "$TAR_PATH"
tar -C "$VERIFY_TAR" -xzf "$TAR_PATH" 2>/dev/null || { mkdir -p "$VERIFY_TAR"; tar -C "$VERIFY_TAR" -xzf "$TAR_PATH"; }
file "$VERIFY_TAR/automation-center" | grep -Eq "$EXPECTED_ELF_ARCH"
python3 "$ROOT/packaging/common/scan_artifact.py" "$VERIFY_TAR"
python3 "$ROOT/packaging/common/release_manifest.py" record --artifact "$DEB_PATH" --platform "linux-$RELEASE_ARCH" --architecture "$RELEASE_ARCH" --format deb
python3 "$ROOT/packaging/common/release_manifest.py" record --artifact "$TAR_PATH" --platform "linux-$RELEASE_ARCH" --architecture "$RELEASE_ARCH" --format tar.gz
python3 "$ROOT/packaging/common/release_manifest.py" verify
echo "PASS: Linux $ARCHITECTURE genuine artifacts written to $OUTPUT"
