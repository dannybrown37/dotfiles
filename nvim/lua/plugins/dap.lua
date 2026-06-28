return {
	"mfussenegger/nvim-dap",
	dependencies = {
		"rcarriga/nvim-dap-ui",
		"nvim-neotest/nvim-nio",
		"williamboman/mason.nvim",
		"jay-babu/mason-nvim-dap.nvim",
		"mfussenegger/nvim-dap-python",
		"leoluz/nvim-dap-go",
	},

	keys = {
		{ "<leader>dc", desc = "[D]ebug: [C]ontinue / Start" },
		{ "<leader>di", desc = "[D]ebug: Step [I]nto" },
		{ "<leader>do", desc = "[D]ebug: Step [O]ver" },
		{ "<leader>dO", desc = "[D]ebug: Step Out" },
		{ "<leader>db", desc = "[D]ebug: Toggle [B]reakpoint" },
		{ "<leader>dB", desc = "[D]ebug: Conditional [B]reakpoint" },
		{ "<leader>dl", desc = "[D]ebug: Run [L]ast" },
		{ "<leader>dt", desc = "[D]ebug: [T]erminate" },
		{ "<leader>du", desc = "[D]ebug: Toggle [U]I" },
	},

	config = function()
		local dap = require("dap")
		local dapui = require("dapui")

		require("mason-nvim-dap").setup({
			automatic_installation = true,
			ensure_installed = { "debugpy", "delve", "js-debug-adapter" },
		})

		dapui.setup({
			icons = { expanded = "▾", collapsed = "▸", current_frame = "*" },
			controls = { icons = { pause = "⏸", play = "▶", step_into = "⏎", step_over = "⏭", step_out = "⏮", step_back = "b", run_last = "▶▶", terminate = "⏹", disconnect = "⏏" } },
		})

		-- Python (uses debugpy)
		require("dap-python").setup(vim.fn.stdpath("data") .. "/mason/packages/debugpy/venv/bin/python")
		require("dap-python").test_runner = "pytest"

		-- Go (uses delve)
		require("dap-go").setup()

		-- Node/TypeScript (uses js-debug-adapter)
		dap.adapters["pwa-node"] = {
			type = "server",
			host = "localhost",
			port = "${port}",
			executable = {
				command = vim.fn.stdpath("data") .. "/mason/packages/js-debug-adapter/js-debug-adapter",
				args = { "${port}" },
			},
		}
		for _, lang in ipairs({ "javascript", "typescript" }) do
			dap.configurations[lang] = {
				{
					type = "pwa-node",
					request = "launch",
					name = "Launch file",
					program = "${file}",
					cwd = "${workspaceFolder}",
				},
				{
					type = "pwa-node",
					request = "attach",
					name = "Attach to process",
					processId = require("dap.utils").pick_process,
					cwd = "${workspaceFolder}",
				},
			}
		end

		-- Keymaps
		vim.keymap.set("n", "<leader>dc", dap.continue, { desc = "[D]ebug: [C]ontinue / Start" })
		vim.keymap.set("n", "<leader>di", dap.step_into, { desc = "[D]ebug: Step [I]nto" })
		vim.keymap.set("n", "<leader>do", dap.step_over, { desc = "[D]ebug: Step [O]ver" })
		vim.keymap.set("n", "<leader>dO", dap.step_out, { desc = "[D]ebug: Step Out" })
		vim.keymap.set("n", "<leader>db", dap.toggle_breakpoint, { desc = "[D]ebug: Toggle [B]reakpoint" })
		vim.keymap.set("n", "<leader>dB", function()
			dap.set_breakpoint(vim.fn.input("Breakpoint condition: "))
		end, { desc = "[D]ebug: Conditional [B]reakpoint" })
		vim.keymap.set("n", "<leader>dl", dap.run_last, { desc = "[D]ebug: Run [L]ast" })
		vim.keymap.set("n", "<leader>dt", dap.terminate, { desc = "[D]ebug: [T]erminate" })
		vim.keymap.set("n", "<leader>du", dapui.toggle, { desc = "[D]ebug: Toggle [U]I" })

		-- Auto open/close UI on debug sessions
		dap.listeners.after.event_initialized["dapui_config"] = dapui.open
		dap.listeners.before.event_terminated["dapui_config"] = dapui.close
		dap.listeners.before.event_exited["dapui_config"] = dapui.close
	end,
}
