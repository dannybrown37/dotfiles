--#region
-- NOTE: [[ Keymaps ]] See `:help vim.keymap.set()`

-- region The Windows Section -- because it's silly to ignore decades of muscle memory
vim.api.nvim_set_keymap("i", "<C-s>", "<Esc>:w<CR>", { noremap = true, desc = "Exit insert mode and save file" })
vim.api.nvim_set_keymap("i", "<C-a>", "<Esc>yG", { noremap = true, desc = "Select all from current line" })
vim.api.nvim_set_keymap("v", "<C-c>", "y", { noremap = true, desc = "Copy text in visual mode" })
vim.api.nvim_set_keymap("i", "<C-v>", "p", { noremap = true, desc = "Paste text in insert mode" })
vim.api.nvim_set_keymap("v", "<C-x>", "d", { noremap = true, desc = "Cut text in visual mode" })
vim.api.nvim_set_keymap("i", "<C-z>", "<Esc>u", { noremap = true, desc = "Undo" })
vim.api.nvim_set_keymap("i", "<C-S-Right>", "<C-o>vwe", { noremap = true, desc = "Visually select word to right" })
vim.api.nvim_set_keymap("i", "<C-S-Left>", "<C-o>vb", { noremap = true, desc = "Visually select word to left" })
--#endregion

--#region <leader> QOL Keymaps
vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Clear highlight on search in normal mode" })
vim.keymap.set("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Open diagnostic [Q]uickfix list" })
vim.keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" }) -- NOTE: This won't work in all terminal emulators/tmux/etc.

vim.api.nvim_set_keymap("n", "<C-j>", ":m .+1<CR>==", { noremap = true, silent = true, desc = "Move line down" })
vim.api.nvim_set_keymap("n", "<C-k>", ":m .-2<CR>==", { noremap = true, silent = true, desc = "Move line up" })
vim.api.nvim_set_keymap("v", "<C-j>", ":m '>+1<CR>gv=gv", { noremap = true, silent = true, desc = "Move lines down" })
vim.api.nvim_set_keymap("v", "<C-k>", ":m '<-2<CR>gv=gv", { noremap = true, silent = true, desc = "Move lines up" })

vim.keymap.set("n", "J", "20jzz", { desc = "Jump down 20 lines but keep cursor in center of screen" })
vim.keymap.set("n", "K", "20kzz", { desc = "Jump up 20 lines but keep cursor in center of screen" })

vim.keymap.set("n", "n", "nzzzv", { desc = "Keep cursor in center of screen when searching buffer" })
vim.keymap.set("n", "N", "Nzzzv", { desc = "Keep cursor in center of screen when searching buffer" })

vim.keymap.set("v", "<leader>o", ":'<,'>sort<CR>", { desc = "Sort selected lines" })
vim.keymap.set("v", "<leader>O", ":'<,'>sort!<CR>", { desc = "Sort selected lines in reverse" })
vim.keymap.set("n", "<leader>o", ":sort<CR>", { desc = "Sort current buffer" })
vim.keymap.set("n", "<leader>O", ":sort!<CR>", { desc = "Sort current buffer in reverse" })

vim.keymap.set("n", "<leader>rw", ":%s/\\<<C-r><C-w>\\>/<C-r><C-w>/gI", { desc = "[R]eplace [W]ord in current buffer" })

vim.keymap.set("n", "<leader>x", "<cmd>!chmod +x %<CR>", { desc = "Make current file e[x]ecutable" })

vim.keymap.set("n", "<leader>e", vim.cmd.Ex, { desc = "[E]xplore files from curent location" })

local fn = require("functions")
vim.keymap.set("n", "<leader>note", fn.CreateNote, { desc = "[N]ote file (created in ~/notes)" })
--#endregion

--#region Telescope Keymaps
-- See `:help telescope.builtin`
local builtin = require("telescope.builtin")
local actions = require("telescope.actions")
local action_state = require("telescope.actions.state")

vim.keymap.set("n", "<leadev>sh", builtin.help_tags, { desc = "[S]earch [H]elp" })
vim.keymap.set("n", "<leader>sk", builtin.keymaps, { desc = "[S]earch [K]eymaps" })
vim.keymap.set("n", "<leader>sf", builtin.find_files, { desc = "[S]earch [F]iles" })
vim.keymap.set("n", "<leader>ss", builtin.builtin, { desc = "[S]earch [S]elect Telescope" })
vim.keymap.set("n", "<leader>sw", builtin.grep_string, { desc = "[S]earch current [W]ord" })
vim.keymap.set("n", "<leader>sg", builtin.live_grep, { desc = "[S]earch by [G]rep" })
vim.keymap.set("n", "<leader>sD", builtin.diagnostics, { desc = "[S]earch [D]iagnostics" })
vim.keymap.set("n", "<leader>sr", builtin.resume, { desc = "[S]earch [R]esume" })
vim.keymap.set("n", "<leader>s.", builtin.oldfiles, { desc = '[S]earch Recent Files ("." for repeat)' })
vim.keymap.set("n", "<leader><leader>", builtin.buffers, { desc = "[ ] Find existing buffers" })

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

