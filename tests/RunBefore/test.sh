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

    assert $pake Test3
    assert test -f _build/Test3

rm -rf _build
