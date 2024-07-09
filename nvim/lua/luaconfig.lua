vim.api.nvim_create_autocmd("FileType", {
	pattern = "lua",
	callback = function()
		vim.opt_local.expandtab = true
		vim.opt_local.shiftwidth = 2
		vim.opt_local.tabstop = 2
		vim.opt_local.softtabstop = 2
		vim.opt_local.foldmethod = "manual"
		local iabbrev = function(lhs, rhs)
			vim.keymap.set("i", lhs, rhs, { buffer = true, silent = true })
		end
		-- Insert Lua specific abbreviations here
		iabbrev("local", "local ")
		iabbrev("function", "function ")
		-- Add more abbreviations as needed
	end,
})
