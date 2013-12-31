. ../common.sh
rm -rf __build

assert_fail $pake -c nooooo hi

rm -rf __build
