--#region
-- NOTE: Global Settings
-- Sets <space> as the leader key  -- See `:help mapleader`
-- WARNING: Must happen before plugins are loaded (otherwise wrong leader will be used)
vim.g.mapleader = " "
vim.g.maplocalleader = " "
vim.g.have_nerd_font = true -- Set to true if you have a Nerd Font installed and selected in the terminal
--#endregion

--#region
-- NOTE: [[ Setting options ]]  -- See `:help vim.opt`  For more options, you can see `:help option-list`
vim.opt.number = true -- line numbers show
vim.opt.relativenumber = true -- relative live numbers for faster jumping
vim.opt.scrolloff = 10 -- Minimal number of screen lines to keep above and below the cursor.
vim.opt.signcolumn = "yes" -- Keep signcolumn on by default

vim.opt.mouse = "a" -- Enable mouse mode, can be useful for resizing splits for example!
vim.opt.showmode = false -- already shown in status bar
vim.opt.clipboard = "unnamedplus" -- Sync clipboard between OS and Neovim.
vim.opt.cursorline = true -- Show which line your cursor is on
vim.opt.updatetime = 25 -- Decrease update time
vim.opt.timeoutlen = 30 -- Decrease mapped sequence wait time  -- Displays which-key popup sooner
vim.opt.splitright = true -- Configure how new splits should be opened
vim.opt.splitbelow = true
vim.opt.list = true -- `:help 'list'`
vim.opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" } --  `:help 'listchars'`, how white space is displayed

vim.opt.inccommand = "split" -- Preview substitutions live, as you type!
vim.opt.hlsearch = true
vim.opt.incsearch = true
vim.opt.ignorecase = true -- Case-insensitive searching UNLESS \C or one or more capital letters in the search term
vim.opt.smartcase = true

vim.opt.undofile = true

vim.opt.breakindent = true
vim.opt.smartindent = true
vim.opt.wrap = false

vim.opt.expandtab = true
vim.opt.shiftwidth = 4
vim.opt.softtabstop = 4
vim.opt.tabstop = 4
vim.opt.foldmethod = "manual"

vim.opt.colorcolumn = "72,79,88,100"
vim.opt.termguicolors = true
--#endregion
