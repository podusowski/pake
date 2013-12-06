pake=`dirname $BASH_SOURCE`/../pake.py

function error()
{
    echo "----------------------------------------------------------------------"
    echo "error in cmd: $@"
    echo "----------------------------------------------------------------------"
    exit 1
}

function assert()
{
    echo running: $@
    $@ || error $@
}

function assert_fail()
{
    echo running: $@
    $@ && error $@
}

function big_echo()
{
    echo
    echo "----------------------------------------------------------------------"
    echo $@
    echo "----------------------------------------------------------------------"
    echo
}

export DEBUG=1

