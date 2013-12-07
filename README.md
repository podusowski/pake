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

### Variable sharing

```
# external_library.pake
set $library_dir _build/external_library/
target phony external_library run_before(./do_some_cmake_build_or_something.sh)
```
```
# Sample.pake
target application Sample sources(main.cpp) library_dir($external_library.library_dir) link_with(external_library)
```

## Language elements

```
target phony [ run_before(SCRIPT) ] [ run_after(SCRIPT) ]
target application [ run_before(SCRIPT) ] [ run_after(SCRIPT) ] [ sources(LIST) ] [ link_with(LIST) ] [ library_dir(LIST) ]
target static_library [ run_before(SCRIPT) ] [ run_after(SCRIPT) ] [ sources(LIST) ]
[ set | append ] VARIABLE_NAME VALUE
```

## Features

 * C++ header dependency resolver
 * Minimal tree polution (single `_build` directory with the results)
 * Easy project integration - just put `pake.py` inside your tree and write `.pake` files
 * No "include"-mess. Pake walks trough your tree and find .pake files to be used in your project
 * Shared variables. You can easily read variable from other module
 * No new language to learn, if you want some logic, you write a shell script
 * Very simple syntax. Only 3 directives: `target`, `set` and `append`
 * No "build system generation", pake is just building your software

## Planned features

 * Toolchain configuration
 * Parallel builds

