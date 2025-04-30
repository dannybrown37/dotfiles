#SingleInstance Force
#NoEnv ; Recommended for performance and compatibility with future AutoHotkey releases.
#Warn ; Enable warnings to assist with detecting common errors.
#Persistent
SetTitleMatchMode, 2  ;

SendMode Input ; Recommended for new scripts due to its superior speed and reliability.


; Load aliases into a dictionary on script startup
aliases := {} ; Dictionary to hold alias-name => alias-command pairs
LoadAliases()

; LoadAliases function definition
LoadAliases()
{
    global aliases
    ; Run the alias command inside wsl.exe and capture the output
    RunWait, wsl.exe bash -l -i -c "alias > /tmp/aliases.txt", , Hide
    wslFilePath := "\\wsl$\Debian\tmp\aliases.txt"  ; Update this if needed based on your WSL distro
    FileRead, OutputVar, %wslFilePath%
    ; Split the output into lines and parse each alias
    Loop, Parse, OutputVar, `n
    {
        line := A_LoopField
        if (RegExMatch(line, "^alias\s+([^=]+)=['""](.*)['""]$", m))
        {
            aliases[m1] := m2  ; Automatically strips the quotes
        }
        else if (RegExMatch(line, "^alias\s+([^=]+)=(.*)$", m))
        {
            aliases[m1] := m2  ; Handles unquoted values
        }
    }
}

; triple-commas will disappear to trigger a search of aliases, enter with space
:*:,,,::
{
    Input, userInput, V T5, %A_Space%  ; Wait for space after `,,,<alias>`
    aliasName := Trim(userInput)

    if (!aliases.HasKey(aliasName))
        return  ; Do nothing if alias not found

    aliasValue := aliases[aliasName]

    ; Replace `,,,<alias>` with alias value
    Loop, % StrLen(",,,") + StrLen(aliasName)
        Send, {BS}

    Send, %aliasValue%
    return
}


; Commands that don't need to be expanded to run should be
; defined as Bash aliases in config/.bash_aliases. We can
; expand them with a triple-comma, but it's not necessary
; for usage in the CLI.

; Commands that are not intended to be run in the CLI, such
; as code snippets or partial commands that need to be
; adjusted before they are run, should be defined in this
; file.


; LLM tools
::,,llm::For future responses in this chat, never apologize. Don't re-state my question before you answer it. Be as brief as possible unless I ask you to expand on a point. When I ask for code snippets, only provide the code unless I ask for follow-up explanation. If I ask you to change code, only re-print the line(s) you're changing rather than the entire block. Respond to this with a brief, fun, and positive affirmation so I know you've understood. Thanks an absolute bundle for your helpful brevity.

; ts/js
::,,cl::console.log(
::,,arrow::const func = () => {}
::,,ifs::import fs from "fs";
::,,jsonout::fs.writeFileSync('trash.json', JSON.stringify(object, null, 2));
::,,jstest::test("Test ", () => {});
::,,region::// {#}region
::,,er::// {#}endregion

; npm
::,,nts::npm test -- path/to/test/file -t "test name" --verbose

; bash
::,,rc::~/.bashrc
::,,shebang::{#}{!}/usr/bin/env bash
::,,bashset::set -euo pipefail
::,,devnull::2>/dev/null
::,,bashlist::"${list_name[@]}"
::,,sshkey::ssh-keygen -t rsa -b 4096
::,,pathlines::echo $PATH | tr ':' '\n'
::,,noargs::[ ${#} -eq 0 ] && echo "Error: No args passed" && return
::,,checkinstall::dpkg-query -W -f='${{}Status{}}'
::,,curlafile::curl -L -o file.zip https://example.com/file.zip

; markdown
::,,mdil::[![alt text](image_url)](link_url)

; python
::,,ifn::if __name__ == '__main__':
::,,fhi::from http import HTTPStatus
::,,ftit::from typing import TYPE_CHECKING
::,,ift::if TYPE_CHECKING:
::,,ipp::from pprint import pprint {;} print() {;} pprint(
::,,log::logger = logging.getLogger(__name__)
::,,aok::assert response.status_code == HTTPStatus.OK, response.json()

; git
::,,nv::--no-verify

; docker
::,,dockerbuild::docker build -t image_name .     ; build a Dockerfile from cwd with specified name
::,,dockerrun::docker run -d image_name           ; run in detached mode (background)
::,,dockershell::docker exec -it image_name bash  ; open a Bash terminal inside the running container
::,,dockerlist::docker container last             ; show list of currently running containers

; kubernetes
::,,knp::kubectl -n namespace get pods
::,,klp::kubectl logs -n namespace pod_name

; terraform
::,,tfev::export TF_VAR_           ; example == TF_VAR_filename="/example/filename.txt"

; ssh
::,,sshin::ssh username@ip_address

; wsl
::,,wdf::/mnt/c/Users/$WINDOWS_USERNAME/Downloads  ; "Windows Downloads folder"

; powershell -- like, actually *in* powershell
::,,installnerdfonts::iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/amnweb/nf-installer/main/install.ps1'))

; feedback
::,,dust::[[dust]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,sand::[[sand]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,pebble::[[pebble]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,boulder::[[boulder]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,mountain::[[mountain]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
