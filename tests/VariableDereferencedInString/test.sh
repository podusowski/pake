. ../common.sh

rm -rf _build
mkdir -p _build

assert $pake hello
assert test -f _build/hello

rm -rf _build

