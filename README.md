pake (early alpha)
====
Friendly C++ build system which doesn't follow trends.

## Motivation
Pake is trying to address lack of good alternative for plain make when it comes to C++ development. Although there is a cmake, qmake and bunch of other projects, either provided painless project management so I decided to give a shot in implementing my own vision of how build system should be usable.

Unline other popular C++ build system such as CMake, pake is not build system generator. Instead it just tries to minimize your effort as much as it can and it just compiles your code.

## Examples

### The simplest sctipt you can get
```
target application Test1 sources(Test.cpp)
```

### Static library example

```
target static_library Library sources(lib.cpp)
target application Test sources(main.cpp) link_with(Library) depends_on(Library)
```

## Features

 * C++ header dependency resolver
 * Minimal tree polution (single `_build` directory with the results)
 * Easy project integration - just put `pake.py` inside your tree and write `.pake` files
 * No "include"-mess. Pake walks trough your tree and find .pake files to be used in your project
 * No new language to learn, if you want some logic, you write a shell script

## Planned features

 * Toolchain configuration
 * Parallel builds
