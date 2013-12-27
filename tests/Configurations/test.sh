. ../common.sh

rm -rf _build

assert $pake -c fake hello
assert test -f _build/fake

assert $pake -c windows-mingw hello
assert test -f _build/hello.exe

rm -rf _build

