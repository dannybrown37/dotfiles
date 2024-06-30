#SingleInstance Force
#NoEnv ; Recommended for performance and compatibility with future AutoHotkey releases.
#Warn ; Enable warnings to assist with detecting common errors.

SendMode Input ; Recommended for new scripts due to its superior speed and reliability.


; LLM tools
::,,llm::For future responses in this chat: never apologize. Don't re-state my question before you answer it. Be as brief as possible unless I ask you to expand on a point. When I ask for code snippets, only provide the code unless I ask for follow-up explanation. Respond to this with a brief, fun, and positive affirmation so I know you've understood. Thanks!


; personal
::,,me::Danny Brown
::@@::dannybrown37@gmail.com
::,,linkedin::https://www.linkedin.com/in/dannybrown37
::,,github::https:://www.github.com/dannybrown37
::,,installdotfiles::curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash


; ts/js
::,,cl::console.log(
::,,arrow::const funcname = () => {}
::,,ifs::import fs from "fs";
::,,jsonout::fs.writeFileSync('trash.json', JSON.stringify(object, null, 2));
::,,jstest::test("Test ", () => {});
::,,region::// {#}region
::,,er::// {#}endregion


; npm
::,,nt::npm test
::,,nts::npm test -- path/to/test/file -t "test name" --verbose
::,,nr::npm run
::,,ns::npm start
::,,nsa::npm start -- --
::,,nrp::npm run pytest


; bash
::,,rc::~/.bashrc
::,,src::source ~/.bashrc
::,,crc::code ~/.bashrc
::,,devnull::2>/dev/null
::,,bashlist::"${list_name[@]}"
::,,sshkey::ssh-keygen -t rsa -b 4096 "email@email.email"
::,,pathlines::echo $PATH | tr ':' '\n'
::,,noargs::[ ${#} -eq 0 ] && echo "Error: No args passed" && return
::,,done::&& push_to_topic danny_build_notifications The script has finished running.
::,,checkinstall::dpkg-query -W -f='${{}Status{}}'


; python
::,,ifn::if __name__ == '__main__':
::,,fhi::from http import HTTPStatus
::,,ftit::from typing import TYPE_CHECKING
::,,ift::if TYPE_CHECKING:
::,,ipp::from pprint import pprint {;} print() {;} pprint(
::,,log::logger = logging.getLogger(__name__)
::,,rst::ruff check src tests
::,,rfst::ruff format src tests
::,,pv::python --version
::,,aok::assert response.status_code == HTTPStatus.OK, response.json()


; venv
::,,pmv::python -m venv .venv && source .venv/bin/activate
::,,vba::source .venv/bin/activate
::,,nuke::deactivate {;} rm -r .venv && python -m venv .venv && source .venv/bin/activate
; autoenv setup to auto activate an environment and let you know by echoing the folder
::,,newdotenv::echo "source .venv/bin/activate" >> .env && echo "echo '$(basename $(pwd)) env activated'" >> .env && source .env


; pytest
::,,ptt::pytest tests
::,,ptu::pytest tests/unit
::,,pte::pytest tests/e2e
::,,ptc::pytest tests/e2e/cloud
::,,ptl::pytest tests/e2e/local


; pip
::,,pir::pip install -r requirements.txt --require-virtualenv
::,,pirdev::pip install -r requirements.dev.txt --require-virtualenv
::,,pirdocs::pip install -r requirements.docs.txt --require-virtualenv
::,,pie::pip install -e . --require-virtualenv
::,,pf::pip freeze
::,,puf::pip freeze | xargs pip uninstall -y   ; "pip uninstall freeze", removes all packages installed
::,,pup::python -m pip install --upgrade pip


; poetry
::,,pl::poetry lock
::,,pr::poetry run
::,,piae::poetry install --all-extras
::,,pidocs::poetry install --with docs
::,,pidev::poetry install --with dev
::,,prp::poetry run python
::,,ptufb::firebase emulators:exec "poetry run pytest tests/unit -v"
::,,poetrynuke::poetry env remove --all


; git
::,,gs::git status
::,,gpr::git pull rebase
::,,gap::git add -p
::,,gc::git commit -m "
::,,gca::git commit --amend -m "
::,,gcr::git commit --amend --no-edit  ; "git commit rebase", updates last commit
::,,grh::git rebase -i HEAD~
::,,grd::git rebase develop
::,,grm::git rebase main
::,,gco::git checkout
::,,gcb::git checkout -b
::,,gcd::git checkout develop
::,,gcm::git checkout main
::,,gcl::git checkout -
::,,gp::git push
::,,gpf::git push -f
::,,gpo::git push -u origin
::,,glo::git log -1 --pretty=%B ; shows last commit message
::,,gitpurge::git branch | grep -v -e "main" -e "develop" -e "magic" -e "$(git rev-parse --abbrev-ref HEAD)" | xargs git branch -D ; deletes all local branches not named main or develop or currently checked out
::,,gred::git reset --hard origin/develop  ; fix a diverged develop branch
::,,nv::--no-verify
::,,gsu::git submodule update
::,,gsi::git submodule update --init --recursive
::,,grc::git rebase --continue
::,,gra::git rebase --abort
::,,gcue::git config --global user.email "dannybrown37@gmail.com"
::,,gcun::git config --global user.name "Danny Brown"
::,,gcdf::git clone https://www.github.com/dannybrown37/dotfiles


; serverless
::,,sdd::sls deploy --stage=danny
::,,sid::sls info --stage=danny
::,,srd::sls remove --stage=danny


; terraform
::,,tf::terraform
::,,tfi::terraform init
::,,tfv::terraform validate
::,,tff::terraform fmt           ; format config files to canonical formatting
::,,tfp::terraform plan
::,,tfpro::terraform providers   ; see list of all providers in the configuration directory
::,,tfa::terraform apply
::,,tfs::terraform show          ; show current state
::,,tfsj::terraform show -json
::,,tfo::terraform output        ; show defined output variables
::,,tfd::terraform destroy
::,,tfr::terraform refresh       ; sync local terraform to any changes made to resources outside its control
::,,tfg::terraform graph | dot -Tsvg > graph.svg
; TF var definition order:
; 1. env vars -> 2. terraform.tfvars -> 3. *.auto.tfvars (alphabetical) -> 4. -var or -var-file flag
; It will load the above in the order listed, using the last one if multiple are defined.
::,,tfav::terraform apply -var "   ; example == -var "filename=/example/filename.txt"
::,,tfavf::terraform apply -var-file *.tfvars      ;  or just name *.auto.tfvars to not have to pass
::,,etfv::export TF_VAR_           ; example == TF_VAR_filename="/example/filename.txt"


; docker
::,,dockerbuild::docker build -t image_name .     ; build a Dockerfile from cwd with specified name
::,,dockerrun::docker run -d image_name           ; run in detached mode (background)
::,,dockershell::docker exec -it image_name bash  ; open a Bash terminal inside the running container
::,,dockerlist::docker container last             ; show list of currently running containers


; kubernetes
::,,knp::kubectl -n namespace get pods
::,,klp::kubectl logs -n namespace pod_name


; feedback
::,,dust::[[dust]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,sand::[[sand]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,pebble::[[pebble]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,boulder::[[boulder]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
::,,mountain::[[mountain]](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)


; fixes for weird situations

; when a `sudo apt-get update` was failing due to a missing public key, this was the needle in the haystack among a lot of suggestions that didn't work
::,,fixhashicorppublickey::wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg

; Control+Shift+G will automatically search Google for text in clipboard
^+g::
{
  Send, ^c
  Sleep 50
  Run, https://www.google.com/search?q=%clipboard%
  Return
}

; Control + Shift + Z toggles Windows terminal
SwitchToWindowsTerminal()
{
  windowHandleId := WinExist("ahk_exe WindowsTerminal.exe")
  windowExistsAlready := windowHandleId > 0

  ; If the Windows Terminal is already open, determine if we should put it in focus or minimize it.
  if (windowExistsAlready = true)
  {
    activeWindowHandleId := WinExist("A")
    windowIsAlreadyActive := activeWindowHandleId == windowHandleId

    if (windowIsAlreadyActive)
    {
      ; Minimize the window.
      WinMinimize, "ahk_id %windowHandleId%"
    }
    else
    {
      ; Put the window in focus.
      WinActivate, "ahk_id %windowHandleId%"
      WinShow, "ahk_id %windowHandleId%"
    }
  }
  ; Else it's not already open, so launch it.
  else
  {
    Run, wt
  }
}
^+z::SwitchToWindowsTerminal()


; Control + Shift + X toggles Visual Studio Code
^+x::
  SwitchToVSCode()
return

SwitchToVSCode() {
  exeName := "Code.exe"
  windowHandleId := WinExist("ahk_exe " exeName)
  windowExistsAlready := windowHandleId > 0

  if (windowExistsAlready = true) {
    activeWindowHandleId := WinExist("A")
    windowIsAlreadyActive := activeWindowHandleId == windowHandleId

    if (windowIsAlreadyActive) {
      WinMinimize, "ahk_id %windowHandleId%"
    }
    else {
      WinActivate, "ahk_id %windowHandleId%"
      WinShow, "ahk_id %windowHandleId%"
    }
  }
  else {
    Run, % exeName
  }
}

; Ctrl+Shift+C to focus on open Chrome window
^+c::
{
     ; Attempt to activate Chrome by its window title
    SetTitleMatchMode, 2  ; Allows partial match for window titles
    if WinExist("Google Chrome")
    {
        WinActivate
    }
    else
    {
        MsgBox, Chrome is not running.
    }
    return
}

; Ctrl+Shift+D to open Microsoft T(D)eams
^+d::
{
    ; Attempt to activate Microsoft Teams by its window title
    SetTitleMatchMode, 2  ; Allows partial match for window titles
    if WinExist("Microsoft Teams")
    {
        WinActivate
        ; Wait for the window to be active
        WinWaitActive, Microsoft Teams

    }
    else
    {
        MsgBox, Microsoft Teams is not running.
    }
    return
}
