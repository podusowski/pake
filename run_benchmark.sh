set -e

working_directory=__benchmark
project_sources=src
pake=`pwd`/src/pake.py
report_file=report.txt

function make_header_filename()
{
    local index=$1
    local level=$2

    echo -n "$project_sources/header_level${level}_${index}.hpp"
}

function generate_headers()
{
    local index=$1
    local level=$2

    local last_file=`make_header_filename $index $level`

    echo "#include <string>" > $last_file

    local filename=""

    for i in `seq 1 $(($level - 1))`; do
        local include_file=`make_header_filename $index $(($i + 1))`
        filename=`make_header_filename $index $i`

        echo "#include \"$include_file\"" > $filename
    done

    echo $filename
}

function generate_compilation_units()
{
    local size=$1
    local level=$2

    for i in `seq $size`; do
        local header=`generate_headers $i $level`
        local filename="$project_sources/compilation_unit_${i}.cpp"
        echo "#include \"$header\"" > $filename
        echo $filename
    done

    local main_filename=$project_sources/main.cpp
    echo "int main() {}" > $main_filename
    echo $main_filename
}

function perform_tests()
{
    local compilation_unit_size=1
    local header_include_level=2

    generate_compilation_units $compilation_unit_size $header_include_level > compilation_units.list

    test_pake
    test_cmake

    cat $report_file
}

function report()
{
    tee --append $report_file
}

function measure_time()
{
    /usr/bin/time --format "%E" --output=time.out $@

    echo "`cat time.out` $@" | tee --append $report_file
}

function test_buildsystem()
{
    local build_command=$@

    local line="-----------------------------------------------------------------------------"

    echo $line | report

    echo -n "clean build:         " | report
    measure_time $build_command

    echo -n "nothing to be done:  " | report
    measure_time $build_command

    echo $line | report
    echo | report
}

function test_pake()
{
    local pake_module=build.pake

    echo -n > $pake_module

    cat compilation_units.list | while read unit; do
        echo "append \$sources $unit" >> $pake_module
    done

    echo "target application build_by_pake sources(\$sources) include_dirs(.)" >> $pake_module

    PYTHONDONTWRITEBYTECODE=1 test_buildsystem $pake -a -j1
}

function test_cmake()
{
    local cmake_module=CMakeLists.txt

    echo -n > $cmake_module

    echo 'cmake_minimum_required(VERSION 2.6)' >> $cmake_module
    echo 'project(Benchmark)' >> $cmake_module
    echo 'include_directories("${PROJECT_SOURCE_DIR}")' >> $cmake_module
    echo "add_executable(Benchmark `cat compilation_units.list`)" >> $cmake_module

    cmake .

    test_buildsystem make -j1
}

function main()
{
    rm -rf $working_directory
    mkdir -p $working_directory/$project_sources
    pushd $working_directory
    perform_tests
    popd
}

main
