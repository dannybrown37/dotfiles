vim.api.nvim_create_autocmd("FileType", {
	pattern = "typescript",
	callback = function()
		vim.opt_local.expandtab = true
		vim.opt_local.shiftwidth = 2
		vim.opt_local.tabstop = 2
		vim.opt_local.softtabstop = 2
		vim.opt_local.foldmethod = "manual"
		local iabbrev = function(lhs, rhs)
			vim.keymap.set("i", lhs, rhs, { buffer = true, silent = true })
		end
		-- put us in TS if we happen to be in Python mode
		iabbrev("True", "true")
		iabbrev("False", "false")
		iabbrev("#", "//")
		iabbrev("None", "null")
	end,
})
