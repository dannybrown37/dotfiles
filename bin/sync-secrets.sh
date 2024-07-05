#!/usr/bin/bash

##
## This reads secret files from pass
## Reads local secret files
## Sorts lines (except for top-level directives)
## Removes duplicates
## Writes synced secrets both locally and to password-store
## Assumes secrets are one line, backed up for recreated
##

sync-secrets() {
    local ahk_secrets_from_pass=$(pass ahk/secrets)
    local bash_secrets_from_pass=$(pass bash/secrets)

    local ahk_secrets_file="${DOTFILES_DIR}/ahk/secrets.ahk"
    local bash_secrets_file="${DOTFILES_DIR}/config/.secrets"

    local ahk_secrets_from_repo=$(cat "$ahk_secrets_file")
    local bash_secrets_from_repo=$(cat "$bash_secrets_file")

        mv "$ahk_secrets_file" "$ahk_secrets_file.bak"
    mv "$bash_secrets_file" "$bash_secrets_file.bak"

    local merged_ahk_secrets=$(
        echo -e "$ahk_secrets_from_pass\n$ahk_secrets_from_repo" \
        | sort \
        | uniq)
    merged_ahk_secrets=$(
        echo -e "#SingleInstance Force\n$merged_ahk_secrets" \
        | awk '!seen[$0]++')


    local merged_bash_secrets=$(
        echo -e "$bash_secrets_from_pass\n$bash_secrets_from_repo" \
        | sort \
        | uniq)
    merged_bash_secrets=$(
        echo -e "#!/usr/bin/bash\n$merged_bash_secrets" \
        | awk '!seen[$0]++')

    echo "$merged_ahk_secrets" > "$ahk_secrets_file"
    echo "$merged_bash_secrets" > "$bash_secrets_file"

    pass insert -m ahk/secrets <  "$ahk_secrets_file"
    pass insert -m bash/secrets < "$bash_secrets_file"
}
