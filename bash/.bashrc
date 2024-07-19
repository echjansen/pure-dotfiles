#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

PS1='[\u@\h \W]\$ '

# Fonts
# setfont ter-v22b

# Aliases
alias ls='LC_COLLATE=C ls -hla --group-directories-first --color=auto'
alias grep='grep --color=auto'
alias mg='mg -n'

# Exports
export PATH=~/.local/bin:$PATH
export EDITOR='emacs -nw'
export VISUAL=$EDITOR
export TERMINAL=foot

# GPG with OnlyKey (instead of YubiKey)
# export GNUPGHOME=$HOME/.gnupg/onlykey

# GPG for SSH Authentication
unset SSH_AGENT_PID
if [ "${gnupg_SSH_AUTH_SOCK_by:-0}" -ne $$ ]; then
  export SSH_AUTH_SOCK="$(gpgconf --list-dirs agent-ssh-socket)"
fi
