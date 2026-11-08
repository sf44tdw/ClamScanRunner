#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 OUTPUT_DIRECTORY" >&2
    exit 2
fi

cd "$(dirname "$0")/.."
output_dir=$(mkdir -p "$1" && cd "$1" && pwd)
topdir=$(mktemp -d)
trap 'rm -rf "$topdir"' EXIT
mkdir -p "$topdir"/{BUILD,BUILDROOT,RPMS,SOURCES,SRPMS}
git show HEAD:clamscanrunner.spec > "$topdir/clamscanrunner.spec"
git show HEAD:tests/test_rpm_scriptlets.py > "$topdir/test_rpm_scriptlets.py"

read -r name version release arch < <(
    rpmspec -q --define 'dist %{nil}' \
        --qf '%{NAME} %{VERSION} %{RELEASE} %{ARCH}\n' "$topdir/clamscanrunner.spec"
)
if [ "$name" != clamscanrunner ] || [ "$arch" != noarch ]; then
    echo "Unexpected RPM name or architecture: $name $arch" >&2
    exit 1
fi

git archive --format=tar --prefix="$name-$version/" HEAD |
    gzip > "$topdir/SOURCES/$name-$version.tar.gz"
rpmbuild -bb --define "_topdir $topdir" --define 'dist %{nil}' \
    --define '_rpmfilename %{NAME}-%{VERSION}-%{RELEASE}.rpm' "$topdir/clamscanrunner.spec"

rpm_file="$topdir/RPMS/$name-$version-$release.rpm"
test -f "$rpm_file"
rpm_metadata=$(rpm -qp --qf '%{NAME} %{VERSION} %{RELEASE} %{ARCH}' "$rpm_file")
if [ "$rpm_metadata" != "$name $version $release noarch" ]; then
    echo "Unexpected RPM metadata: $rpm_metadata" >&2
    exit 1
fi
CLAMSCANRUNNER_RPM="$rpm_file" python3 "$topdir/test_rpm_scriptlets.py"
install -m 644 "$rpm_file" "$output_dir/"
