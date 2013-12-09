mkdir -p _build

for i in {1..10000}; do
    echo "#pragma once" > _build/generated_$i.hpp
    echo "#include \"_build/generated_$i.hpp\"" >> _build/generated.cpp
done

