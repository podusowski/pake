. ../common.sh

rm -rf _build


    big_echo "complicated app"

    mkdir -p _build

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
