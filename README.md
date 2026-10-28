# Granite Chat App

Chat with the local Granite 3.1 model in a desktop window, grounded in files from
the `Grounding Data` folder.

## Setup

1. Run `install.bat` to check Python and Tkinter, install Ollama if needed, and
   download the Granite model.
2. Add supported reference files to `Grounding Data`.
3. Launch the app from the desktop shortcut or run `run_app.bat`.

The GUI uses Python's built-in Tkinter library and does not require additional
Python packages. Enter a number of days to limit files by their last-modified
date, or leave it blank to load all supported files. Click **Reload data** after
changing the filter or updating the files.

Supported file extensions: `.txt`, `.log`, `.md`, `.json`, `.conf`, `.csv`,
`.xml`, and `.yaml`.
