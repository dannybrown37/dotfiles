return -- LSP Configuration & Plugins
{
	"neovim/nvim-lspconfig",
	dependencies = {
		{ "williamboman/mason.nvim", config = true }, -- WARNING: Must be loaded before dependents
		"williamboman/mason-lspconfig.nvim",
		"WhoIsSethDaniel/mason-tool-installer.nvim",
		{ "j-hui/fidget.nvim", opts = {} },
		{ "folke/neodev.nvim", opts = {} },
		"jose-elias-alvarez/null-ls.nvim",
	},

	config = function() --  This function gets run when an LSP attaches to a particular buffer.
		vim.api.nvim_create_autocmd("LspAttach", {
			group = vim.api.nvim_create_augroup("kickstart-lsp-attach", { clear = true }),
			callback = function(event)
				local map = function(keys, func, desc)
					vim.keymap.set("n", keys, func, { buffer = event.buf, desc = desc .. " (word under cursor: LSP)" })
				end

				local tele = require("telescope.builtin")

				map("<leader>gd", tele.lsp_definitions, "[G]oto [D]efinition")
				map("<leader>gr", tele.lsp_references, "[G]oto [R]eferences")
				map("<leader>gI", tele.lsp_implementations, "[G]oto [I]mplementation")
				map("<leader>gt", tele.lsp_type_definitions, "[G]oto [T]ype Definition")
				map("<leader>gD", vim.lsp.buf.declaration, "[G]oto [D]eclaration (i.e. import)")

				map("<leader>sd", tele.lsp_document_symbols, "[S]earch [D]ocument Symbols")
				map("<leader>sp", tele.lsp_dynamic_workspace_symbols, "[S]earch [P]roject Symbols")
				map("<leader>rs", vim.lsp.buf.rename, "[R]ename [S]ymbol")
				map("<leader>a", vim.lsp.buf.code_action, "Code [A]ction (try with cursor on top of error)")
				map("D", vim.lsp.buf.hover, "Hover [D]ocumentation")

				-- When you move your cursor, the highlights will be cleared (the second autocommand).
				--    See `:help CursorHold` for information about when this is executed
				local client = vim.lsp.get_client_by_id(event.data.client_id)
				if client and client.server_capabilities.documentHighlightProvider then
					local highlight_augroup = vim.api.nvim_create_augroup("kickstart-lsp-highlight", { clear = false })
					vim.api.nvim_create_autocmd({ "CursorHold", "CursorHoldI" }, {
						buffer = event.buf,
						group = highlight_augroup,
						callback = vim.lsp.buf.document_highlight,
					})

					vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
						buffer = event.buf,
						group = highlight_augroup,
						callback = vim.lsp.buf.clear_references,
					})

					vim.api.nvim_create_autocmd("LspDetach", {
						group = vim.api.nvim_create_augroup("kickstart-lsp-detach", { clear = true }),
						callback = function(event2)
							vim.lsp.buf.clear_references()
							vim.api.nvim_clear_autocmds({ group = "kickstart-lsp-highlight", buffer = event2.buf })
						end,
					})
				end

				-- The following autocommand is used to enable inlay hints in your
				-- code, if the language server you are using supports them
				-- This may be unwanted, since they displace some of your code
				if client and client.server_capabilities.inlayHintProvider and vim.lsp.inlay_hint then
					map("<leader>th", function()
						vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled({}))
					end, "[T]oggle Inlay [H]ints")
				end
			end,
		})

		-- LSP servers and clients are able to communicate to each other what features they support.
		--  By default, Neovim doesn't support everything that is in the LSP specification.
		--  When you add nvim-cmp, luasnip, etc. Neovim now has *more* capabilities.
		--  So, we create new capabilities with nvim cmp, and then broadcast that to the servers.
		local capabilities = vim.lsp.protocol.make_client_capabilities()
		capabilities = vim.tbl_deep_extend("force", capabilities, require("cmp_nvim_lsp").default_capabilities())

		require("lspconfig").pyright.setup({
			capabilities = (function()
				local capabilities_pr = vim.lsp.protocol.make_client_capabilities()
				capabilities_pr.textDocument.publishDiagnostics.tagSupport.valueSet = { 2 }
				return capabilities_pr
			end)(),
		})
		require("lspconfig").taplo.setup({ capabilities = capabilities })
		require("lspconfig").ruff_lsp.setup({ capabilities = capabilities })

		local servers = {
			pyright = {},
			tsserver = {},
			lua_ls = {
				settings = {
					Lua = {
						completion = {
							callSnippet = "Replace",
						},
					},
				},
			},
		}

		require("mason").setup()
		local ensure_installed = vim.tbl_keys(servers or {})
		vim.list_extend(ensure_installed, {
			"stylua", -- lua styler
			"pyright", -- LSP for Python
			"ruff-lsp", -- Python linter
			"taplo", -- LSP for toml
			"shfmt",
			"shellcheck",
			"eslint-lsp",
			"prettier",
		})

		local null_ls = require("null-ls")

		null_ls.setup({
			sources = {
				null_ls.builtins.formatting.prettier.with({
					filetypes = { "html", "css", "javascript", "typescript", "json", "yaml", "markdown" },
				}),
			},
		})

		require("mason-tool-installer").setup({ ensure_installed = ensure_installed })

		require("mason-lspconfig").setup({
			handlers = {
				function(server_name)
					local server = servers[server_name] or {}
					server.capabilities = vim.tbl_deep_extend("force", {}, capabilities, server.capabilities or {})
					require("lspconfig")[server_name].setup(server)
				end,
			},
		})
	end,
}
