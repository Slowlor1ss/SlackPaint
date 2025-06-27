import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.colorchooser import askcolor
import webbrowser
from PIL import Image, ImageTk
import random
import os

from Updater import Updater
from ImageToEmojiUI import ImageToEmojiUI

import json
from io import BytesIO
import urllib.request

__version__ = "v0.2.1-beta"

def check_for_update():
    updater = Updater(__version__)
    return updater.check_for_update()

MAX_EMOJIS = 999#10
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
        self.root.resizable(False, False)

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

        self.slack_emojis_version = None # To store the last modified date of the file used to load slack emojis, used to check the "version"
        self.slack_emojis = None  # To store the loaded Slack emoji mapping

        # --- Canvas collapsible section ---
        self.canvas_container = tk.Frame(root)
        self.canvas_container.pack(fill="both", expand=True)

        self.toggle_canvas_button = tk.Button(
            self.canvas_container, text="▼ Hide Canvas", command=self.toggle_canvas
        )
        self.toggle_canvas_button.pack(anchor="w")

        # -- Canvas scrolling --

        # Create a frame that will contain the scrollable canvas
        self.canvas_frame = tk.Frame(self.canvas_container)
        self.canvas_frame.pack(fill="both", expand=True)

        # Initially create canvas without scrollbars
        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0)

        # Create scrollbars
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)

        # Attach canvas to scrollbars
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        # Pack canvas
        self.canvas.pack(fill="both", expand=True)
        
        self.is_scrollable = False

        self.active_button = None
        
        self.approxNonCanvasWidth = 0
        self.approxNonCanvasHeight = 0
        self.setup_settings_panel()
        self.setup_bindings()
        self.reset_grid(initialize=True)

        self.root.bind("<Button-1>", self.refocus_canvas, add="+")
        
        # Bind window resize event to check if we need scrollbars
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.root.after(0, self.late_init)

    def late_init(self):
        """This will run after the first visual frame is drawn"""
        self.root.update_idletasks()

        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        canvas_width = self.cols * self.cell_size
        canvas_height = self.rows * self.cell_size
        self.approxNonCanvasWidth = window_width - canvas_width
        self.approxNonCanvasHeight = window_height - canvas_height

    def on_canvas_configure(self, event):
        self.resize_after_id = None
            
        # Get current window size
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        max_window_width = int(screen_width * 0.7)
        max_window_height = int(screen_height * 0.7)
        
        # Calculate max allowed canvas dimensions (capped at when window reaches 70% screen)
        #max_width = min(self.cols * self.cell_size, max_window_width - self.approxNonCanvasWidth)
        max_width = self.cols * self.cell_size
        max_height = min(self.rows * self.cell_size, max_window_height - self.approxNonCanvasHeight)
        
        # Check if we need scrollbars (window is getting too big)
        needs_scrollbars = (window_width > max_window_width or
                            window_height > max_window_height)
        
        if needs_scrollbars and not self.is_scrollable:
            # Set size of canvas so it doesnt exceed our max
            self.canvas.config(width=max_width, height=max_height)
            self.make_canvas_scrollable()
        elif not needs_scrollbars and self.is_scrollable:
            # Set size of canvas so it doesnt exceed our max
            self.canvas.config(width=max_width, height=max_height)
            self.make_canvas_non_scrollable()
        else:
            # Just update the canvas size
            self.canvas.config(width=max_width, height=max_height)
            # Update scroll region if scrollable
            if self.is_scrollable:
                self.canvas.config(
                    scrollregion=(0, 0, self.cols * self.cell_size, self.rows * self.cell_size)
                )

    def make_canvas_scrollable(self):
        if self.is_scrollable:
            return

        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)

        self.canvas.pack_forget()  # Remove canvas temporarily

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Set scroll region
        self.canvas.config(
            scrollregion=(0, 0, self.cols * self.cell_size, self.rows * self.cell_size)
        )

        self.canvas.bind("<MouseWheel>", self.on_canvas_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_canvas_shift_mousewheel)

        self.is_scrollable = True

    def make_canvas_non_scrollable(self):
        if not self.is_scrollable:
            return

        # Reset the scroll otherwise we run in to issue when making the canvas smaller again and the content being scrolled
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)

        # Hide scrollbars
        self.v_scroll.pack_forget()
        self.h_scroll.pack_forget()

        # Clear scrollregion
        self.canvas.config(scrollregion="")

        self.canvas.unbind("<MouseWheel>")
        self.canvas.unbind("<Shift-MouseWheel>")

        self.is_scrollable = False

    def on_canvas_mousewheel(self, event):
        """Handle vertical scrolling with mouse wheel"""
        if self.is_scrollable:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_canvas_shift_mousewheel(self, event):
        """Handle horizontal scrolling with Shift+mouse wheel"""
        if self.is_scrollable:
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def toggle_canvas(self):
        if self.canvas_frame.winfo_ismapped():
            self.canvas_frame.pack_forget()
            self.toggle_canvas_button.config(text="▶ Show Canvas")
        else:
            self.canvas_frame.pack(fill="both", expand=True)
            self.toggle_canvas_button.config(text="▼ Hide Canvas")

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
                        "5. Use this file when clicking 'Add Slack Emoji'\n"
                        "6. Click 'Add Slack Emoji' again to add a emoji")
        ImageToEmojiUI.create_tooltip(help_icon, help_text)

        button_frame2 = tk.Frame(self.settings_frame)
        button_frame2.pack()
        tk.Button(button_frame2, text="Export", command=self.export).pack(side="left", padx=2)
        tk.Button(button_frame2, text="Save", command=self.save).pack(side="left", padx=2)
        tk.Button(button_frame2, text="Load", command=self.load).pack(side="left", padx=2)

        # Create a frame for Image to Emoji button
        convert_img_frame = tk.Frame(self.settings_frame)
        convert_img_frame.pack()

        convert_img_button = tk.Button(convert_img_frame, text="Image to Emoji", command=self.open_image_converter)
        convert_img_button.pack(side="left")
        
        # --- Legacy features toggle ---
        legacy_frame = tk.Frame(self.settings_frame)
        legacy_frame.pack()
        # Inner frame that holds actual legacy feature buttons
        legacy_inner_frame = tk.Frame(legacy_frame)

        self.legacy_features_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            legacy_frame,
            text="Enable Legacy Features",
            variable=self.legacy_features_var,
            command=lambda: self.toggle_legacy_features(legacy_inner_frame)
        ).pack(pady=3)

        # Create Add Image button (if legacy mode enabled)
        tk.Label(legacy_inner_frame, text="Note: These images cannot be saved.").pack()
        self.add_image_button = tk.Button(legacy_inner_frame, text="Add Image", command=self.add_image)
        self.add_image_button.pack(pady=2)

        tk.Label(self.settings_frame, text="Use left mouse to draw right to remove (idx 0).").pack()
        tk.Label(self.settings_frame, text="Press 0-9 to select emoji index. Or click on the label.").pack()

    def open_image_converter(self):
        """Open the Image to Emoji converter dialog"""
        # Check if Slack emojis are loaded
        if not self.slack_emojis:
            messagebox.showinfo("Slack Emojis Required", 
                            "Please load Slack emojis first using the 'Add Slack Emoji' button.")
            return
        # Show the converter UI
        ImageToEmojiUI(self.root, self)

    def toggle_legacy_features(self, frame):
        if self.legacy_features_var.get():
            frame.pack()
        else:
            frame.pack_forget()

    # There's probably a way better way of doing this lol
    def confirm_reset_grid(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the entire grid?"):
            # I mainly added this (emoji_mappings[0] = (":_:", "#ffffff"))
            # because when converting image to emoji's often idx 0 changes to an image making the gridlines dissapear (intended)
            self.emoji_mappings[0] = (":_:", "#ffffff") 
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
            idLabel = tk.Label(frame, text=f"{i}", width=1)
            idLabel.pack(side="left")

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

            # Left-click to change color/image (when clicking the preview)
            color_box.bind("<Button-1>", lambda e, i=i, cb=color_box: choose_color_or_image(i, cb))

            # Left-click on label to select an emoji for drawing
            emoji.bind("<Button-1>", lambda e, i=i: self.select_emoji(i), add="+")
            idLabel.bind("<Button-1>", lambda e, i=i: self.select_emoji(i), add="+")
            frame.bind("<Button-1>", lambda e, i=i: self.select_emoji(i), add="+")

            # Remove button
            remove_btn = tk.Button(frame, text="-", command=lambda i=i: self.remove_emoji(i), width=2)
            remove_btn.pack(side="left", padx=4)

            self.emoji_entries[i] = (emoji, color_box)

        self.update_selection_highlight()

        # Adjust scroll canvas height for 2-column layout
        visible_rows = min((self.emoji_count + 1) // 2, 4)
        row_height = 40 + 1 # +1 for padding
        self.scroll_canvas.config(height=visible_rows * row_height)
        self.on_canvas_configure(None)

    def select_emoji(self, index):
        """Select an emoji for drawing by clicking on it"""
        if index < self.emoji_count:
            self.current_color = index
            self.update_selection_highlight()
            self.canvas.focus_set()  # Keep canvas focused for keyboard shortcuts

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

    # Re-fetch and update the preview image for all Slack emojis currently in the palette
    def reload_slack_emojis(self):
        if not self.slack_emojis:
            messagebox.showinfo("Slack Emojis Not Loaded", "Please load Slack emojis first using 'Add Slack Emoji'.")
            return

        for i in self.slack_emoji_indices:
            emoji_name, url_or_img = self.emoji_mappings[i]
            name_clean = emoji_name.strip(":")
            if name_clean not in self.slack_emojis:
                continue  # Emoji might have been removed from the source

            url = self.slack_emojis[name_clean]
            try:
                with urllib.request.urlopen(url) as response:
                    img_data = response.read()
                img = Image.open(BytesIO(img_data)).resize((self.cell_size, self.cell_size), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)

                self.emoji_mappings[i] = (emoji_name, tk_img)

                # Update preview image in the UI
                _, color_box = self.emoji_entries[i]
                color_box.config(image=tk_img)
                color_box.image = tk_img  # Keep reference
            except Exception as e:
                print(f"Failed to reload emoji {emoji_name}: {e}")

        self.refresh_grid_colors()
        messagebox.showinfo("Slack Emojis Reloaded", "Slack emoji previews have been reloaded.")

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
            messagebox.showerror("Error", f"Failed to load emoji image: {url}\n{e} (the emoji might have been removed from the server)")

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
            timestamp = os.path.getmtime(path)
            self.slack_emojis_version = datetime.datetime.fromtimestamp(timestamp)
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
            return False
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
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load emoji image: {url}\n{e}")
            return False
        
    def add_slack_emoji_to_palette_parallel(self, name, url):
        try:
            with urllib.request.urlopen(url) as response:
                img_data = response.read()
            img = Image.open(BytesIO(img_data)).resize((self.cell_size, self.cell_size), Image.Resampling.LANCZOS)
            return name, img
        except Exception as e:
            #messagebox.showerror("Error", f"Failed to load emoji image: {url}\n{e}")
            return name, None

    def finalize_add_slack_emoji_to_palette(self, img, name):
        if img is None:
            # Create a fallback image (100x100, debug purple)
            img = Image.new('RGB', (25, 25), color=(255, 0, 255)) 
        tk_img = ImageTk.PhotoImage(img)
        self.emoji_mappings[self.emoji_count] = (f":{name}:", tk_img)
        # Mark this as a Slack emoji
        self.slack_emoji_indices.add(self.emoji_count)
        self.emoji_count += 1

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

    def remove_all_emojis(self):
        # Prevent removing the default emoji at index 0
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

        # Reset emoji mappings and related state
        self.emoji_mappings.clear()
        self.slack_emoji_indices.clear()
        self.emoji_count = 0

        # Rebuild UI and visuals
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

    def set_grid_size(self, new_rows, new_cols):
        if new_rows <= 0 or new_cols <= 0:
            raise ValueError
        self.rows = new_rows
        self.cols = new_cols
        self.reset_grid()
        self.canvas.focus_set()
        #self.on_canvas_configure(None)

    def update_grid_size(self):
        try:
            new_rows = int(self.row_entry.get())
            new_cols = int(self.col_entry.get())
            if new_rows <= 0 or new_cols <= 0:
                raise ValueError
            self.set_grid_size(new_rows, new_cols)
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
        #self.setup_canvas_bindings()

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
        # Convert canvas coordinates to account for scrolling
        if self.is_scrollable:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
        else:
            canvas_x = event.x
            canvas_y = event.y
        
        col = int(canvas_x // self.cell_size)
        row = int(canvas_y // self.cell_size)
        
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
        # --- Export confirmation message ---
        self.export_msg = tk.Label(self.settings_frame, text="", fg="green")
        self.export_msg.config(text="Copied to clipboard!")
        self.export_msg.pack()
        self.root.after(2000, lambda: self.export_msg.pack_forget()) #self.export_msg.config(text="")

    def save(self):
        self.update_palette()
        path = filedialog.asksaveasfilename(defaultextension=".emojigrid")
        if path:
            # Prepare save data
            save_data = {
                "version": __version__,
                "grid_size": {
                    "rows": self.rows,
                    "cols": self.cols
                },
                "emoji_mappings": {},
                "grid": self.grid,
                "slack_emoji_json": self.slack_emojis  # Save the entire Slack emoji JSON
            }

            # Process emoji mappings
            for idx, (emoji_name, value) in self.emoji_mappings.items():
                if idx in self.slack_emoji_indices:
                    # For Slack emojis, just save the name
                    save_data["emoji_mappings"][idx] = {
                        "type": "slack",
                        "name": emoji_name
                    }
                elif isinstance(value, str):  # Color
                    save_data["emoji_mappings"][idx] = {
                        "type": "color",
                        "name": emoji_name,
                        "color": value
                    }
                else:  # Image (though we're not handling this fully in this version)
                    save_data["emoji_mappings"][idx] = {
                        "type": "image",
                        "name": emoji_name
                    }

            # Save to file
            with open(path, "w") as f:
                json.dump(save_data, f, indent=4)

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("Emoji Grid Files", "*.emojigrid")])
        if not path:
            return

        try:
            with open(path, "r") as f:
                save_data = json.load(f)

            # Reset existing state
            self.emoji_mappings.clear()
            self.slack_emoji_indices.clear()
            self.emoji_count = 0

            # Restore Slack emojis JSON if present
            self.slack_emojis = save_data.get("slack_emoji_json", None)

            # Restore grid size
            self.set_grid_size(save_data["grid_size"]["rows"], save_data["grid_size"]["cols"])
            
            # Update grid size entries
            self.row_entry.delete(0, tk.END)
            self.col_entry.delete(0, tk.END)
            self.row_entry.insert(0, str(self.rows))
            self.col_entry.insert(0, str(self.cols))

            # Restore emoji mappings
            for idx, emoji_data in save_data["emoji_mappings"].items():
                idx = int(idx)  # Ensure idx is an integer
                
                if emoji_data["type"] == "slack":
                    # For Slack emojis, try to reload from the saved Slack emoji JSON
                    name = emoji_data["name"].strip(":")  # Remove colons
                    
                    if self.slack_emojis and name in self.slack_emojis:
                        url = self.slack_emojis[name]
                        try:
                            with urllib.request.urlopen(url) as response:
                                img_data = response.read()
                            img = Image.open(BytesIO(img_data)).resize((self.cell_size, self.cell_size), Image.Resampling.LANCZOS)
                            tk_img = ImageTk.PhotoImage(img)
                            
                            self.emoji_mappings[idx] = (emoji_data["name"], tk_img)
                            self.slack_emoji_indices.add(idx)
                            self.emoji_count = max(self.emoji_count, idx + 1)
                        except Exception as e:
                            print(f"Failed to load Slack emoji {name}: {e}")
                            # Fallback to a default color if image can't be loaded
                            self.emoji_mappings[idx] = (emoji_data["name"], "#cccccc")
                    else:
                        # If Slack emoji JSON is not available or emoji not found
                        self.emoji_mappings[idx] = (emoji_data["name"], "#cccccc")
                
                elif emoji_data["type"] == "color":
                    self.emoji_mappings[idx] = (emoji_data["name"], emoji_data["color"])
                    self.emoji_count = max(self.emoji_count, idx + 1)
                
                elif emoji_data["type"] == "image":
                    # Placeholder for future image handling
                    self.emoji_mappings[idx] = (emoji_data["name"], "#ffffff")
                    self.emoji_count = max(self.emoji_count, idx + 1)

            # Restore grid
            self.grid = save_data["grid"]

            # Rebuild UI and refresh grid
            self.build_emoji_entries()
            self.reset_grid()
            self.refresh_grid_colors()

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    check_for_update()
    root.lift() # Bring window to top
    app = EmojiGridApp(root)
    root.mainloop()
