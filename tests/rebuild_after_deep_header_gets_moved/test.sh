. ../common.sh

rm -rf __build
mkdir -p __build

pushd __build

    echo "// nothing" > deeper_header.hpp
    echo -e "#include \"deeper_header.hpp\"" > header.hpp
    echo -e "#include \"header.hpp\"\nint main() {}" > test.cpp
    echo "target application test sources(test.cpp)" > test.pake

    assert $pake test
    assert __build/__default/test

    echo -e "#include \"new_deeper_header.hpp\"" > header.hpp
    mv deeper_header.hpp new_deeper_header.hpp

    assert $pake test

popd

rm -rf __build

