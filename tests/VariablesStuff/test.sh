. ../common.sh
rm -rf __build

    mkdir -p __build
    assert $pake hello
    assert test -f __build/__default/test1
    assert test -f __build/__default/test2
    assert test -f __build/__default/test3
    assert test -f __build/__default/test10

rm -rf __build
