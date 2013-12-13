. ../common.sh

rm -rf _build
mkdir _build

for i in *.pake; do
    name=`echo $i | sed 's/.pake//'`
    mkdir -p _build/$name
    cp $i _build/$name/
    pushd _build/$name/ > /dev/null
        assert_fail $pake hello
    popd > /dev/null
done

rm -rf _build
