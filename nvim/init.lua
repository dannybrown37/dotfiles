--[[  NOTE: These are Danny's Neovim settings
      A helpful lua syntax guide:  https://learnxinyminutes.com/docs/lua/
      A guide on neovim's lua integration:  https://neovim.io/doc/user/lua-guide.html
      If experiencing any errors while trying to run inti.lua, run `:checkhealth` for more info.
--]]

--NOTE: Settings need to be loaded before lazy.nvim is loaded
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
	ui = {
		icons = vim.g.have_nerd_font and {} or {
			cmd = "⌘",
			config = "🛠",
			event = "📅",
			ft = "📂",
			init = "⚙",
			keys = "🗝",
			plugin = "🔌",
			runtime = "💻",
			require = "🌙",
			source = "📄",
			start = "🚀",
			task = "📌",
			lazy = "💤 ",
		},
	},
})

-- NOTE: Keymaps and autocommands need to be loaded after lazy.nvim is loaded
require("keymaps")
require("autocommands") -- includes autocmds for lsp autoformatting

-- The line beneath this is called `modeline`. See `:help modeline`
-- vim: ts=2 sts=2 sw=2 et
