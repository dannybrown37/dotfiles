; Bash aliases become ,,name hotstrings. Loaded on a timer so the WSL round
; trip doesn't delay every other hotkey at startup.
Aliases := Map()
SetTimer(LoadAliases, -1)

LoadAliases() {
    global Aliases
    ; Update the \\wsl$ path below if your WSL distro isn't Debian.
    try {
        RunWait('wsl.exe bash -l -i -c "source ~/.bashrc; alias > /tmp/aliases.txt"', , "Hide")
        output := FileRead("\\wsl$\Debian\tmp\aliases.txt", "UTF-8")
    } catch
        return
    ; These names have their own dynamic ,,name hotstring below that fetches
    ; live data instead of typing the alias's literal command string.
    dynamicHotstringNames := Map("song", true, "sorn", true)
    for aliasName, aliasValue in ParseAliases(output) {
        if dynamicHotstringNames.Has(aliasName)
            continue
        Aliases[aliasName] := aliasValue
        ; T (text mode): alias values are shell, where !, ^, + and {} are
        ; literal characters, not keystroke modifiers.
        Hotstring(":T:,," aliasName, aliasValue)
    }
}


; Commands that don't need to be expanded to run should be
; defined as Bash aliases in config/.bash_aliases. We can
; expand them with a triple-comma, but it's not necessary
; for usage in the CLI.

; Commands that are not intended to be run in the CLI, such
; as code snippets or partial commands that need to be
; adjusted before they are run, should be defined in this
; file.

; project-based
::,,scr::SKIP=changelog-reminder


; ts/js
:*:,,cl::console.log(){Left}
:*:,,arrow::const func = () => {{}{}}{Left}
:*:,,ifs::import fs from "fs";
:*:,,jsonout::fs.writeFileSync('trash.json', JSON.stringify(object, null, 2));
:*:,,jstest::test("", () => {{}{}});{Left 13}
:*:,,region::// {#}region
:*:,,er::// {#}endregion

; npm
:*:,,nts::npm test -- path/to/test/file -t "test name" --verbose

; bash
:*:,,rc::~/.bashrc
:*:,,shebang::{#}{!}/usr/bin/env bash
:*:,,bashset::set -euo pipefail
:*:,,devnull::2>/dev/null
:*:,,bashlist::"${list_name[@]}"
:*:,,sshkey::ssh-keygen -t rsa -b 4096
:*:,,pathlines::echo $PATH | tr ':' '\n'
:*:,,noargs::[ ${#} -eq 0 ] && echo "Error: No args passed" && return
:*:,,checkinstall::dpkg-query -W -f='${{}Status{}}'
:*:,,curlafile::curl -L -o file.zip https://example.com/file.zip
:*:,,ds::DEV_STACK=

; markdown
:*:,,mdil::{[}{!}[alt_text](image_url)](link_url)

; python
:*:,,ifn::if __name__ == '__main__':
:*:,,fhi::from http import HTTPStatus
:*:,,ftit::from typing import TYPE_CHECKING
:*:,,ift::if TYPE_CHECKING:
:*:,,ipp::from pprint import pprint {;} print() {;} pprint(){Left}
:*:,,log::logger = logging.getLogger(__name__)
:*:,,aok::assert response.status_code == HTTPStatus.OK, response.json()
:*:,,env::from os import environ as env
:*:,,bp::breakpoint()

; git
:*:,,nv::--no-verify

; docker
:*:,,dockerbuild::docker build -t image_name .     ; build a Dockerfile from cwd with specified name
:*:,,dockerrun::docker run -d image_name           ; run in detached mode (background)
:*:,,dockershell::docker exec -it image_name bash  ; open a Bash terminal inside the running container
:*:,,dockerlist::docker container ls               ; show list of currently running containers

; kubernetes
:*:,,knp::kubectl -n namespace get pods
:*:,,klp::kubectl logs -n namespace pod_name

; terraform
:*:,,tfev::export TF_VAR_           ; example == TF_VAR_filename="/example/filename.txt"

; ssh
:*:,,sshin::ssh username@ip_address

; wsl
:*:,,wdf::/mnt/c/Users/$WINDOWS_USERNAME/Downloads  ; "Windows Downloads folder"

; powershell -- like, actually *in* powershell
:*:,,installnerdfonts::iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/amnweb/nf-installer/main/install.ps1'))

; feedback
:*:,,dust::[[dust]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
:*:,,sand::[[sand]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
:*:,,pebble::[[pebble]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
:*:,,boulder::[[boulder]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
:*:,,mountain::[[mountain]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)

; Strudel
:*X:,,switchangel::SendText("await (async () => { (0, eval)(await (await fetch('https://raw.githubusercontent.com/switchangel/strudel-scripts/refs/heads/main/prebake.strudel')).text()); })();")

; Spotify -- dynamic hotstrings, fetch live data from WSL and insert it
; directly instead of typing a fixed string (see the exclusion list in
; LoadAliases above). Both bash functions print only their result to stdout,
; so the captured file content is exactly what gets inserted.
InsertSpotifyOutput(bashFunction) {
    try exitCode := RunWait('wsl.exe bash -l -i -c "source ~/.bashrc; ' bashFunction ' >/tmp/spotify_hotstring_output.txt"', , "Hide")
    catch
        exitCode := -1
    if exitCode {
        MsgBox(bashFunction " failed (exit " exitCode ") -- is a track playing?")
        return
    }
    ; Update this path if your WSL distro isn't Debian.
    SendText(Trim(FileRead("\\wsl$\Debian\tmp\spotify_hotstring_output.txt", "UTF-8"), "`r`n"))
}

; @doc song: ,,song -- insert a Spotify link for the currently playing track
:*X:,,song::InsertSpotifyOutput("spotify_copy_playing_link")

; @doc sorn: ,,sorn -- insert "Song On Right Now" markdown for the currently playing track
:*X:,,sorn::InsertSpotifyOutput("spotify_now_playing_markdown")
