import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.colorchooser import askcolor
from PIL import Image, ImageTk
import random
import os

MAX_EMOJIS = 10
DEFAULT_ROWS = 20
DEFAULT_COLS = 20
CELL_SIZE = 25

emoji_palette = {
    0: (":white_square:", "#ffffff"),
    1: (":racoon_king:", "#cccccc"),
    2: (":party_raccoon:", "#ffaa55"),
}

class EmojiGridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Emoji Grid Painter")

        self.rows = DEFAULT_ROWS
        self.cols = DEFAULT_COLS
        self.cell_size = CELL_SIZE
        self.current_color = 1
        self.grid = []
        self.rects = {}
        self.canvas_images = {}  # Track image objects separately
        self.image_mode = False

        self.emoji_mappings = emoji_palette.copy()
        self.emoji_count = len(self.emoji_mappings)

        self.canvas = tk.Canvas(root, highlightthickness=0)
        self.canvas.pack()

        self.setup_settings_panel()
        self.setup_bindings()
        self.reset_grid(initialize=True)

        self.root.bind("<Button-1>", self.refocus_canvas, add="+")

    def setup_settings_panel(self):
        self.settings_frame = tk.Frame(self.root)
        self.settings_frame.pack()

        # --- Grid size controls ---
        grid_size_frame = tk.Frame(self.settings_frame)
        grid_size_frame.pack()
        tk.Label(grid_size_frame, text="Rows").pack(side="left")
        self.row_entry = tk.Entry(grid_size_frame, width=5)
        self.row_entry.insert(0, str(self.rows))
        self.row_entry.pack(side="left")
        tk.Label(grid_size_frame, text="Cols").pack(side="left")
        self.col_entry = tk.Entry(grid_size_frame, width=5)
        self.col_entry.insert(0, str(self.cols))
        self.col_entry.pack(side="left")
        tk.Button(grid_size_frame, text="Update Grid", command=self.update_grid_size).pack(side="left", padx=5)

        # --- Scrollable emoji mapping panel ---
        self.mapping_container = tk.Frame(self.settings_frame)
        self.mapping_container.pack()

        self.mapping_frame = tk.Frame(self.mapping_container)
        self.mapping_frame.pack(fill="x")

        self.scroll_canvas = tk.Canvas(self.mapping_frame, height=160, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.mapping_frame, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="x", expand=True)

        self.scroll_frame = tk.Frame(self.scroll_canvas)
        self.scroll_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        # Update scroll region dynamically
        self.scroll_frame.bind("<Configure>", lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))

        # Scroll with mouse wheel when hovered
        self.scroll_canvas.bind("<Enter>", lambda e: self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.scroll_canvas.bind("<Leave>", lambda e: self.scroll_canvas.unbind_all("<MouseWheel>"))

        # --- Build and adjust emoji panel ---
        self.emoji_entries = {}
        self.emoji_frames = {}
        self.build_emoji_entries()

        # --- Buttons ---
        button_frame = tk.Frame(self.settings_frame)
        button_frame.pack()
        tk.Button(button_frame, text="Add Emoji", command=self.add_emoji).pack(side="left", padx=2)
        tk.Button(button_frame, text="Add Image", command=self.add_image).pack(side="left", padx=2)
        tk.Button(button_frame, text="Export", command=self.export).pack(side="left", padx=2)
        tk.Button(button_frame, text="Save", command=self.save).pack(side="left", padx=2)
        tk.Button(button_frame, text="Load", command=self.load).pack(side="left", padx=2)

        # --- Export confirmation message ---
        self.export_msg = tk.Label(self.settings_frame, text="", fg="green")
        self.export_msg.pack()

        tk.Label(self.settings_frame, text="Press 0-9 to select emoji index.").pack()

    def _on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_emoji_entries(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.emoji_entries = {}
        self.emoji_frames = {}
        for i in range(self.emoji_count):
            row = tk.Frame(self.scroll_frame, bd=2, relief="solid")
            row.pack(anchor="w", pady=1, padx=2, fill="x")
            self.emoji_frames[i] = row

            tk.Label(row, text=f"{i}").pack(side="left")
            emoji = tk.Entry(row, width=15)
            emoji.insert(0, self.emoji_mappings.get(i, (":white_square:", "#ffffff"))[0])
            emoji.pack(side="left")

            #color_hex = self.emoji_mappings.get(i, (":white_square:", "#ffffff"))[1]
            #color_box = tk.Label(row, bg=color_hex, width=3, relief="raised")
            #color_box.pack(side="left", padx=5)

            value = self.emoji_mappings.get(i, (":white_square:", "#ffffff"))[1]
            if isinstance(value, str) and value.startswith("#"):
                color_box = tk.Label(row, bg=value, width=3, relief="raised")
            else:
                color_box = tk.Label(row, image=value, width=25, height=25, relief="raised")
                color_box.image = value  # Keep a reference so it doesn't get garbage collected
            color_box.pack(side="left", padx=5)

            def choose_color_or_image(i=i, color_box=color_box):
                current = self.emoji_mappings[i][1]
                if isinstance(current, str) and current.startswith("#"):
                    # It's a color — show color picker
                    result = askcolor(title="Choose Color", initialcolor=current)
                    if result[1]:
                        self.emoji_mappings[i] = (self.emoji_entries[i][0].get(), result[1])
                        color_box.config(bg=result[1])
                        self.refresh_grid_colors()
                else:
                    # It's an image — let user pick a new image
                    path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
                    if path:
                        from PIL import Image, ImageTk
                        img = Image.open(path)
                        size = CELL_SIZE
                        img = img.resize((size, size), Image.Resampling.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                        self.emoji_mappings[i] = (self.emoji_entries[i][0].get(), tk_img)
                        color_box.config(image=tk_img)
                        color_box.image = tk_img
                        self.refresh_grid_colors()

            color_box.bind("<Button-1>", lambda e, i=i: choose_color_or_image(i))

            remove_btn = tk.Button(row, text="-", command=lambda i=i: self.remove_emoji(i))
            remove_btn.pack(side="left")

            self.emoji_entries[i] = (emoji, color_box)
        self.update_selection_highlight()

        # Resize scroll_canvas based on content:
        visible_rows = min(self.emoji_count, 5)
        row_height = 35  # Approx height per row (adjust as needed)
        new_height = visible_rows * row_height
        self.scroll_canvas.config(height=new_height)

    def update_selection_highlight(self):
        for i, frame in self.emoji_frames.items():
            if i == self.current_color:
                frame.config(highlightbackground="lightgray", highlightthickness=1, relief="flat")
            else:
                frame.config(highlightthickness=0, relief="flat")

    def add_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if not path:
            return
        img = Image.open(path)
        img = self.prepare_image(img)
        tk_img = ImageTk.PhotoImage(img)
        self.emoji_mappings[self.emoji_count] = (os.path.basename(path), tk_img)
        self.emoji_count += 1
        self.build_emoji_entries()
        self.canvas.focus_set()

    def prepare_image(self, img):
        size = self.cell_size
        img = img.resize((size, size), Image.LANCZOS)
        return img

    def remove_emoji(self, index):
        if index == 0:
            messagebox.showinfo("Cannot remove", "Cannot remove the default emoji.")
            return

        # Step 1: Clear the index from the grid
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == index:
                    self.grid[r][c] = 0
                elif self.grid[r][c] > index:
                    self.grid[r][c] -= 1

        # Step 2: Delete the mapping and re-index
        del self.emoji_mappings[index]
        self.emoji_mappings = {
            new_i: self.emoji_mappings[old_i]
            for new_i, old_i in enumerate(sorted(self.emoji_mappings))
        }
        self.emoji_count = len(self.emoji_mappings)

        # Step 3: Rebuild UI and grid visuals
        self.build_emoji_entries()
        self.refresh_grid_colors()

    def add_emoji(self):
        if self.emoji_count >= MAX_EMOJIS:
            messagebox.showinfo("Limit reached", f"Maximum of {MAX_EMOJIS} emojis allowed.")
            return
        pastel_color = self.random_pastel_color()
        self.emoji_mappings[self.emoji_count] = (":new:", pastel_color)
        self.emoji_count += 1
        self.build_emoji_entries()
        self.canvas.focus_set()

    def random_pastel_color(self):
        r = lambda: random.randint(100, 255)
        return f'#{r():02x}{r():02x}{r():02x}'

    def update_palette(self):
        changed = False
        for i, (emoji_entry, color_box) in self.emoji_entries.items():
            emoji_val = emoji_entry.get().strip()
            color_val = color_box["bg"]
            if isinstance(self.emoji_mappings[i][1], str) and self.emoji_mappings[i] != (emoji_val, color_val):
                self.emoji_mappings[i] = (emoji_val, color_val)
                changed = True
        if changed:
            self.refresh_grid_colors()

    def refresh_grid_colors(self):
        for r in range(self.rows):
            for c in range(self.cols):
                idx = self.grid[r][c]
                fill = self.emoji_mappings.get(idx, (":?", "black"))[1]

                # Remove previous image if it exists
                if (r, c) in self.canvas_images:
                    self.canvas.delete(self.canvas_images[(r, c)])
                    del self.canvas_images[(r, c)]

                if isinstance(fill, str):
                    self.canvas.itemconfig(self.rects[(r, c)], fill=fill)
                else:
                    self.canvas.itemconfig(self.rects[(r, c)], fill="white")
                    img_id = self.canvas.create_image(c * self.cell_size, r * self.cell_size, anchor="nw", image=fill)
                    self.canvas_images[(r, c)] = img_id

    def update_grid_size(self):
        try:
            new_rows = int(self.row_entry.get())
            new_cols = int(self.col_entry.get())
            if new_rows <= 0 or new_cols <= 0:
                raise ValueError
            self.rows = new_rows
            self.cols = new_cols
            self.reset_grid()
            self.canvas.focus_set()
        except ValueError:
            messagebox.showerror("Invalid input", "Grid size must be positive integers.")

    def reset_grid(self, initialize=False):
        old = self.grid if not initialize else []
        self.grid = [[old[r][c] if r < len(old) and c < len(old[0]) else 0 for c in range(self.cols)] for r in range(self.rows)]
        self.canvas.config(width=self.cols * self.cell_size, height=self.rows * self.cell_size)
        self.canvas.delete("all")
        self.rects.clear()
        self.canvas_images.clear()  # Clear image references
        for r in range(self.rows):
            for c in range(self.cols):
                x1, y1 = c * self.cell_size, r * self.cell_size
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size
                color = self.emoji_mappings.get(self.grid[r][c], (":?", "black"))[1]
                if isinstance(color, str):
                    rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="gray")
                else:
                    rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="gray")
                    self.canvas.create_image(x1, y1, anchor="nw", image=color)
                self.rects[(r, c)] = rect

    def setup_bindings(self):
        self.canvas.bind("<Button-1>", self.paint_at)
        self.canvas.bind("<B1-Motion>", self.paint_at)
        self.root.bind("<Key>", self.handle_keypress)

    def refocus_canvas(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if not isinstance(widget, tk.Entry):
            self.canvas.focus_set()

    def paint_at(self, event):
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row][col] = self.current_color

            # Remove existing image if present
            if (row, col) in self.canvas_images:
                self.canvas.delete(self.canvas_images[(row, col)])
                del self.canvas_images[(row, col)]

            color = self.emoji_mappings.get(self.current_color, (":?", "black"))[1]
            if isinstance(color, str):
                self.canvas.itemconfig(self.rects[(row, col)], fill=color)
            else:
                self.canvas.itemconfig(self.rects[(row, col)], fill="white")
                img_id = self.canvas.create_image(col * self.cell_size, row * self.cell_size, anchor="nw", image=color)
                self.canvas_images[(row, col)] = img_id

    def handle_keypress(self, event):
        if isinstance(self.root.focus_get(), tk.Entry):
            return
        if event.char.isdigit():
            idx = int(event.char)
            if idx < self.emoji_count:
                self.current_color = idx
                self.update_selection_highlight()

    def export(self):
        self.update_palette()
        output = "\n".join("".join(self.emoji_mappings[cell][0] for cell in row) for row in self.grid)
        self.root.clipboard_clear()
        self.root.clipboard_append(output)
        self.export_msg.config(text="Copied to clipboard!")
        self.root.after(2000, lambda: self.export_msg.config(text=""))

    def save(self):
        self.update_palette()
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w") as f:
                for row in self.grid:
                    f.write("".join(self.emoji_mappings[cell][0] for cell in row) + "\n")

    def load(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        with open(path, "r") as f:
            lines = [line.strip() for line in f.readlines()]
        self.rows = len(lines)
        self.cols = max(len(line.split(":")) // 2 for line in lines)
        self.row_entry.delete(0, tk.END)
        self.col_entry.delete(0, tk.END)
        self.row_entry.insert(0, str(self.rows))
        self.col_entry.insert(0, str(self.cols))
        self.reset_grid()
        for r, line in enumerate(lines):
            parts = [":" + p + ":" for p in line.split(":") if p]
            for c, part in enumerate(parts):
                for idx, (emoji, _) in self.emoji_mappings.items():
                    if part == emoji:
                        self.grid[r][c] = idx
                        #self.paint_at(tk.Event())
                        break
        self.refresh_grid_colors()

if __name__ == "__main__":
    root = tk.Tk()
    app = EmojiGridApp(root)
    root.mainloop()
