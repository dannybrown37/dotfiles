-- INFO:
-- this file holds work in progress and nvim ideas I'm not 100% about incorporating yet

function COPY_REGION_TO_REGION()
	local bufnr = vim.fn.bufnr("%") -- Get current buffer number
	local cursor = vim.api.nvim_win_get_cursor(0)
	local start_line = cursor[1]
	local end_line = cursor[1]
	-- Find start of region
	while start_line > 1 do
		if vim.api.nvim_buf_get_lines(bufnr, start_line - 1, start_line, false)[1]:find("#region") then
			break
		end
		start_line = start_line - 1
	end
	-- Find end of region
	local line_count = vim.api.nvim_buf_line_count(bufnr)
	while end_line <= line_count do
		if vim.api.nvim_buf_get_lines(bufnr, end_line - 1, end_line, false)[1]:find("#endregion") then
			break
		end
		end_line = end_line + 1
	end
	local lines_to_yank = vim.api.nvim_buf_get_lines(bufnr, start_line - 1, end_line, false)
	vim.fn.setreg("0", lines_to_yank)
	local content = table.concat(lines_to_yank, "\n")
	vim.highlight.on_yank({ higroup = "IncSearch", timeout = 200 })
	print("yanked current region")
	-- Note: This requires the `xclip` or `xsel` command-line tool to be installed
	local command = string.format('echo -n "%s" | xclip -selection clipboard', content)
	vim.fn.system(command)
end
-- Bind this function to a key mapping in Neovim
vim.api.nvim_set_keymap("n", "yar", ":lua COPY_REGION_TO_REGION()<CR>", { noremap = true, silent = true })
