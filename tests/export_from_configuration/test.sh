. ../common.sh

rm -rf __build

assert $pake hello
assert test -f __build/__default/hello

assert $pake hello -c my_configuration
assert test -f __build/my_configuration/hello

rm -rf __build
