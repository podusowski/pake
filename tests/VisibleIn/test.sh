. ../common.sh
rm -rf __build

assert $pake -c linux-debug hello hello_ut
assert test -f __build/linux-debug/hello
assert test -f __build/linux-debug/hello_ut

rm -rf __build

assert $pake -c linux-release hello
assert_fail $pake -c linux-release hello_ut
assert test -f __build/linux-release/hello
assert_fail test -f __build/linux-release/hello_ut

rm -rf __build

assert $pake -a -c linux-release
assert test -f __build/linux-release/hello
assert_fail test -f __build/linux-release/hello_ut

rm -rf __build
