. ../common.sh

rm -rf _build

assert $pake -c fake hello
assert test -f _build/fake

assert $pake -c linux hello_linux
assert test -f _build/hello_linux

assert $pake -c windows hello_windows
assert test -f _build/hello_windows.exe

rm -rf _build

