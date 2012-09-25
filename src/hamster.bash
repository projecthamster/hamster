# bash completion for hamster
# TODO - merge hamster-cli into hamster-time-tracker and then both into "hamster"

_hamster_helper()
{
    local IFS=$'\n'
    COMPREPLY+=( $(
        hamster-cli "$@" 2>/dev/null ) )
}

_hamster()
{
    local cur prev opts base
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    #
    #  The basic options we'll complete.
    #
    opts="start stop list export" #  TODO - overview statistics edit preferences about


    #
    #  Complete the arguments to some of the basic commands.
    #
    case "${prev}" in

    start)
        _hamster_helper "assist" "$prev" "$cur"
        return 0
        ;;

    esac

   COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
   return 0
}
complete -F _hamster hamster-cli
