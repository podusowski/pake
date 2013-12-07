pake (early alpha)
====
Friendly C++ build system which doesn't follow trends.


## Motivation
Pake is trying to address lack of good alternative for plain make when it comes to C++ development. Although there is a cmake, qmake and bunch of other projects, either provided painless project management so I decided to give a shot in implementing my own vision of how build system should be usable.

Unlike other popular C++ build system CMake, pake is not a build system generator. Instead it just compiles your stuff requiring from you as less as it can.


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


## Targets

Unlike make, where you're responsible to deliver means to build the artefact, pake has several, dedicated target types and uses it's own understanding of toolchain to provide deliverables.

Each target type might call external script, to do that, you can use either `run_before` or `run_after` parameter. See the example.

```
target type phony tests run_before(./run_tests.sh)
```

### Application
The most common target which you can use. It builds complete C++ application from sources or libraries.

#### Example

```
target application sources(main.cpp utils.cpp)
```

### Static library
Static library is just packed object files which can be later used by other targets.


### Phony
This target does nothing when it comes to pake's compiler support. It can be used to group other targets or perform build using external techniques.

## Variables

Obviously variables are things where you can store stuff, for example list of files to compile. Variables can be manipulated by `set` and `append` directives. Name of the variable must always start with `$`, the reason for that is that in pake, simple literals (like `some_file.cpp`) are not surrounded by quotation marks and pake needs to distinguish one another.

## Modules

Pake tree consists of so called modules, those are simply `.pake` files somewhere in your project sources. You don't have to include anything, the idea is that pake walks through all directories looking for the modules. There is no limitation on how many targets are inside the module. Each variable has it's module origin, so although you can create as many variables you want, their names can't duplicate across one module (they can however in many different modules).

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
 * Minimal tree pollution (single `_build` directory with the results)
 * Easy project integration - just put `pake.py` inside your tree and write `.pake` files
 * No "include"-mess. Pake walks trough your tree and find .pake files to be used in your project
 * Shared variables. You can easily read variable from other module
 * No new language to learn, if you want some logic, you write a shell script
 * Very simple syntax. Only 3 directives: `target`, `set` and `append`
 * No "build system generation", pake is just building your software


## Drawbacks

 * pake is not a programming language and never will be, to do advanced things like finding the package you should use normal language such as bash or python.
 * Finding `.pake` files is a big feature but it might also be some pain in the ass when used in large projects


## Planned features

 * Toolchain configuration
 * Parallel builds

