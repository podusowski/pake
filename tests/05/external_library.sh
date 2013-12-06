mkdir -p _build/external_library
c++ -c -o _build/external_library/external_library.o external_library.cpp
ar -rcs _build/external_library/external_library.a _build/external_library/external_library.o
