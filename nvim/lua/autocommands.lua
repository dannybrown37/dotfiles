--#region
-- NOTE: [[ Basic Autocommands ]] See `:help lua-guide-autocommands`

-- Highlight when yanking (copying) text  --  See `:help vim.highlight.on_yank()`
vim.api.nvim_create_autocmd("TextYankPost", {
	desc = "Highlight when yanking (copying) text",
	group = vim.api.nvim_create_augroup("kickstart-highlight-yank", { clear = true }),
	callback = function()
		vim.highlight.on_yank()
	end,
})

--  Control white space at end of lines
vim.api.nvim_create_autocmd("BufWritePre", {
	pattern = "*",
	callback = function()
		vim.cmd("%s/\\s\\+$//e")
		vim.cmd("%s/\\r//e")
	end,
})

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
		vim.opt_local.foldmethod = "indent"
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

vim.api.nvim_create_autocmd("FileType", {
	pattern = "typescript",
	callback = function()
		vim.opt_local.expandtab = true
		vim.opt_local.shiftwidth = 2
		vim.opt_local.tabstop = 2
		vim.opt_local.softtabstop = 2
		vim.opt_local.foldmethod = "indent"
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
