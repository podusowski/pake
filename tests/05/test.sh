. ../common.sh

rm -rf __build

assert $pake Test
assert test -f __build/__default/Test

rm -rf __build
