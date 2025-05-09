import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.colorchooser import askcolor
from PIL import Image, ImageTk
import random
import os

#from TooltipHelper import SLACK_EMOJI_HELP_TEXT, SLACK_EMOJI_CODE

import json
from io import BytesIO
import urllib.request
import re

import webbrowser
import urllib.request

__version__ = "v0.1.0-beta"

# TODO: add a better update system, possibly one that updates the app for you?
def check_for_update():
    try:
        remote_url = "https://raw.githubusercontent.com/Slowlor1ss/SlackPaint/main/version.txt"
        with urllib.request.urlopen(remote_url, timeout=5) as response:
            latest_version = response.read().decode().strip()
        if latest_version != __version__:
            answer = messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available. Visit GitHub to download?")
            if answer:
                webbrowser.open("https://github.com/Slowlor1ss/SlackPaint/releases")
    except Exception as e:
        print("Version check failed:", e)

MAX_EMOJIS = 10
DEFAULT_ROWS = 20
DEFAULT_COLS = 20
CELL_SIZE = 25

emoji_palette = {
    0: (":_:", "#ffffff"),
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
        # Track which emojis were added from Slack
        self.slack_emoji_indices = set()

        self.slack_emojis = None  # To store the loaded Slack emoji mapping

        self.canvas = tk.Canvas(root, highlightthickness=0)
        self.canvas.pack()

        self.active_button = None

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
        tk.Button(grid_size_frame, text="Clear Grid", command=self.confirm_reset_grid).pack(side="left", padx=5)

        # --- Scrollable emoji mapping panel ---
        self.mapping_container = tk.Frame(self.settings_frame)
        self.mapping_container.pack()

        self.mapping_frame = tk.Frame(self.mapping_container)
        self.mapping_frame.pack(fill="x")

        self.scroll_canvas = tk.Canvas(self.mapping_frame, width=450, height=160, borderwidth=0, highlightthickness=0)
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
        # tk.Button(button_frame, text="Add Slack Emoji", command=self.add_slack_emoji).pack(side="left", padx=2)

        # Create a frame for the Slack button and its help icon
        slack_frame = tk.Frame(button_frame)
        slack_frame.pack(side="left", padx=2)
        
        slack_button = tk.Button(slack_frame, text="Add Slack Emoji", command=self.add_slack_emoji)
        slack_button.pack(side="left")

        # Add help icon
        help_icon = tk.Label(slack_frame, text="?", font=("Arial", 8), 
                            bg="#4a7a8c", fg="white", width=1, height=1,
                            relief="raised", cursor="question_arrow")
        help_icon.pack(side="left", padx=1)

        # Add tooltip to the help icon
        # slack_help_text = ("To use Slack emojis, you need to export them as a JSON file.\n\n"
        #                 "1. Visit your Slack workspace in a browser\n"
        #                 "   https://YourworkspaceName.slack.com/customize/emoji\n"
        #                 "2. Open DevTools (F12 or Ctrl+Shift+I)\n"
        #                 "3. In the Console tab, paste the code\n"
        #                 "   (Code gets copied when clicking this question mark)\n"
        #                 "4. Copy the output and save it as a .json file\n"
        #                 "5. Use this file when clicking 'Add Slack Emoji'")
        
        # Function to copy code to clipboard and show a message
        def copy_code_to_clipboard():
            answer = messagebox.askyesno("Redirection", f"This will Redirect you to the github page from where you can copy said neccecary code to make the JSON of app slack emojis")
            if answer:
                webbrowser.open("https://github.com/Slowlor1ss/SlackPaint/blob/main/ScriptToGetSlackEmojis.js")
            #code_to_copy = SLACK_EMOJI_CODE
            #self.root.clipboard_clear()
            #self.root.clipboard_append(code_to_copy)
            #messagebox.showinfo("Code Copied", "The Slack emoji fetch code has been copied to your clipboard!")
            
        # Add clipboard functionality to the help icon
        help_icon.bind("<Button-1>", lambda e: copy_code_to_clipboard())
        
        help_text = ("To use Slack emojis, you need to export them as a JSON file.\n\n"
                        "1. Visit your Slack workspace in a browser\n"
                        "   https://YourworkspaceName.slack.com/customize/emoji\n"
                        "2. Open DevTools (F12 or Ctrl+Shift+I)\n"
                        "3. In the Console tab, paste the code\n"
                        "   (You can copy the code from the github page clicking the question mark will redirect you)\n"
                        "4. Save the output file\n"
                        "5. Use this file when clicking 'Add Slack Emoji'")
        self.create_tooltip(help_icon, help_text)

        button_frame2 = tk.Frame(self.settings_frame)
        button_frame2.pack()
        tk.Button(button_frame2, text="Export", command=self.export).pack(side="left", padx=2)
        tk.Button(button_frame2, text="Save", command=self.save).pack(side="left", padx=2)
        tk.Button(button_frame2, text="Load", command=self.load).pack(side="left", padx=2)

        # --- Export confirmation message ---
        self.export_msg = tk.Label(self.settings_frame, text="", fg="green")
        self.export_msg.pack()

        tk.Label(self.settings_frame, text="Use left mouse to draw right to remove (idx 0).").pack()
        tk.Label(self.settings_frame, text="Press 0-9 to select emoji index.").pack()

    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(tip, text=text, justify=tk.LEFT,
                            background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                            padx=6, pady=3, wraplength=350)
            label.pack()
            
            widget._tooltip = tip
            
        def leave(event):
            if hasattr(widget, "_tooltip"):
                widget._tooltip.destroy()
                del widget._tooltip
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    # There's probably a way better way of doing this lol
    def confirm_reset_grid(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the entire grid?"):
            self.reset_grid(initialize=True)

    def _on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_emoji_entries(self):
        # Clear previous widgets
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.emoji_entries = {}
        self.emoji_frames = {}

        num_cols = 2  # Two wide column

        for i in range(self.emoji_count):
            row = i // num_cols
            col = i % num_cols

            # Container frame for each emoji entry
            frame = tk.Frame(self.scroll_frame, bd=2, relief="solid", padx=10, pady=1)
            frame.grid(row=row, column=col, sticky="w")
            self.emoji_frames[i] = frame

            # ID Label
            tk.Label(frame, text=f"{i}", width=1).pack(side="left")

            # Emoji text entry
            emoji = tk.Entry(frame, width=15)
            emoji.insert(0, self.emoji_mappings.get(i, (":white_square:", "#ffffff"))[0])
            emoji.pack(side="left", padx=4)

            # Color or image display
            value = self.emoji_mappings.get(i, (":white_square:", "#ffffff"))[1]
            if isinstance(value, str) and value.startswith("#"):
                color_box = tk.Label(frame, bg=value, width=3, relief="raised")
            else:
                color_box = tk.Label(frame, image=value, width=25, height=25, relief="raised")
                color_box.image = value  # Prevent GC

            color_box.pack(side="left", padx=6)

            # Color/image selection logic
            def choose_color_or_image(i=i, color_box=color_box):
                current = self.emoji_mappings[i][1]
                
                # Check if this is a Slack emoji
                if i in self.slack_emoji_indices:
                    # If it's a Slack emoji, open the Slack emoji search dialog
                    if self.slack_emojis is not None:
                        self.show_slack_emoji_search_for_update(i, color_box)
                    else:
                        # This should never happen! but just in case it does...
                        messagebox.showinfo("Slack Emojis Not Loaded", 
                                           "Please load Slack emoji JSON first using 'Add Slack Emoji' button.")
                elif isinstance(current, str) and current.startswith("#"):
                    # Handle color selection
                    result = askcolor(title="Choose Color", initialcolor=current)
                    if result[1]:
                        self.emoji_mappings[i] = (self.emoji_entries[i][0].get(), result[1])
                        color_box.config(bg=result[1])
                        self.refresh_grid_colors()
                else:
                    # Handle regular image selection
                    path = filedialog.askopenfilename(
                        initialdir="/",
                        title="Select An Image",
                        filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif"), ("Any", ".*")]
                    )
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

            # Left-click to change color/image
            color_box.bind("<Button-1>", lambda e, i=i, cb=color_box: choose_color_or_image(i, cb))
            # Right-click to remove emoji
            color_box.bind("<Button-3>", lambda e, i=i: self.remove_emoji(i))

            # Remove button
            remove_btn = tk.Button(frame, text="-", command=lambda i=i: self.remove_emoji(i), width=2)
            remove_btn.pack(side="left", padx=4)

            self.emoji_entries[i] = (emoji, color_box)

        self.update_selection_highlight()

        # Adjust scroll canvas height for 2-column layout
        visible_rows = min((self.emoji_count + 1) // 2, 4)
        row_height = 40 + 1 # +1 for padding
        self.scroll_canvas.config(height=visible_rows * row_height)

    # New method for updating a specific Slack emoji
    def show_slack_emoji_search_for_update(self, index, color_box):
        search_window = tk.Toplevel(self.root)
        search_window.title("Select New Slack Emoji")
        search_window.geometry("300x400")
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_window, textvariable=search_var)
        search_entry.pack(fill="x", padx=5, pady=5)
    
        listbox = tk.Listbox(search_window)
        listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        def update_list(*args):
            search_term = search_var.get().lower()
            listbox.delete(0, tk.END)
            
            if not search_term:
                # If empty search, show all emojis
                for key in self.slack_emojis:
                    listbox.insert(tk.END, key)
                return
                
            # Find matches based on different search patterns
            matches = set()
            
            for key in self.slack_emojis:
                key_lower = key.lower()
                # Remove colons from emoji name
                clean_key = key_lower.strip(':')
                
                # Direct substring match
                if search_term in clean_key:
                    matches.add(key)
                    continue
                    
                # Handle compound words with separators
                # For example: "notlikethis" should match "not_like_this"
                clean_key_no_separators = clean_key.replace('-', '').replace('_', '')
                
                if search_term in clean_key_no_separators:
                    matches.add(key)
                    continue
                    
                # For search terms with multiple words, check if they appear in the emoji name
                if '_' in search_term or '-' in search_term:
                    search_parts = search_term.replace('-', '_').split('_')
                    clean_key_parts = clean_key.replace('-', '_').split('_')
                    
                    # Check if all search parts are in the emoji parts
                    if all(any(sp in part for part in clean_key_parts) for sp in search_parts):
                        matches.add(key)
                    continue
                    
                # For things like "catnot" matching "notlikethis-cat", we'll use a more targeted approach
                if len(search_term) >= 4:
                    # Split search term into potential pieces (first half and second half)
                    mid = len(search_term) // 2
                    first_half = search_term[:mid]
                    second_half = search_term[mid:]
                    
                    # Check if both halves appear in the emoji name (in any order)
                    if (first_half in clean_key and second_half in clean_key) or \
                    (first_half in clean_key_no_separators and second_half in clean_key_no_separators):
                        matches.add(key)
                        continue
            
            # Sort matches for better UX
            sorted_matches = sorted(matches)
            for match in sorted_matches:
                listbox.insert(tk.END, match)
                
        # Add a results count label
        result_label = tk.Label(search_window, text="")
        result_label.pack(fill="x", padx=5)
        
        def on_search_update(*args):
            update_list()
            count = listbox.size()
            result_label.config(text=f"{count} results found")
        
        search_var.trace("w", on_search_update)
        on_search_update()
        
        def on_select(event):
            if not listbox.curselection():
                return
            selection = listbox.get(listbox.curselection())
            url = self.slack_emojis[selection]
            # Update the existing emoji instead of adding a new one
            self.update_slack_emoji(index, selection, url, color_box)
            search_window.destroy()
            
        listbox.bind("<Double-Button-1>", on_select)
        search_entry.focus()

    # New method to update an existing slack emoji
    def update_slack_emoji(self, index, name, url, color_box):
        try:
            with urllib.request.urlopen(url) as response:
                img_data = response.read()
            img = Image.open(BytesIO(img_data)).resize((self.cell_size, self.cell_size), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            
            # Update the emoji mapping
            emoji_name = f":{name}:"
            self.emoji_mappings[index] = (emoji_name, tk_img)
            
            # Update the UI
            self.emoji_entries[index][0].delete(0, tk.END)
            self.emoji_entries[index][0].insert(0, emoji_name)
            color_box.config(image=tk_img)
            color_box.image = tk_img  # Keep a reference
            
            # Refresh the grid
            self.refresh_grid_colors()
            self.canvas.focus_set()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load emoji image:\n{e}")

    def update_selection_highlight(self):
        for i, frame in self.emoji_frames.items():
            if i == self.current_color:
                frame.config(highlightbackground="lightgray", highlightthickness=1, relief="flat")
            else:
                frame.config(highlightthickness=0, relief="flat")

    def add_image(self):
        # TODO: this is prone to bugs we have duplicated code path = filedialog.askopenfilename... make this a function or something
        #path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        #path = filedialog.askopenfilename(initialdir="/", title="Select An Image", filetypes=(("jpeg files", "*.jpg;*.jpeg"), ("gif files", "*.gif*"), ("png files", "*.png")))
        path = filedialog.askopenfilename(initialdir="/", title="Select An Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif"),("Any", ".*")])
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

    def add_slack_emoji(self):
        if self.slack_emojis is None:
            path = filedialog.askopenfilename(title="Select Slack Emoji JSON", filetypes=[("JSON files", "*.json")])
            if not path:
                return
            with open(path, "r") as f:
                self.slack_emojis = json.load(f)
            messagebox.showinfo("Loaded", f"{len(self.slack_emojis)} Slack emojis loaded.")
            return

        # Show search dialog
        self.show_slack_emoji_search()

    # I really need to clean this up, I wanted a decent search functionality but at what cost
    # this has some problems like just typing _ is being handled as if its nothing we need to fix that
    # but its fine for now as it still shows up high in the list so its manageable for now 
    def show_slack_emoji_search(self):
        search_window = tk.Toplevel(self.root)
        search_window.title("Search Slack Emoji")
        search_window.geometry("300x400")
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_window, textvariable=search_var)
        search_entry.pack(fill="x", padx=5, pady=5)
    
        listbox = tk.Listbox(search_window)
        listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        def update_list(*args):
            search_term = search_var.get().lower()
            listbox.delete(0, tk.END)
            
            if not search_term:
                # If empty search, show all emojis
                for key in self.slack_emojis:
                    listbox.insert(tk.END, key)
                return
                
            # Find matches based on different search patterns
            matches = set()
            
            for key in self.slack_emojis:
                key_lower = key.lower()
                # Remove colons from emoji name
                clean_key = key_lower.strip(':')
                
                # Direct substring match (original behavior)
                if search_term in clean_key:
                    matches.add(key)
                    continue
                    
                # Handle compound words with separators
                # For example: "notlikethis" should match "not_like_this"
                clean_key_no_separators = clean_key.replace('-', '').replace('_', '')
                
                if search_term in clean_key_no_separators:
                    matches.add(key)
                    continue
                    
                # For search terms with multiple words, check if they appear in the emoji name
                if '_' in search_term or '-' in search_term:
                    search_parts = search_term.replace('-', '_').split('_')
                    clean_key_parts = clean_key.replace('-', '_').split('_')
                    
                    # Check if all search parts are in the emoji parts
                    if all(any(sp in part for part in clean_key_parts) for sp in search_parts):
                        matches.add(key)
                    continue
                    
                # For things like "catnot" matching "notlikethis-cat", we'll use a more targeted approach
                if len(search_term) >= 4:
                    # Split search term into potential pieces (first half and second half)
                    mid = len(search_term) // 2
                    first_half = search_term[:mid]
                    second_half = search_term[mid:]
                    
                    # Check if both halves appear in the emoji name (in any order)
                    if (first_half in clean_key and second_half in clean_key) or \
                    (first_half in clean_key_no_separators and second_half in clean_key_no_separators):
                        matches.add(key)
                        continue
            
            # Sort matches for better UX
            sorted_matches = sorted(matches)
            for match in sorted_matches:
                listbox.insert(tk.END, match)
                
        # Add a results count label
        result_label = tk.Label(search_window, text="")
        result_label.pack(fill="x", padx=5)
        
        def on_search_update(*args):
            update_list()
            count = listbox.size()
            result_label.config(text=f"{count} results found")
        
        search_var.trace("w", on_search_update)
        on_search_update()
        
        def on_select(event):
            if not listbox.curselection():
                return
            selection = listbox.get(listbox.curselection())
            url = self.slack_emojis[selection]
            self.add_slack_emoji_to_palette(selection, url)
            search_window.destroy()
            
        listbox.bind("<Double-Button-1>", on_select)
        search_entry.focus()

    def add_slack_emoji_to_palette(self, name, url):
        if self.emoji_count >= MAX_EMOJIS:
            messagebox.showinfo("Limit reached", f"Maximum of {MAX_EMOJIS} emojis allowed.")
            return
        try:
            with urllib.request.urlopen(url) as response:
                img_data = response.read()
            img = Image.open(BytesIO(img_data)).resize((self.cell_size, self.cell_size), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self.emoji_mappings[self.emoji_count] = (f":{name}:", tk_img)
            # Mark this as a Slack emoji
            self.slack_emoji_indices.add(self.emoji_count)
            self.emoji_count += 1
            self.build_emoji_entries()
            self.canvas.focus_set()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load emoji image:\n{e}")

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
        
        # Update slack_emoji_indices
        new_slack_indices = set()
        for old_idx in self.slack_emoji_indices:
            if old_idx < index:
                new_slack_indices.add(old_idx)
            elif old_idx > index:
                new_slack_indices.add(old_idx - 1)
        self.slack_emoji_indices = new_slack_indices
        
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
            current_color_or_image = self.emoji_mappings[i][1]
            if self.emoji_mappings[i][0] != emoji_val:
                self.emoji_mappings[i] = (emoji_val, current_color_or_image)
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
                    img_id = self.canvas.create_image(x1, y1, anchor="nw", image=color)
                    self.canvas_images[(r, c)] = img_id
                self.rects[(r, c)] = rect

    def setup_bindings(self):
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<B3-Motion>", self.on_mouse_drag)
        self.root.bind("<Key>", self.handle_keypress)

    def on_left_click(self, event):
        self.active_button = 1
        self.paint_at(event)

    def on_right_click(self, event):
        self.active_button = 3
        self.paint_at(event)

    def on_mouse_drag(self, event):
        self.paint_at(event)

    def refocus_canvas(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if not isinstance(widget, tk.Entry):
            self.canvas.focus_set()

    def paint_at(self, event):
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if self.active_button == 1:  # Left click = paint
                new_idx = self.current_color
            elif self.active_button == 3:  # Right click = erase
                new_idx = 0
            else:
                return

            self.grid[row][col] = new_idx

            # Remove existing image if present
            if (row, col) in self.canvas_images:
                self.canvas.delete(self.canvas_images[(row, col)])
                del self.canvas_images[(row, col)]

            fill = self.emoji_mappings.get(new_idx, (":?", "black"))[1]
            if isinstance(fill, str):
                self.canvas.itemconfig(self.rects[(row, col)], fill=fill)
            else:
                self.canvas.itemconfig(self.rects[(row, col)], fill="white")
                img_id = self.canvas.create_image(col * self.cell_size, row * self.cell_size, anchor="nw", image=fill)
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

        flat_emojis = [":" + p + ":" for line in lines for p in line.split(":") if p]
        unique_emojis = []
        for e in flat_emojis:
            if e not in unique_emojis:
                unique_emojis.append(e)

        # Build new mappings
        self.emoji_mappings = {
            i: (emoji, self.random_pastel_color()) for i, emoji in enumerate(unique_emojis)
        }
        self.emoji_count = len(self.emoji_mappings)

        # Update UI
        self.build_emoji_entries()

        # Update grid size
        self.rows = len(lines)
        self.cols = max(len(line.split(":")) // 2 for line in lines)
        self.row_entry.delete(0, tk.END)
        self.col_entry.delete(0, tk.END)
        self.row_entry.insert(0, str(self.rows))
        self.col_entry.insert(0, str(self.cols))
        self.reset_grid()

        # Fill grid
        for r, line in enumerate(lines):
            parts = [":" + p + ":" for p in line.split(":") if p]
            for c, part in enumerate(parts):
                for idx, (emoji, _) in self.emoji_mappings.items():
                    if part == emoji:
                        self.grid[r][c] = idx
                        break
        self.refresh_grid_colors()

if __name__ == "__main__":
    root = tk.Tk()
    check_for_update()
    app = EmojiGridApp(root)
    root.mainloop()
