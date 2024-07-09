vim.api.nvim_create_autocmd("FileType", {
	pattern = "python",
	callback = function()
		-- use pep8 standards
		vim.opt_local.expandtab = true
		vim.opt_local.shiftwidth = 4
		vim.opt_local.tabstop = 4
		vim.opt_local.softtabstop = 4
		-- folds based on indentation https://neovim.io/doc/user/fold.html#fold-indent
		-- if you are a heavy user of folds, consider using `nvim-ufo`
		vim.opt_local.foldmethod = "manual"
		local iabbrev = function(lhs, rhs)
			vim.keymap.set("ia", lhs, rhs, { buffer = true })
		end
		-- automatically capitalize boolean values. Useful if you come from a
		-- different language, and lowercase them out of habit.
		iabbrev("true", "True")
		iabbrev("false", "False")
		-- put us in Python if we happen to be in TS mode
		iabbrev("//", "#")
		iabbrev("null", "None")
		iabbrev("none", "None")
	end,
})
