import os
import queue
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


MODEL = "granite3.1-dense:latest"
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".log",
    ".md",
    ".json",
    ".conf",
    ".csv",
    ".xml",
    ".yaml",
}
SYSTEM_DIRECTIVES = """You are an expert data analyst, medical informatics auditor, and technical system engineer.
Your sole objective is to analyze the local reference data provided below and answer user queries with absolute factual precision.

=== CORE OPERATIONAL DIRECTIVES ===
1. STRICT GROUNDING: Rely EXCLUSIVELY on the data found between the tags. If an answer cannot be verified or derived directly from the provided text, state clearly: 'I cannot find that information in the current data load.' Do not invent facts or history.
2. FORMATTING RULES: When presenting multi-row data, inventory lists, metrics, or comparison points, format the output as a clean Markdown Table with clear headers. Use bold text for key identifiers or critical status levels.
3. CONCISE RESPONSES: Provide direct, punchy answers. Avoid conversational filler or long preambles.
4. MEDICAL/LOGISTICS CONTEXT: Treat Patient IDs, inventory numbers, and timestamps with extreme mathematical precision. If cross-referencing multiple files, explicitly link rows by shared ID keys.
5. NO RETROSPECTIVE LOGS: Focus ONLY on answering the user's immediate question. Do not summarize previous answers.

--- LOCAL GROUNDED DATA START ---
{grounding_data}
--- LOCAL GROUNDED DATA END ---

User Question: {question}
"""


def load_grounding_data(target_dir, days_limit):
    cutoff = None
    if days_limit:
        cutoff = datetime.now().timestamp() - timedelta(days=days_limit).total_seconds()

    files = sorted(
        path
        for path in target_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if cutoff is not None:
        files = [path for path in files if path.stat().st_mtime > cutoff]

    sections = []
    for path in files:
        try:
            content = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as error:
            raise OSError(f"Could not read {path}: {error}") from error
        sections.append(f"[SOURCE FILE: {path.name}]\n{content}")
    return "\n\n".join(sections), len(files)


class GraniteChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Granite 3.1 Grounded Chat")
        self.root.geometry("850x650")
        self.root.minsize(600, 450)
        self.target_dir = Path(__file__).resolve().parent / "Grounding Data"
        self.target_dir.mkdir(exist_ok=True)
        self.result_queue = queue.Queue()
        self.busy = False
        self.grounding_data = ""

        self.days_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self._build_ui()
        self.reload_data()
        self.root.after(100, self._process_results)

    def _build_ui(self):
        controls = ttk.Frame(self.root, padding=(12, 12, 12, 6))
        controls.pack(fill=tk.X)
        ttk.Label(controls, text="Load files modified in the last").pack(side=tk.LEFT)
        days_entry = ttk.Entry(controls, textvariable=self.days_var, width=8)
        days_entry.pack(side=tk.LEFT, padx=(6, 4))
        days_entry.bind("<Return>", lambda _event: self.reload_data())
        ttk.Label(controls, text="days (blank = all)").pack(side=tk.LEFT)
        self.reload_button = ttk.Button(
            controls, text="Reload data", command=self.reload_data
        )
        self.reload_button.pack(side=tk.RIGHT)

        self.chat = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state=tk.DISABLED, padx=10, pady=10
        )
        self.chat.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        input_frame = ttk.Frame(self.root, padding=(12, 6))
        input_frame.pack(fill=tk.X)
        self.question = tk.Text(input_frame, height=3, wrap=tk.WORD)
        self.question.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.question.bind("<Control-Return>", self._send_from_shortcut)
        self.send_button = ttk.Button(
            input_frame, text="Send", command=self.send_question
        )
        self.send_button.pack(side=tk.LEFT, padx=(8, 0), anchor=tk.S)

        ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor=tk.W,
            padding=(12, 4),
        ).pack(fill=tk.X)
        self._append_chat(
            "Granite",
            "Ask a question about the files loaded from your Grounding Data folder. "
            "Press Ctrl+Enter or click Send.",
        )

    def _append_chat(self, speaker, text):
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, f"{speaker}\n", "speaker")
        self.chat.insert(tk.END, f"{text}\n\n")
        self.chat.tag_configure("speaker", font=("TkDefaultFont", 10, "bold"))
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def reload_data(self):
        raw_days = self.days_var.get().strip()
        if raw_days:
            try:
                days_limit = int(raw_days)
            except ValueError:
                messagebox.showerror(
                    "Invalid day limit",
                    "Enter a whole number from 1 to 36500, or leave it blank.",
                )
                return
            if not 1 <= days_limit <= 36500:
                messagebox.showerror(
                    "Invalid day limit",
                    "Enter a whole number from 1 to 36500, or leave it blank.",
                )
                return
        else:
            days_limit = None

        try:
            data, count = load_grounding_data(self.target_dir, days_limit)
        except OSError as error:
            messagebox.showerror("Could not load data", str(error))
            return

        self.grounding_data = data
        limit_text = f"Last {days_limit} days" if days_limit else "All dates"
        self.status_var.set(
            f"{count} file(s) loaded from {self.target_dir} | {limit_text}"
        )

    def _send_from_shortcut(self, _event):
        self.send_question()
        return "break"

    def send_question(self):
        if self.busy:
            return
        question = self.question.get("1.0", tk.END).strip()
        if not question:
            return

        self.question.delete("1.0", tk.END)
        self._append_chat("You", question)
        self.busy = True
        self.send_button.configure(state=tk.DISABLED)
        self.reload_button.configure(state=tk.DISABLED)
        self.status_var.set("Waiting for Ollama...")
        prompt = SYSTEM_DIRECTIVES.format(
            grounding_data=self.grounding_data,
            question=question,
        )
        threading.Thread(
            target=self._run_model, args=(prompt,), daemon=True
        ).start()

    def _run_model(self, prompt):
        try:
            result = subprocess.run(
                ["ollama", "run", MODEL],
                input=prompt,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                ),
            )
            if result.returncode:
                detail = result.stderr.strip() or (
                    f"Ollama exited with code {result.returncode}."
                )
                self.result_queue.put(("error", detail))
            else:
                self.result_queue.put(("answer", result.stdout.strip()))
        except OSError as error:
            self.result_queue.put(
                (
                    "error",
                    "Could not start Ollama. Confirm it is installed and "
                    f"available on PATH.\n{error}",
                )
            )

    def _process_results(self):
        try:
            while True:
                result_type, content = self.result_queue.get_nowait()
                if result_type == "answer":
                    self._append_chat(
                        "Granite",
                        content or "(The model returned an empty response.)",
                    )
                    self.status_var.set("Ready")
                else:
                    self._append_chat("Error", content)
                    self.status_var.set("Ollama request failed")
                self.busy = False
                self.send_button.configure(state=tk.NORMAL)
                self.reload_button.configure(state=tk.NORMAL)
        except queue.Empty:
            pass
        self.root.after(100, self._process_results)


if __name__ == "__main__":
    root = tk.Tk()
    GraniteChatApp(root)
    root.mainloop()
