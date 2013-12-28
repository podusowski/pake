. ../common.sh

rm -rf __build

    mkdir -p __build

    assert $pake Test
    assert __build/__default/Test

    big_echo "touch and rebuild"
    touch __build/__default/generated_1.hpp
    assert $pake Test

    assert $pake Test2
    assert test -f __build/__default/Test2

    # it's artefact is Test2 so it shouldnt be rebuilt
    assert $pake Test4
    assert_fail test -f __build/__default/Test4
    touch Test.pake
    assert $pake Test4
    assert test -f __build/__default/Test4


    assert $pake Test3
    assert test -f __build/__default/Test3

rm -rf __build
