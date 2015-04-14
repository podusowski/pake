. ../common.sh

rm -rf __build
mkdir -p __build

pushd __build

    echo "// nothing" > test.cpp

    echo 'configuration __default compiler("${test.__path}/../c++-wrapper.sh")' > test.pake
    echo 'target static_library test sources(test.cpp)' >> test.pake

    assert $pake test

    absolute_path_to_cpp=`pwd`/test.cpp

    calls:
    cat calls.list

    assert grep $absolute_path_to_cpp calls.list 2> /dev/null

popd

rm -rf __build
