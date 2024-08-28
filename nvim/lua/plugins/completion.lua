return {
	"hrsh7th/nvim-cmp",

	event = { "InsertEnter", "CmdlineEnter" },

	dependencies = {
		-- Snippet Engine & its associated nvim-cmp source
		{
			"L3MON4D3/LuaSnip",
			build = (function()
				if vim.fn.has("win32") == 1 or vim.fn.executable("make") == 0 then
					return
				end
				return "make install_jsregexp"
			end)(),
			dependencies = {
				{
					"rafamadriz/friendly-snippets",
					config = function()
						require("luasnip.loaders.from_vscode").lazy_load()
					end,
				},
			},
		},
		"saadparwaiz1/cmp_luasnip",
		"hrsh7th/cmp-nvim-lsp",
		"hrsh7th/cmp-path",
		{
			"supermaven-inc/supermaven-nvim",
			-- commit = "df3ecf7",
			event = "User FilePost",
			opts = {
				disable_keymaps = false,
				disable_inline_completion = false,
				keymaps = {
					accept_suggestion = "<Tab>",
					clear_suggestion = "<Nop>",
				},
			},
		},
		{
			"Exafunction/codeium.nvim",
			enabled = true,
			opts = {
				enable_chat = true,
			},
		},
	},

	config = function()
		local luasnip = require("luasnip")
		luasnip.config.setup({})
	end,
}
