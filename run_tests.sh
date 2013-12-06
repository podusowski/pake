pake=`pwd`/pake.py

function error()
{
    echo "----------------------------------------------------------------------"
    echo "error in cmd: $@"
    echo "----------------------------------------------------------------------"
    exit 1
}

function assert()
{
    echo running: $@
    $@ || error $@
}

function assert_fail()
{
    echo running: $@
    $@ && error $@
}

function big_echo()
{
    echo
    echo "----------------------------------------------------------------------"
    echo $@
    echo "----------------------------------------------------------------------"
    echo
}

export DEBUG=1

pushd tests/01
    rm -rf _build

    big_echo "some normal build"
    for i in {1..2}; do
        assert $pake Test$i
        assert _build/Test$i
    done

    big_echo "no rebuild"
    assert $pake Test1

    rm -rf _build
popd

pushd tests/02
    rm -rf _build

    big_echo "invalid c++ code"
    assert_fail $pake Failed

    rm -rf _build
popd

pushd tests/03
    rm -rf _build
    mkdir -p _build

    big_echo "complicated app"

    for i in {1..10000}; do
        echo "#pragma once" > _build/generated_$i.hpp
        echo "#include \"_build/generated_$i.hpp\"" >> _build/generated.cpp
    done

    assert $pake Test
    assert _build/Test

    big_echo "touch and rebuild"
    touch _build/generated_1.hpp
    assert $pake Test

    rm -rf _build
popd

pushd tests/04
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
popd

big_echo "it works, yeah!"
