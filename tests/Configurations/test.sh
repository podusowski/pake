. ../common.sh

rm -rf __build

assert $pake hello_default
assert test -f __build/__default/hello_default

assert $pake -c fake hello
assert test -f __build/fake/fake

assert $pake -c fake hello_library
assert test -f __build/fake/fake_archive

assert $pake -c linux hello_linux
assert test -f __build/linux/hello_linux
assert test -f __build/linux/linux # $__configuration.__name

rm -rf __build

