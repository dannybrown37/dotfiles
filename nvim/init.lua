--[[  NOTE: These are Danny's Neovim settings
      A helpful lua syntax guide:  https://learnxinyminutes.com/docs/lua/
      A guide on neovim's lua integration:  https://neovim.io/doc/user/lua-guide.html
      If experiencing any errors while trying to run inti.lua, run `:checkhealth` for more info.
--]]

require("settings")

--  See `:help lazy.nvim.txt` or https://github.com/folke/lazy.nvim for more info
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
	local lazyrepo = "https://github.com/folke/lazy.nvim.git"
	vim.fn.system({ "git", "clone", "--filter=blob:none", "--branch=stable", lazyrepo, lazypath })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
	{ import = "plugins" }, -- one plugin config per file in lua/plugins
}, {
	ui = require("iconconfig"),
})

require("keymaps")
require("autocommands") -- includes autocmds for lsp autoformatting

-- The line beneath this is called `modeline`. See `:help modeline`
-- vim: ts=2 sts=2 sw=2 et
