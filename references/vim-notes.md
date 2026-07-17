## use `vc` command to run non-comment lines of this file into fzf

##
## neovim commands
##

:map <key>  -- see key bindings for a particular key
:nmap  -- all key bindings for normal mode
:vmap  -- all key bindings for visual mode
:imap  -- all key bindings for insert mode
:omap  -- all key binds for operator-pending mode

:Mason  -- package manager/installer, use i on selected line to install package
:checkhealth  -- run when if you encounter errors with init.lua
:Lazy -- check status of plugins, use ? in this menu for additional help
:Lazy update  -- update plugins etc.
:help  -- general neovim help
:help lua-guide  -- get help with lua integrations into neovim
:Telescope help_tags  -- search help tags via Telescope plugin (keymaps is a neat option)
:help telescope  -- learn more about telescope and how to use it
:help telescope.setup()  -- learn more about how to set up telescope
<c-/> && ?  -- important keymaps for telescope (TODO: investigate more)
:help lsp-vs-treesitter  -- maybe I'll want to look at this someday
:Telescope colorscheme  -- change the color scheme for the session

# debug
:redir! > ~/nvim_msgs.txt  -- errors sometimes flash on exit, review them by writing to a file

# buffers
:split  -- horizontally split the screen
:vsplit -- vertically split the screen
:edit <file/path> -- but <leader>sf to fuzzy search files is better
:enew  -- open a new file in the editor
:new  -- split horizontally and open a new file in the editor
:vnew  -- split vertically and open a new file in the editor

# tabs
:tabnew <filename>  -- open a new tab to an empty file or pass a file name/path
:tabclose  -- close the current tab
:tabonly  -- close all other tabs except the current one
:tabmove -/+1  -- move current tab to the left/right
:tabnext <or> :tabn -- switch to next tab
:tabprevious <or> :tabp -- switch to previous tab
:tabn <number> -- go to a specific tab by number



# Telescope commands w/ no space
gI -- go to implementation (useful for types defined separate from implementation)
gr -- go to references
gd -- go to definition of currently selected function/variable/etc. (requires language lsp)
gD -- go to declaration (i.e., the import statement)
K -- pop up documentation for the word under cursor; scroll away to remove


# Telescope space + commands
# Ctrl+P and Ctrl+N to scroll up and down in these context menus
sf -- search files
sh -- search help
ds -- document symbols fuzzy find, search current document for vars, functions, classes, etc.
ws -- workspace symbols fuzzy find, search entire workspace for vars, functions, classes, etc.
rn -- rename variable under cursor, with LSP should support multi-file changes


# numToStr/Comment.nvim plugin
gcc -- toggle comment on/off on current line

##
## vim
##

cheat sheet  -- https://cheatography.com/marconlsantos/cheat-sheets/neovim/

# macros
q<char>  -- start recording in the <char> macro
q        -- finish recording macro
@<char>  -- call recorded macro

# delete things fast
dw  -- delete the whole/rest of the word from the point of the cursor
dd  -- delete the whole line
<num>dd  -- delete the next <num> lines
d$ --  delete from cursor to end of line
d<num>w  -- delete the next <num> words in the line

# insert mode fast
o -- open a line below cursor in insert mode
O -- open a line above cursor in insert mode
i -- insert mode right before cursor
a -- insert mode right after cursor ("append")
A -- insert mode at end of line ("Append")
jA -- insert mode at the end of the next line
ja -- insert mode at next line moving cursor down vertically

# yank/place i.e., copy/paste
y -- yank/copy text selected
yw -- yank word, copy from cursor to end of word
p -- paste/place text copied or deleted after cursor
P -- paste/place text copied or deleted before cursor
yap  -- select and yank a full paragraph (copy/paste), white space to white space
yy  -- yanks/copies the full current line
yiw -- yank inner word, yanks current word without surrounding whitespace
yaw -- yank a word, but also yanks trailing whitespace
ygg -- yank from cursor to top of file
yG  -- yank from cursor to bottom of file


# shift text
Shift+>  -- shift selected right by a tab width
Shift+<  -- shift selected left by a tab width

# replacement
r<char> -- replace currently selected char with <char>
R -- replace characters until you hit <escape>
:s/<old>/<new>  -- replaces first instance of <old> with <new> on line
:s/<old>/<new>/g  -- replaces all instance of <old> with <new> on line
:#,#s/<old>/<new>/g  -- replace all instance <old> with <new> between lines # and #
:%s/<old>/<new>/g  -- replace all instances of <old> with <new> in whole file
:%s/<old>/<new>/gc  -- prompt for each instance of <old> in file whether to replace with <new>

# remove words/line
ce -- remove rest of the word from point of cursor and immediately put in insert mode
c<num>e -- remove <num> words
c$ -- remove until end of line and immediately put in insert mode

# file navigation
gg -- straight to top of the file
G  -- straight to bottom of the file
:<num>  -- straight to line number
<num>G  -- also straight to line number
0 -- straight to beginning of line
<num>w  -- move cursor forward <num> words
$  -- move cursor to end of current line
j$ -- move cursor to the end of the next line
e -- moves cursor to the end of the next word
<num>j  -- jump down <num> lines
<num>k  -- jump up <num> lines

% -- toggles between matching {} () [] icon selected

# undo/redo
u -- undo last command
U -- return current line to its original state
Ctrl+r  -- redo last undone change

# searching
/<phrase> + Enter -- searches file for phrase, then `n` moves cursor to next instance of phrase searched for

# external commands
:!<command>  -- execute external commands such as `ls` from within Neovim. Args accepted.

# SAVE AS
:w <NEW_FILE_NAME>  -- write current file to new location

# SAVE PART OF TEXT
v  -- visual selection, this will select the current line and allow you to select more with j/k or arrows, et al
V -- visual line selection
o -- while in visual mode, toggle between start and end of selection
:  -- after finishing selecting, enter this, you will see this: '<,'>
w <FILE_NAME>  -- write selected text to a new file named <FILE_NAME>
w! <FILE_NAME>  -- overwrite file if it already exists
d -- delete selected text

# Copying from a file
:r <FILE_NAME> -- copy the text of <FILE_NAME> below the cursor
:r!<command> -- copy the output of the command (such as `ls`) below the cursor

# :set command for settings
:set ic  -- ignore case in searching
:set noic  -- don't ignore case in searching
:set hls  -- highlights search term (pretty sure?)
:set is   -- inclusive search (matches when term matches parts of words)
:set invic -- inverts value of setting prefixed with "inv"
:nohlsearch -- removes highlighting of search
NOTE: If you want to ignore case for just one search command, use [\c](/\c) in the phrase: /ignore\c <Enter>

# help
:e<tab>  -- neovim will show all available commands that start with "e"
:help <command>  -- get docs on any command with :help
