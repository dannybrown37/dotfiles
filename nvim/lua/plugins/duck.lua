return {
	"tamton-aquib/duck.nvim",
	config = function()
		vim.keymap.set("n", "<leader>dd", function()
			require("duck").hatch()
		end, { desc = "Duck hatch" })
		vim.keymap.set("n", "<leader>dk", function()
			require("duck").cook()
		end, { desc = "Duck kill" })
		vim.keymap.set("n", "<leader>da", function()
			require("duck").cook_all()
		end, { desc = "Duck kill all" })
	end,
}
