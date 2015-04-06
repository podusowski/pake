pake_dir=`dirname $BASH_SOURCE`/..
pake=`readlink -f $pake_dir`/__build/pake.py

reset="\033[0m"
bg1="\033[44;37m"
bg2="\033[40;37m"

header="\033[1;49;34m"
passed="\033[7;49;32m"
failed="\033[7;49;31m"
debug="\033[0;49;90m"

function error()
{
    echo "----------------------------------------------------------------------"
    echo "error in cmd: $@"
    echo "----------------------------------------------------------------------"
    exit 1
}

function assert()
{
    echo -e "${debug}expecting to succeed: $@${reset}"
    $@ || error $@
}

function assert_fail()
{
    echo -e "${debug}expecting to fail: $@${reset}"
    $@ && error assert_fail $@
}

function big_echo()
{
    echo -e "${debug}${@}${reset}"
}

#export DEBUG=1

