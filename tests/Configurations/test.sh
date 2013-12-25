. ../common.sh

rm -rf _build

assert $pake hello
assert _build/hello

rm -rf _build

