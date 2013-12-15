. ../common.sh
rm -rf _build

    mkdir -p _build
    assert $pake hello
    assert test -f _build/test1
    assert test -f _build/test2
    assert test -f _build/test3
    assert test -f _build/test10

rm -rf _build
