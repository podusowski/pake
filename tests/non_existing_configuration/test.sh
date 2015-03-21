. ../common.sh
rm -rf __build

assert_fail $pake -c non_existing_configuration hi

rm -rf __build
