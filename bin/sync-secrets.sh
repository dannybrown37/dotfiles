#!/usr/bin/bash

##
## This reads secret files from pass
## Reads local secret files
## Sorts lines (except for top-level directives)
## Removes duplicates
## Writes synced secrets both locally and to password-store
##

sync-secrets() {
    local ahk_secrets_from_pass=$(pass ahk/secrets)
    local bash_secrets_from_pass=$(pass bash/secrets)

    local ahk_secrets_from_repo=$(cat "${DOTFILES_DIR}/ahk/secrets.ahk")
    local bash_secrets_from_repo=$(cat "${DOTFILES_DIR}/config/.secrets")

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

    echo "$merged_ahk_secrets" > "${DOTFILES_DIR}/ahk/secrets.ahk"
    echo "$merged_bash_secrets" > "${DOTFILES_DIR}/config/.secrets"

    pass insert -m ahk/secrets < "${DOTFILES_DIR}/ahk/secrets.ahk"
    pass insert -m bash/secrets < "${DOTFILES_DIR}/config/.secrets"
}
