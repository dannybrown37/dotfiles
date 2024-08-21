--#region
-- NOTE: [[ Basic Keymaps ]] See `:help vim.keymap.set()`

-- Set highlight on search, but clear on pressing <Esc> in normal mode
vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>")

-- Diagnostic keymaps
vim.keymap.set("n", "[d", vim.diagnostic.goto_prev, { desc = "Go to previous [D]iagnostic message" })
vim.keymap.set("n", "]d", vim.diagnostic.goto_next, { desc = "Go to next [D]iagnostic message" })
vim.keymap.set("n", "<leader>e", vim.diagnostic.open_float, { desc = "Show diagnostic [E]rror messages" })
vim.keymap.set("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Open diagnostic [Q]uickfix list" })

-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
vim.keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })

-- region The Windows Section -- because it's silly to ignore decades of muscle memory

-- Ctrl+S == save in both insert and normal mode
vim.api.nvim_set_keymap("n", "<C-S>", ":w<CR>", { noremap = true })
vim.api.nvim_set_keymap("i", "<C-S>", "<Esc>:w<CR>", { noremap = true })
-- Ctrl+A selects the full document
vim.api.nvim_set_keymap("n", "<C-a>", "VggG", { noremap = true })
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
		vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "n", true)
		vim.wait(49, function()
			return vim.fn.mode() == "n"
		end)
	end
	vim.lsp.buf.rename()
end, { noremap = true, silent = true })

-- Move lines up and down with Alt + j and Alt + k
vim.api.nvim_set_keymap("n", "<A-j>", ":m .+1<CR>==", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<A-Down>", ":m .+1<CR>==", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<A-k>", ":m .-2<CR>==", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<A-Up>", ":m .-2<CR>==", { noremap = true, silent = true })

--#endregion

--#region Leader Keymaps

vim.keymap.set("n", "<leader>ex", vim.cmd.Ex) -- explore files

function CREATE_NOTE()
	local notes_dir = os.getenv("HOME") .. "/notes/"
	vim.fn.mkdir(notes_dir, "p")
	local note_title = vim.fn.input("Enter note title: ")
	if note_title == "" then
		print("A note title is required.")
		return
	end
	print("Enter note content one line at a time (empty input to finish): ")
	local note_content = ""
	local line
	while true do
		line = vim.fn.input("")
		if line == "" then
			break
		end
		note_content = note_content .. line .. "\n"
	end
	local note_path = notes_dir .. note_title
	if vim.fn.filereadable(note_path) == 1 then
		print("Error: This note already exists!")
		return
	end
	local file = io.open(note_path, "w")
	if file then
		file:write(note_content)
		file:close()
		print("Note saved to: " .. note_path)
	else
		print("Error: Could not write the note.")
	end
end
vim.api.nvim_set_keymap("n", "<leader>note", ":lua CREATE_NOTE()<CR>", { noremap = true, silent = true })

--#endregion

--#region Telescope Keymaps
-- See `:help telescope.builtin`
local builtin = require("telescope.builtin")

vim.keymap.set("n", "<leadev>sh", builtin.help_tags, { desc = "[S]earch [H]elp" })
vim.keymap.set("n", "<leader>sk", builtin.keymaps, { desc = "[S]earch [K]eymaps" })
vim.keymap.set("n", "<leader>sf", builtin.find_files, { desc = "[S]earch [F]iles" })
vim.keymap.set("n", "<leader>ss", builtin.builtin, { desc = "[S]earch [S]elect Telescope" })
vim.keymap.set("n", "<leader>sw", builtin.grep_string, { desc = "[S]earch current [W]ord" })
vim.keymap.set("n", "<leader>sg", builtin.live_grep, { desc = "[S]earch by [G]rep" })
vim.keymap.set("n", "<leader>sd", builtin.diagnostics, { desc = "[S]earch [D]iagnostics" })
vim.keymap.set("n", "<leader>sr", builtin.resume, { desc = "[S]earch [R]esume" })
vim.keymap.set("n", "<leader>s.", builtin.oldfiles, { desc = '[S]earch Recent Files ("." for repeat)' })
vim.keymap.set("n", "<leader><leader>", builtin.buffers, { desc = "[ ] Find existing buffers" })

-- Slightly advanced example of overriding default behavior and theme
vim.keymap.set("n", "<leader>/", function()
	-- You can pass additional configuration to Telescope to change the theme, layout, etc.
	builtin.current_buffer_fuzzy_find(require("telescope.themes").get_dropdown({
		winblend = 10,
		previewer = false,
	}))
end, { desc = "[/] Fuzzily search in current buffer" })

-- It's also possible to pass additional configuration options.
--  See `:help telescope.builtin.live_grep()` for information about particular keys
vim.keymap.set("n", "<leader>s/", function()
	builtin.live_grep({
		grep_open_files = true,
		prompt_title = "Live Grep in Open Files",
	})
end, { desc = "[S]earch [/] in Open Files" })

-- Shortcut for searching your Neovim configuration files
vim.keymap.set("n", "<leader>sn", function()
	builtin.find_files({ cwd = vim.fn.stdpath("config") })
end, { desc = "[S]earch [N]eovim files" })
