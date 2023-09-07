#! /bin/bash/


# Copy a file from WSL-Linux to Windows downloads folder with tab auto-completion


# Completion function to autocomplete folders from cwd
_complete() {

  _complete_cpw() {
    local cur opts
    cur=${COMP_WORDS[COMP_CWORD]}
    opts=$(compgen -f $cur)
    COMPREPLY=( $(compgen -W "${opts[*]}" -- $cur) )
  }

  complete -F _complete_cpw cpw
}

# Register completion
_complete

# Main function to copy files from WSL to Windows
cpw() {

  windows_prefix="/mnt/c/Users/$WINDOWS_USERNAME"
  windows_path="$windows_prefix/Downloads"

  if [ $# -ne 1 ] && [ $# -ne 2 ]; then
    echo "Usage: ${0} <file_to_copy> [path_to_copy]"
    return
  fi

  source=$1
  dest=$2

  if [ ! -z $dest ]; then
    windows_path="$windows_prefix/$dest"
  fi

  cp "$source" "$windows_path/$source"

}
