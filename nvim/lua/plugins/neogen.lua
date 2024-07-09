-- Docstring creation, quickly create docstrings via `<leader>a`
return {
	"danymat/neogen",
	opts = {},
	keys = {
		{
			"<leader>a",
			function()
				require("neogen").generate({})
			end,
			desc = "Add Docstring",
		},
	},
}
