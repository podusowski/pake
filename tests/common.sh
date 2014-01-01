pake_dir=`dirname $BASH_SOURCE`/..
pake=`readlink -f $pake_dir`/pake.py

reset="\033[0m"
bg1="\033[44;37m"
bg2="\033[40;37m"

function error()
{
    echo "----------------------------------------------------------------------"
    echo "error in cmd: $@"
    echo "----------------------------------------------------------------------"
    exit 1
}

function assert()
{
    echo -e "${bg1}Test:${reset} running $@"
    $@ || error $@
}

function assert_fail()
{
    echo -e "${bg1}Test:${reset} running $@"
    $@ && error assert_fail $@
}

function big_echo()
{
    echo -e "${bg1}Test:${reset} $@"
}

#export DEBUG=1

