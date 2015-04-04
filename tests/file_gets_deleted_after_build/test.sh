. ../common.sh

rm -rf __build
mkdir -p __build

pushd __build

    echo "// nothing" > header.hpp
    echo -e "#include \"header.hpp\"\nint main() {}" > test.cpp
    echo "target application test sources(test.cpp)" > test.pake

    assert $pake test
    assert __build/__default/test

    echo "int main() {}" > test.cpp
    rm header.hpp

    assert $pake test
    assert __build/__default/test

popd

rm -rf __build

