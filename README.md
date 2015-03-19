## What is it?

Pake is just another C++ build system (currently, C files will go through C++ compiler) with kind of different philosophy than otherts. The main difference is that pake's script does not allow any logic, it means, you can not make conditions, loops, etc, you just declare what shuold happen in given target and/or configuration and for any other stuff, regular script language can be used (eg. python or bash).

## How to get it?

Because pake is a alpha quality software, the only official way of distributing it is to "build" it using waffle and put in inside your project repository. To simplyfy this, there is a shell script called `make_pake.sh` which generates `__build/pake.py` file which you can directly put and use in your project.

## More documentation

See [wiki pages for documentation](https://github.com/podusowski/pake/wiki)

