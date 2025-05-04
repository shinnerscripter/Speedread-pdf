import tkinter as tk
from tkinter import filedialog, ttk
import fitz  # PyMuPDF
import time
import os
import json

class PDFReader:
    def __init__(self, root):
        self.root = root
        self.root.title("Leitor Dinâmico de PDF")
        
        self.filename = ""
        self.words = []
        self.index = 0
        self.running = False
        self.paused = False
        self.delay = 1.0

        self.save_folder = "progressos"
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)

        self.setup_ui()
        self.setup_keyboard_bindings()

    def setup_ui(self):
        self.select_button = tk.Button(self.root, text="Escolher PDF", command=self.open_pdf)
        self.select_button.pack(pady=5)

        self.wpm_label = tk.Label(self.root, text="Palavras por minuto:")
        self.wpm_label.pack()

        self.wpm_entry = tk.Entry(self.root)
        self.wpm_entry.insert(0, "50")
        self.wpm_entry.pack(pady=5)

        self.theme_label = tk.Label(self.root, text="Tema de cores:")
        self.theme_label.pack()

        self.theme_var = tk.StringVar()
        self.theme_menu = ttk.Combobox(self.root, textvariable=self.theme_var, state="readonly")
        self.theme_menu['values'] = [
            "Branco no Preto", "Preto no Branco", "Preto no Amarelo",
            "Amarelo no Azul", "Verde no Preto"
        ]
        self.theme_menu.current(0)
        self.theme_menu.pack(pady=5)

        self.controls_frame = tk.Frame(self.root, bg=self.root["bg"])
        self.controls_frame.pack(pady=5)

        self.start_button = tk.Button(self.controls_frame, text="Iniciar", command=self.start)
        self.start_button.pack(side="left", padx=5)

        self.continue_button = tk.Button(self.controls_frame, text="Continuar", command=self.resume)
        self.continue_button.pack(side="left", padx=5)

        self.pause_button = tk.Button(self.controls_frame, text="Parar", command=self.pause)
        self.pause_button.pack(side="left", padx=5)

        self.back_button = tk.Button(self.controls_frame, text="Voltar 5", command=self.go_back)
        self.back_button.pack(side="left", padx=5)

        self.goto_frame = tk.Frame(self.root)
        self.goto_frame.pack(pady=5)

        self.goto_label = tk.Label(self.goto_frame, text="Ir para palavra número:")
        self.goto_label.pack(side="left")

        self.goto_entry = tk.Entry(self.goto_frame, width=10)
        self.goto_entry.pack(side="left", padx=5)

        self.goto_button = tk.Button(self.goto_frame, text="Ir", command=self.goto_word)
        self.goto_button.pack(side="left")

        self.text_widget = tk.Text(self.root, height=7, wrap="word")
        self.text_widget.pack(pady=10)
        self.text_widget.config(state="disabled")

        self.word_label = tk.Label(self.root, text="", font=("Arial", 36))
        self.word_label.pack(pady=10)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        self.counter_label = tk.Label(self.root, text="Palavras lidas: 0 de 0")
        self.counter_label.pack(pady=5)

        self.update_theme()
        self.theme_var.trace_add("write", lambda *args: self.update_theme())

    def setup_keyboard_bindings(self):
        self.root.bind("<space>", lambda event: self.toggle_pause())
        self.root.bind("<Left>", lambda event: self.go_back())
        self.root.bind("<Right>", lambda event: self.increase_speed_temporarily())
        self.root.bind("<Up>", lambda event: self.increase_speed())
        self.root.bind("<Down>", lambda event: self.decrease_speed())
        self.root.bind("<Home>", lambda event: self.go_to_start())
        self.root.bind("<End>", lambda event: self.go_to_end())
        self.root.bind("<Return>", lambda event: self.start())
        self.root.bind("r", lambda event: self.resume())
        self.root.bind("s", lambda event: self.save_progress())

    def open_pdf(self):
        filepath = filedialog.askopenfilename(filetypes=[("Arquivos PDF", "*.pdf")])
        if filepath:
            self.filename = filepath
            self.load_pdf()

    def load_pdf(self):
        doc = fitz.open(self.filename)
        text = ""
        for page in doc:
            text += page.get_text()
        self.words = text.split()
        self.index = 0
        self.load_progress()
        self.update_display()

    def save_progress(self):
        if self.filename:
            save_path = os.path.join(self.save_folder, os.path.basename(self.filename) + ".json")
            with open(save_path, "w") as f:
                json.dump({"index": self.index}, f)

    def load_progress(self):
        save_path = os.path.join(self.save_folder, os.path.basename(self.filename) + ".json")
        if os.path.exists(save_path):
            with open(save_path, "r") as f:
                data = json.load(f)
                self.index = data.get("index", 0)

    def start(self):
        try:
            wpm = int(self.wpm_entry.get())
            self.delay = 60.0 / wpm
        except ValueError:
            self.delay = 1.0

        self.running = True
        self.paused = False
        self.display_snippet()
        self.root.after(100, self.update_word)

    def resume(self):
        if not self.running and self.paused:
            self.running = True
            self.paused = False
            self.root.after(100, self.update_word)

    def pause(self):
        self.running = False
        self.paused = True
        self.save_progress()

    def toggle_pause(self):
        if self.running:
            self.pause()
        elif self.paused:
            self.resume()

    def go_back(self):
        self.index = max(0, self.index - 5)
        self.display_snippet()
        self.highlight_word_in_snippet()
        self.update_word_label()
        self.update_progress()

    def goto_word(self):
        try:
            new_index = int(self.goto_entry.get())
            if 0 <= new_index < len(self.words):
                self.index = new_index
                self.display_snippet()
                self.highlight_word_in_snippet()
                self.update_word_label()
                self.update_progress()
                self.save_progress()
        except ValueError:
            pass

    def update_word(self):
        if self.running and self.index < len(self.words):
            current_word = self.words[self.index]
            self.update_display()
            self.index += 1
            self.save_progress()

            # Delay dinâmico baseado no comprimento e pontuação
            adjusted_delay = self.delay
            if len(current_word) > 3:
                adjusted_delay *= 1 + 0.05 * (len(current_word) - 3)
            if current_word[-1] in ".,!?;:":
                adjusted_delay *= 1.5

            self.root.after(int(adjusted_delay * 1000), self.update_word)
        elif self.index >= len(self.words):
            self.running = False
            self.paused = True

    def update_display(self):
        if self.index >= len(self.words):
            return

        current_word = self.words[self.index]
        self.word_label.config(text=current_word)
        self.display_snippet()
        self.highlight_word_in_snippet()
        self.update_progress()

    def update_progress(self):
        if self.words:
            progress_value = (self.index / len(self.words)) * 100
            self.progress['value'] = progress_value
            self.counter_label.config(text=f"Palavras lidas: {self.index} de {len(self.words)}")

    def display_snippet(self):
        self.text_widget.config(state="normal")
        self.text_widget.delete(1.0, "end")

        window_size = 20
        start = max(0, self.index - window_size)
        end = min(len(self.words), self.index + window_size)

        self.snippet_words = self.words[start:end]
        self.snippet_text = ' '.join(self.snippet_words)

        self.snippet_start_index = start
        self.text_widget.insert("end", self.snippet_text)
        self.text_widget.config(state="disabled")

    def highlight_word_in_snippet(self):
        self.text_widget.config(state="normal")
        self.text_widget.tag_remove("highlight", "1.0", "end")

        if 0 <= self.index - self.snippet_start_index < len(self.words):
            word_in_snippet = self.words[self.index]
            start_idx = self.snippet_text.lower().find(word_in_snippet.lower())
            if start_idx != -1:
                start = f"1.0 + {start_idx} chars"
                end = f"1.0 + {start_idx + len(word_in_snippet)} chars"
                self.text_widget.tag_add("highlight", start, end)
                self.text_widget.tag_config("highlight", underline=1)
                self.text_widget.see(start)

        self.text_widget.config(state="disabled")

    def update_word_label(self):
        if self.index < len(self.words):
            self.word_label.config(text=self.words[self.index])

    def update_theme(self):
        themes = {
            "Branco no Preto": ("white", "black"),
            "Preto no Branco": ("black", "white"),
            "Preto no Amarelo": ("black", "yellow"),
            "Amarelo no Azul": ("yellow", "blue"),
            "Verde no Preto": ("lime", "black")
        }
        theme = self.theme_var.get()
        fg, bg = themes.get(theme, ("white", "black"))

        self.word_label.config(fg=fg, bg=bg)
        self.root.config(bg=bg)
        self.text_widget.config(bg=bg, fg=fg, insertbackground=fg)
        self.wpm_label.config(bg=bg, fg=fg)
        self.theme_label.config(bg=bg, fg=fg)
        self.start_button.config(bg=bg, fg=fg)
        self.continue_button.config(bg=bg, fg=fg)
        self.back_button.config(bg=bg, fg=fg)
        self.pause_button.config(bg=bg, fg=fg)
        self.select_button.config(bg=bg, fg=fg)
        self.goto_label.config(bg=bg, fg=fg)
        self.goto_button.config(bg=bg, fg=fg)
        self.counter_label.config(bg=bg, fg=fg)
        self.controls_frame.config(bg=bg)
        self.goto_frame.config(bg=bg)
        self.goto_entry.config(bg="white" if bg != "white" else "black", fg="black" if bg != "white" else "white")

    def increase_speed_temporarily(self):
        self.delay *= 0.5

    def increase_speed(self):
        try:
            wpm = int(self.wpm_entry.get())
            wpm = min(1000, wpm + 10)
            self.wpm_entry.delete(0, tk.END)
            self.wpm_entry.insert(0, str(wpm))
            self.delay = 60.0 / wpm
        except ValueError:
            pass

    def decrease_speed(self):
        try:
            wpm = int(self.wpm_entry.get())
            wpm = max(10, wpm - 10)
            self.wpm_entry.delete(0, tk.END)
            self.wpm_entry.insert(0, str(wpm))
            self.delay = 60.0 / wpm
        except ValueError:
            pass

    def go_to_start(self):
        self.index = 0
        self.update_display()
        self.update_word_label()
        self.display_snippet()
        self.update_progress()

    def go_to_end(self):
        self.index = len(self.words) - 1
        self.update_display()
        self.update_word_label()
        self.display_snippet()
        self.update_progress()

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFReader(root)
    root.mainloop()
