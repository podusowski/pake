mkdir -p $build_directory

echo "generating stuff, stand by"

for i in {1..10000}; do
    echo "#pragma once" > $build_directory/generated_$i.hpp
    echo "#include \"_build/generated_$i.hpp\"" >> $build_directory/generated.cpp
done

