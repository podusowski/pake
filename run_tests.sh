for i in tests/*; do
    pushd $i
    if ./test.sh ; then
        echo pass
    else
        echo fail
        exit 1
    fi
    popd
    echo
    echo
done
