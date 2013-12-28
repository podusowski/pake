. ../common.sh
rm -rf __build

    big_echo "static libraries"

    #assert $pake Library
    assert $pake Test
    assert __build/__default/Test

    big_echo "lib has changed, app needs to be rebuilt"

    touch lib.cpp

    # TODO: dumbass test operates on seconds
    sleep 2

    assert $pake Test

    # our app needs to be newer than touched lib.cpp
    assert test __build/__default/Test -nt lib.cpp

    big_echo "nothing has changed"

    sleep 2
    touch __build/__default/now
    sleep 2

    assert $pake Test

    echo
    for i in __build/__default/*; do
        echo $i: `stat $i | grep Modify`
    done
    echo

    assert test __build/__default/Test -nt lib.cpp
    assert test __build/__default/Test -ot __build/__default/now

    # check run_after
    assert $pake Phony

    assert test -f __build/__default/bash

rm -rf __build

