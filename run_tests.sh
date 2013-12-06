for i in tests/*; do
    pushd $i
    ./test.sh
    popd
    echo
    echo
done
