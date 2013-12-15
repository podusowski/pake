. ../common.sh

rm -rf _build

    mkdir -p _build

    assert $pake Test
    assert _build/Test

    big_echo "touch and rebuild"
    touch _build/generated_1.hpp
    assert $pake Test

    assert $pake Test2
    assert test -f _build/Test2

    # it's artefact is Test2 so it shouldnt be rebuilt
    assert $pake Test4
    assert_fail test -f _build/Test4
    touch Test.pake
    assert $pake Test4
    assert test -f _build/Test4


    assert $pake Test3
    assert test -f _build/Test3

rm -rf _build
