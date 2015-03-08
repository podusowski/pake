root=`pwd`
mkdir -p __build
pushd scripts
./waffle_maker.py -o $root/__build/pake.py -p $root/src/ -s $root/src/pake.py
popd
