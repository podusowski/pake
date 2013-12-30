. ../common.sh

rm -rf __build

rm __build/calls.list
assert $pake hello
assert grep -e -c.*main.cpp __build/calls.list
assert grep -e -c.*foo __build/calls.list
assert grep -e -o.*hello __build/calls.list
assert __build/__default/hello

rm __build/calls.list
assert $pake hello
assert_fail grep -e -c.*main.cpp __build/calls.list
assert_fail grep -e -c.*foo __build/calls.list
assert_fail grep -e -o.*hello __build/calls.list

rm __build/calls.list
assert touch main.cpp
assert $pake hello
assert grep -e -c.*main.cpp __build/calls.list
assert_fail grep -e -c.*foo __build/calls.list
assert grep -e -o.*hello __build/calls.list
assert __build/__default/hello

rm __build/calls.list
assert touch utils.hpp
assert $pake hello
assert grep -e -c.*main.cpp __build/calls.list
assert_fail grep -e -c.*foo __build/calls.list
assert grep -e -o.*hello __build/calls.list
assert __build/__default/hello

rm __build/calls.list
assert touch foo.cpp
assert $pake hello
assert_fail grep -e -c.*main.cpp __build/calls.list
assert grep -e -c.*foo __build/calls.list
assert grep -e -o.*hello __build/calls.list
assert __build/__default/hello

rm __build/calls.list
assert touch foo.hpp
assert $pake hello
assert grep -e -c.*main.cpp __build/calls.list
assert grep -e -c.*foo __build/calls.list
assert grep -e -o.*hello __build/calls.list
assert __build/__default/hello

rm -rf __build

