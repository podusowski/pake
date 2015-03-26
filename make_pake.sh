root=`pwd`
mkdir -p __build
pushd scripts
./waffle_maker.py -o $root/__build/pake.py -p $root/src/ -s $root/src/pake.py
(echo "#!/usr/bin/env python2"; tail -n +2 "$root/__build/pake.py") > new_pake
mv new_pake $root/__build/pake.py
chmod +x $root/__build/pake.py
popd
