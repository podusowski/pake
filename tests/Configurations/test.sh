. ../common.sh

rm -rf __build

assert $pake hello_default
assert test -f __build/__default/hello_default

assert $pake -c fake hello
assert test -f __build/fake/fake

assert $pake -c linux hello_linux
assert test -f __build/linux/hello_linux

assert $pake -c windows hello_windows
assert test -f __build/windows/hello_windows.exe

rm -rf __build

