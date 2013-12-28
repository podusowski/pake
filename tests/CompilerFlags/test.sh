. ../common.sh

rm -rf __build

assert $pake hello
assert __build/__default/hello

rm -rf __build

