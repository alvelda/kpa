#!/usr/bin/env bash
# Normalize protodump.py output filenames to the underscored convention used
# by keynote-parser's bundled schemas (14.4 baseline).
#
#   Foo.sos.proto       -> Foo_sos.proto
#   TSCHArchives.Common -> TSCHArchives_Common
#   TSCHArchives.GEN    -> TSCHArchives_GEN
#
# Also rewrites `import "Foo.sos.proto";` -> `import "Foo_sos.proto";` inside
# every .proto so the resulting tree compiles cleanly with protoc.
#
# Usage:
#   normalize_schema_filenames.sh <raw_dir> <normalized_dir>

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <raw_dir> <normalized_dir>" >&2
    exit 64
fi

RAW_DIR="$1"
NORM_DIR="$2"

mkdir -p "$NORM_DIR"

for f in "$RAW_DIR"/*.proto; do
    bn=$(basename "$f")
    newname=$(echo "$bn" \
        | sed 's/\.sos\.proto$/_sos.proto/; s/\.Common\.proto$/_Common.proto/; s/\.GEN\.proto$/_GEN.proto/')
    cp "$f" "$NORM_DIR/$newname"
done

cd "$NORM_DIR"
for f in *.proto; do
    # macOS sed -i needs a backup-extension arg
    sed -i.bak -E '
        s|import "([A-Z][A-Za-z0-9]*Archives)\.sos\.proto";|import "\1_sos.proto";|g
        s|import "TSCHArchives\.Common\.proto";|import "TSCHArchives_Common.proto";|g
        s|import "TSCHArchives\.GEN\.proto";|import "TSCHArchives_GEN.proto";|g
        s|import "TSACommandArchives\.sos\.proto";|import "TSACommandArchives_sos.proto";|g
    ' "$f"
done
rm -f *.bak

echo "normalized $(ls -1 "$NORM_DIR"/*.proto | wc -l | tr -d ' ') .proto files into $NORM_DIR"
