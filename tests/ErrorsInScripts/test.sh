. ../common.sh

rm -rf __build
mkdir __build

for i in *.pake; do
    name=`echo $i | sed 's/.pake//'`
    mkdir -p __build/$name
    cp $i __build/$name/
    pushd __build/$name/ > /dev/null
        assert_fail $pake hello
    popd > /dev/null
done

rm -rf __build
