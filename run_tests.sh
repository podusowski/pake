for i in tests/*; do
    if [ -d $i ]; then
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
    fi
done
