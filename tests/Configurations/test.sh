. ../common.sh

rm -rf _build

assert $pake -c fake hello
assert test -f _build/fake

rm -rf _build

