. ../common.sh
rm -rf __build

assert $pake hello
assert __build/__default/hello
assert test -f __build/__default/hello.txt
assert __build/__default/hello.sh

assert $pake hi
assert test -f __build/__default/hi.txt

rm -rf __build

