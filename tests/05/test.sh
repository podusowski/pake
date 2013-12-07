. ../common.sh

rm -rf _build

assert $pake Test
assert test -f _build/Test

rm -rf _build
