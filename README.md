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

## Modules and variables

Pake tree consists of so called modules, those are simply .pake files somewhere in your project sources. You don't have to include anything, the idea is that pake walks through all directories looking for the modules. There is no limitation on how many targets are inside the module. Each variable has it's module origin, so although you can create as many variables you want, their names can't duplicate across one module (they can however in many different modules).

The neat thing is that you can read variable defined in other module, see the example how to do that.

### Example

```
# A.pake
set $sources a.cpp
target application sources($sources)
```

```
# B.pake
set $sources b.cpp
target application sources($sources $A.sources)
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