--#region Undotree (https://github.com/mbbill/undotree)
vim.keymap.set("n", "<leader>tu", function()
	vim.cmd("UndotreeToggle")
end, { desc = "[T]oggle [U]ndotree" })
--#endregion

--#region Fugitive / Git (https://github.com/tpope/vim-fugitive)
vim.keymap.set("n", "<leader>gs", ":Git status<CR>", { desc = "[G]it [S]tatus" })
vim.keymap.set("n", "<leader>gb", ":Git branch<CR>", { desc = "[G]it [B]ranch" })
vim.keymap.set("n", "<leader>gap", ":Git add -p<CR>", { desc = "[G]it [A]dd [P]atch" })
vim.keymap.set("n", "<leader>ga.", ":Git add .<CR>", { desc = "[G]it [A]dd [.]" })
vim.keymap.set("n", "<leader>gc", ":Git commit<CR>", { desc = "[G]it [C]ommit" })
vim.keymap.set("n", "<leader>gcm", ':Git commit --message "', { desc = "[G]it [C]ommit [M]essage" })
vim.keymap.set("n", "<leader>gca", ":Git commit --amend<CR>", { desc = "[G]it [C]ommit [A]mend" })
vim.keymap.set("n", "<leader>gcr", ":Git commit --amend --no-edit<CR>", { desc = "[G]it [C]ommit [R]ebase" })
vim.keymap.set("n", "<leader>gp", ":Git push<CR>", { desc = "[G]it [P]ush" })
--#endregion

--#region NPM
vim.keymap.set("n", "<leader>ni", "<cmd>! npm install<CR>", { desc = "[N]PM [I]nstall" })
vim.keymap.set("n", "<leader>nu", "<cmd>! npm update<CR>", { desc = "[N]PM [U]pdate" })
vim.keymap.set("n", "<leader>ns", "<cmd>! npm start<CR>", { desc = "[N]PM [S]tart" })
vim.keymap.set("n", "<leader>nl", "<cmd>! npm run lint<CR>", { desc = "[N]PM [L]int" })
vim.keymap.set("n", "<leader>nt", "<cmd>! npm test<CR>", { desc = "[N]PM [T]est" })
vim.keymap.set("n", "<leader>nr", "<cmd>! npm run ", { desc = "[N]PM [R]un" })
vim.keymap.set("n", "<leader>nrp", "<cmd>! npm run pytest<CR>", { desc = "[N]PM [R]un [P]ytest" })
--#endregion

--#region Python
vim.api.nvim_set_keymap("n", "<leader>pr", "<cmd>w<CR><cmd>!python %<CR>", { desc = "[P]ython [R]un Current File" })
vim.api.nvim_set_keymap("n", "<leader>pts", "<cmd>w<CR><cmd>!pytest<CR>", { desc = "[P][T]est [S]uite" })
vim.api.nvim_set_keymap("n", "<leader>ptk", "<cmd>w<CR><cmd>!pytest -k ", { desc = "[P][T]est [K]ey" })
--#endregion

--#region Autocomplete
vim.keymap.set("n", "<leader>ta", function()
	vim.g.toggle_cmp = not vim.g.toggle_cmp
	if vim.g.toggle_cmp then
		vim.notify("Toggled On", vim.log.levels.INFO, { title = "Autocomplete" })
	else
		vim.notify("Toggled Off", vim.log.levels.INFO, { title = "Autocomplete" })
	end
end, { desc = "[T]oggle [A]utocomplete" })
--#endregion

--#region Which-Key prefix mapping
local wk = require("which-key")
wk.add({
	{ "<leader>d", group = "Duck (just for fun)", mode = "n" },
	{ "<leader>f", group = "Find (LSP)" },
	{ "<leader>g", group = "Git" },
	{ "<leader>ga", group = "Git Add" },
	{ "<leader>gc", group = "Git Commit" },
	{ "<leader>n", group = "NPM" },
	{ "<leader>nr", group = "NPM Run" },
	{ "<leader>p", group = "Python" },
	{ "<leader>pt", group = "Pytest" },
	{ "<leader>note", group = "Note" },
	{ "<leader>r", group = "Replace/Rename" },
	{ "<leader>s", group = "Search" },
	{ "<leader>t", group = "Toggle Options" },
})
--#endregion
