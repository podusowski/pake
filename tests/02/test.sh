. ../common.sh

rm -rf _build

big_echo "invalid c++ code"
assert_fail $pake Failed

rm -rf _build

