. ../common.sh

rm -rf _build

big_echo "some normal build"
for i in {1..2}; do
    assert $pake Test$i
    assert _build/Test$i
done

big_echo "everything is up to date so no rebuild"
assert $pake Test1

rm -rf _build

