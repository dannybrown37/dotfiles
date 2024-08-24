local M = {}

function M.CreateNote()
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

return M
