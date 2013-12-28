. ../common.sh

rm -rf __build
mkdir -p __build

assert $pake hello
assert test -f __build/__default/hello

rm -rf __build

