mkdir -p __build/external_library
c++ -c -o __build/external_library/external_library.o external_library.cpp
ar -rcs __build/external_library/libexternal_library.a __build/external_library/external_library.o
