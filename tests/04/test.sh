. ../common.sh
rm -rf _build

    big_echo "static libraries"

    #assert $pake Library
    assert $pake Test
    assert _build/Test

    big_echo "lib has changed, app needs to be rebuilt"

    touch lib.cpp

    # TODO: dumbass test operates on seconds
    sleep 2

    assert $pake Test

    # our app needs to be newer than touched lib.cpp
    assert test _build/Test -nt lib.cpp

    big_echo "nothing has changed"

    sleep 2
    touch _build/now
    sleep 2

    assert $pake Test

    echo
    for i in _build/*; do
        echo $i: `stat $i | grep Modify`
    done
    echo

    assert test _build/Test -nt lib.cpp
    assert test _build/Test -ot _build/now

    # check run_after
    assert $pake Phony

    assert test -f _build/bash

rm -rf _build

