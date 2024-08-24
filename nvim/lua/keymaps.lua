--#region
-- NOTE: [[ Basic Keymaps ]] See `:help vim.keymap.set()`

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
vim.keymap.set({ "n", "i" }, "<F2>", function()
	if vim.fn.mode() == "i" then
		vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "n", true)
		vim.wait(49, function()
			return vim.fn.mode() == "n"
		end)
	end
	vim.lsp.buf.rename()
end, { noremap = true, silent = true, desc = "Rename symbol" })
vim.api.nvim_set_keymap("n", "<A-j>", ":m .+1<CR>==", { noremap = true, silent = true, desc = "Move line down" })
vim.api.nvim_set_keymap("n", "<A-Down>", ":m .+1<CR>==", { noremap = true, silent = true, desc = "Move line down" })
vim.api.nvim_set_keymap("n", "<A-k>", ":m .-2<CR>==", { noremap = true, silent = true, desc = "Move line up" })
vim.api.nvim_set_keymap("n", "<A-Up>", ":m .-2<CR>==", { noremap = true, silent = true, desc = "Move line up" })
--#endregion

--#region <leader> Keymaps of my own

vim.keymap.set("n", "<leader>e", vim.cmd.Ex, { desc = "[E]xplore files from curent location" })

local fn = require("functions")
vim.keymap.set("n", "<leader>n", fn.CreateNote, { desc = "[N]ote file (created in ~/notes)" })

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
		attach_mappings = function(_, _)
			actions.select_default:replace(function(prompt_bufnr)
				actions.close(prompt_bufnr)
				local selection = action_state.get_selected_entry()
				vim.cmd("vsplit " .. selection.path)
			end)
			return true
		end,
	})
end, { desc = "[S]earch for and [V]ertically split a file" })

vim.keymap.set("n", "<leader>/", function()
	builtin.current_buffer_fuzzy_find(require("telescope.themes").get_dropdown({
		winblend = 10,
		previewer = false,
	}))
end, { desc = "[/] Fuzzily search in current buffer" })

vim.keymap.set("n", "<leader>s/", function()
	builtin.live_grep({
		grep_open_files = true,
		prompt_title = "Live Grep in Open Files",
	})
end, { desc = "[S]earch [/] in Open Files" })

vim.keymap.set("n", "<leader>sn", function()
	builtin.find_files({ cwd = vim.fn.stdpath("config") })
end, { desc = "[S]earch [N]eovim configuration files" })

--#endregion

--#region Harpoon Keymaps
local harpoon = require("harpoon")
harpoon:setup()

vim.keymap.set("n", "<leader>h", ":Telescope harpoon marks<CR>", { desc = "Show [H]arpoon Marks" })

vim.keymap.set("n", "<leader>m", function()
	harpoon:list():add()
end, { desc = "[M]ark with Harpoon" })

vim.keymap.set("n", "<C-n>", function()
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

--#region Undotree Keymaps (https://github.com/mbbill/undotree)
vim.keymap.set("n", "<leader>tu", function()
	vim.cmd("UndotreeToggle")
end, { desc = "[T]oggle [U]ndotree" })
--#endregion

--#region Fugitive Keymaps (https://github.com/tpope/vim-fugitive)
vim.keymap.set("n", "<leader>g", vim.cmd.Git, { desc = "[G]it status" })
