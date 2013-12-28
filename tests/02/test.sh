. ../common.sh

rm -rf __build

big_echo "invalid c++ code"
assert_fail $pake Failed

rm -rf __build

