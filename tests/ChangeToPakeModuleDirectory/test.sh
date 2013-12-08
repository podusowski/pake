. ../common.sh

rm -rf _build

assert $pake Hello
assert $pake HelloLibrary

assert _build/Hello

rm -rf _build

