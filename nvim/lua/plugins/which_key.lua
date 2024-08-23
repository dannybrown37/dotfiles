return { -- Useful plugin to show you pending keybinds.
	"folke/which-key.nvim",
	event = "VimEnter", -- Sets the loading event to 'VimEnter'
	config = function() -- This is the function that runs, AFTER loading
		require("which-key").setup()
		-- Document existing key chains
		require("which-key").register({
			-- ["<leader>c"] = { name = "[C]", _ = "which_key_ignore" },
			-- ["<leader>d"] = { name = "[D]", _ = "which_key_ignore" },
			-- ["<leader>e"] = { name = "[E]", _ = "which_key_ignore" },
			-- ["<leader>f"] = { name = "[F]", _ = "which_key_ignore" },
			["<leader>g"] = { name = "[G]oto (LSP)", _ = "which_key_ignore" },
			-- ["<leader>h"] = { name = "[H]", _ = "which_key_ignore" },
			-- ["<leader>i"] = { name = "[I]", _ = "which_key_ignore" },
			-- ["<leader>r"] = { name = "[R]", _ = "which_key_ignore" },
			["<leader>s"] = { name = "[S]earch", _ = "which_key_ignore" },
			["<leader>t"] = { name = "[T]oggle", _ = "which_key_ignore" },
			["<leader>y"] = { name = "S[y]mbols (LSP)", _ = "which_key_ignore" },
		})
	end,
}
