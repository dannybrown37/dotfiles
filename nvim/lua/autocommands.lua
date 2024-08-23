--#region
-- NOTE: [[ Basic Autocommands ]] See `:help lua-guide-autocommands`

vim.api.nvim_create_autocmd("TextYankPost", {
	desc = "Highlight when yanking (copying) text",
	group = vim.api.nvim_create_augroup("kickstart-highlight-yank", { clear = true }),
	callback = function()
		vim.highlight.on_yank()
	end,
})

vim.api.nvim_create_autocmd("BufWritePre", {
	desc = "Format file on save by removing trailing whitespace",
	pattern = "*",
	callback = function()
		vim.cmd("%s/\\s\\+$//e")
		vim.cmd("%s/\\r//e")
	end,
})

vim.api.nvim_create_autocmd("BufEnter", {
	desc = "Open help window in vertical split on entering a help buffer",
	pattern = "*.txt",
	callback = function()
		if vim.bo.filetype == "help" then
			vim.cmd("wincmd L")
		end
	end,
})

vim.api.nvim_create_autocmd("CursorHold", {
	desc = "Highlight word under cursor",
	callback = function()
		vim.cmd("match Search /\\V\\<" .. vim.fn.expand("<cword>") .. "\\>/")
	end,
})

--#endregion
