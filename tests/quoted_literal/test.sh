. ../common.sh

rm -rf __build

assert $pake Test$i
assert __build/__default/Test$i

rm -rf __build

