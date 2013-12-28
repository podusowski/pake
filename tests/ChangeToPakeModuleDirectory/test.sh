. ../common.sh

rm -rf __build

assert $pake Hello
assert $pake HelloLibrary

assert __build/__default/Hello

rm -rf __build

