--#region
-- NOTE: [[ Basic Keymaps ]] See `:help vim.keymap.set()`

-- Set highlight on search, but clear on pressing <Esc> in normal mode
vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Clear highlight on search in normal mode" })
vim.keymap.set("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Open diagnostic [Q]uickfix list" })

-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
vim.keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })

-- region The Windows Section -- because it's silly to ignore decades of muscle memory

vim.api.nvim_set_keymap("i", "<C-S>", "<Esc>:w<CR>", { noremap = true, desc = "Exit insert mode and save file" })
vim.api.nvim_set_keymap("i", "<C-a>", "<Esc>VggG", { noremap = true, desc = "Select from cursor to end of document" })
vim.api.nvim_set_keymap("n", "<C-a>", "VggG", { noremap = true, desc = "Select from cursor to end of document" })
vim.api.nvim_set_keymap("v", "<C-c>", "y", { noremap = true, desc = "Copy text in visual mode" })
vim.api.nvim_set_keymap("i", "<C-v>", "p", { noremap = true, desc = "Paste text in insert mode" })
vim.api.nvim_set_keymap("v", "<C-x>", "d", { noremap = true, desc = "Cut text in visual mode" })
vim.api.nvim_set_keymap("n", "<C-z>", "u", { noremap = true, desc = "Undo" })
vim.api.nvim_set_keymap("i", "<C-z>", "<Esc>u", { noremap = true, desc = "Undo" })

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

vim.keymap.set("n", "<leader>e", vim.cmd.Ex, { desc = "[E]xplore files from curent location" })

function CREATE_NOTE()
	local notes_dir = os.getenv("HOME") .. "/notes/"
	vim.fn.mkdir(notes_dir, "p")
	local note_title = vim.fn.input("Enter note title: ")
	if note_title == "" then
		print("A note title is required.")
		return
	end
	print("\nEnter note content one line at a time (empty input to finish): ")
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
vim.api.nvim_set_keymap(
	"n",
	"<leader>n",
	":lua CREATE_NOTE()<CR>",
	{ noremap = true, silent = true, desc = "[N]ote file (created in ~/notes)" }
)

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

local actions = require("telescope.actions")
local action_state = require("telescope.actions.state")

vim.keymap.set("n", "<leader>sv", function()
	builtin.find_files({
		-- layout_strategy = "vertical",
		attach_mappings = function(_, map)
			-- Replace the default selection action with one that opens in a vertical split
			actions.select_default:replace(function(prompt_bufnr)
				actions.close(prompt_bufnr)
				local selection = action_state.get_selected_entry()
				vim.cmd("vsplit " .. selection.path)
			end)
			return true
		end,
	})
end, { desc = "[S]earch for and [V]ertically split a file" })

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

--#endregion

--#region Harpoon Keymaps
local harpoon = require("harpoon")
harpoon:setup()

vim.keymap.set("n", "<leader>h", ":Telescope harpoon marks<CR>", { desc = "Show [H]arpoon Marks" })

vim.keymap.set("n", "<leader>m", function()
	harpoon:list():add()
end, { desc = "[M]ark with Harpoon" })

vim.keymap.set("n", "<C-h>", function()
	harpoon.ui:toggle_quick_menu(harpoon:list())
end, { desc = "[H]arpoon Quick Menu Toggle" })

vim.keymap.set("n", "<C-u>", function()
	harpoon:list():select(1)
end)
vim.keymap.set("n", "<C-i>", function()
	harpoon:list():select(2)
end)
vim.keymap.set("n", "<C-o>", function()
	harpoon:list():select(3)
end)
vim.keymap.set("n", "<C-p>", function()
	harpoon:list():select(4)
end)

--#endregion
