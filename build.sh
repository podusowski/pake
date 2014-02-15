root=`pwd`
pushd scripts
./waffle_maker.py -o $root/pake.py -p $root/src/ -s $root/src/main.py
popd
