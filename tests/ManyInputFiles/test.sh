. ../common.sh

rm -rf __build
rm -rf src

mkdir src

rm -f hello.pake

for i in {1..50}; do
    echo "void func_$i() {}" > src/func_${i}.cpp
    echo "append \$sources src/func_${i}.cpp" >> hello.pake
done

echo "target application hello sources(main.cpp \$sources)" >> hello.pake

assert $pake hello
assert __build/__default/hello

rm -f hello.pake
rm -rf src
rm -rf __build

