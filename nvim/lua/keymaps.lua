--#region
-- NOTE: [[ Basic Keymaps ]] See `:help vim.keymap.set()`

-- Set highlight on search, but clear on pressing <Esc> in normal mode
vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>")

-- Diagnostic keymaps
vim.keymap.set("n", "[d", vim.diagnostic.goto_prev, { desc = "Go to previous [D]iagnostic message" })
vim.keymap.set("n", "]d", vim.diagnostic.goto_next, { desc = "Go to next [D]iagnostic message" })
vim.keymap.set("n", "<leader>e", vim.diagnostic.open_float, { desc = "Show diagnostic [E]rror messages" })
vim.keymap.set("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Open diagnostic [Q]uickfix list" })

-- Exit terminal mode in the builtin terminal with a shortcut that is a bit easier
-- for people to discover. Otherwise, you normally need to press <C-\><C-n>, which
-- is not what someone will guess without a bit more experience.
--
-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
vim.keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })

-- Keybinds to make split navigation easier. Use CTRL+<hjkl> to switch between windows
--  See `:help wincmd` for a list of all window commands
vim.keymap.set("n", "<C-h>", "<C-w><C-h>", { desc = "Move focus to the left window" })
vim.keymap.set("n", "<C-l>", "<C-w><C-l>", { desc = "Move focus to the right window" })
vim.keymap.set("n", "<C-j>", "<C-w><C-j>", { desc = "Move focus to the lower window" })
vim.keymap.set("n", "<C-k>", "<C-w><C-k>", { desc = "Move focus to the upper window" })

-- The Windows Section -- because you can't beat decades of muscle memory

-- Ctrl+S == save in both insert and normal mode
vim.api.nvim_set_keymap("n", "<C-S>", ":w<CR>", { noremap = true })
vim.api.nvim_set_keymap("i", "<C-S>", "<Esc>:w<CR>", { noremap = true })
-- Ctrl+A selects the full document
vim.api.nvim_set_keymap("n", "<C-a>", "ggVG", { noremap = true })
-- Ctrl+C to copy text
vim.api.nvim_set_keymap("v", "<C-c>", "y", { noremap = true })
-- Ctrl+V to paste for good measure
vim.api.nvim_set_keymap("n", "<C-v>", "p", { noremap = true })
-- Ctrl+X to cut text into clipboard
vim.api.nvim_set_keymap("v", "<C-x>", "d", { noremap = true })
-- Ctrl+Z to undo
vim.api.nvim_set_keymap("n", "<C-z>", "u", { noremap = true })
vim.api.nvim_set_keymap("i", "<C-z>", "<Esc>u", { noremap = true })

-- Use F2 for rename symbol
vim.keymap.set({ "n", "i" }, "<F2>", function()
	if vim.fn.mode() == "i" then
		-- Exit insert mode
		vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "n", true)
		-- Wait for mode change
		vim.wait(49, function()
			return vim.fn.mode() == "n"
		end)
	end
	-- Trigger rename
	vim.lsp.buf.rename()
end, { noremap = true, silent = true })

-- Move lines up and down with Alt + j and Alt + k
vim.api.nvim_set_keymap("n", "<A-j>", ":m .+1<CR>==", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<A-Down>", ":m .+1<CR>==", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<A-k>", ":m .-2<CR>==", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<A-Up>", ":m .-2<CR>==", { noremap = true, silent = true })

--#endregion
