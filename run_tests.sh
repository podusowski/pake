./build.sh

. tests/common.sh

for i in tests/*; do
    if [ -d $i ]; then

        echo -e "${bg1}  running test $i  ${reset}"

        pushd $i > /dev/null
        if ./test.sh ; then
            echo -e "${bg1}  test passed  ${reset}"
        else
            echo -e "${bg1}  test failed  ${reset}"
            exit 1
        fi
        popd > /dev/null
        echo
        echo
    fi
done
