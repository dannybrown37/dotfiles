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
