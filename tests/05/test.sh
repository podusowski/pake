. ../common.sh

rm -rf _build

assert $pake Test
assert test -f Test

rm -rf _build
