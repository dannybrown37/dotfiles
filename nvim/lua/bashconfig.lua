vim.api.nvim_create_autocmd("FileType", {
	pattern = "bash",
	callback = function()
		vim.opt_local.expandtab = true
		vim.opt_local.shiftwidth = 4
		vim.opt_local.tabstop = 4
		vim.opt_local.softtabstop = 4
		vim.opt_local.foldmethod = "manual" -- Set foldmethod to "syntax" for Bash scripts
		vim.opt_local.foldenable = true -- Enable folding
		vim.opt_local.foldlevel = 1 -- Set foldlevel to 1 for moderate folding
		local iabbrev = function(lhs, rhs)
			vim.keymap.set("i", lhs, rhs, { buffer = true, silent = true })
		end
		-- Insert Bash specific abbreviations here
		iabbrev("alias", "alias ")
		iabbrev("for", "for ")
		iabbrev("if", "if ")
		-- Add more abbreviations as needed
	end,
})
