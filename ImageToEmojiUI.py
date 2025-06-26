import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
from PIL import Image
import threading
import os
import time
import queue

from ImageToEmojiConverter import ImageToEmojiConverter

class ImageToEmojiUI:
    def __init__(self, parent, app):
        """
        Args:
            parent: Parent tkinter widget
            app: The main EmojiGridApp instance for accessing its methods
        """
        self.parent = parent
        self.app = app
        self.converter = None
        self.create_ui()
        
    def create_ui(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Convert Image to Emoji Grid")
        #self.dialog.geometry("450x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Main frame
        self.main_frame = tk.Frame(self.dialog, padx=10, pady=10)
        self.main_frame.pack(fill="both", expand=True)
        
        # Image selection
        image_frame = tk.Frame(self.main_frame)
        image_frame.pack(fill="x", pady=5)
        
        tk.Label(image_frame, text="Image:").pack(side="left")
        self.image_path_var = tk.StringVar()
        self.image_path_entry = tk.Entry(image_frame, textvariable=self.image_path_var, width=30)
        self.image_path_entry.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(image_frame, text="Browse...", command=self.browse_image).pack(side="left")
        
        # Size frame
        size_frame = tk.Frame(self.main_frame)
        size_frame.pack(fill="x", pady=5)
        
        # Width control
        width_frame = tk.Frame(size_frame)
        width_frame.pack(side="left", padx=(0, 10))
        tk.Label(width_frame, text="Width %:").pack(side="left")
        self.width_var = tk.StringVar(value="100")
        self.width_entry = tk.Entry(width_frame, textvariable=self.width_var, width=5)
        self.width_entry.pack(side="left", padx=5)
        
        # Height control
        height_frame = tk.Frame(size_frame)
        height_frame.pack(side="left")
        tk.Label(height_frame, text="Height %:").pack(side="left")
        self.height_var = tk.StringVar(value="100")
        self.height_entry = tk.Entry(height_frame, textvariable=self.height_var, width=5)
        self.height_entry.pack(side="left", padx=5)
        
        # Exclude gifs button
        self.exclude_gifs_var = tk.BooleanVar(value=False)
        exclude_gifs_check = tk.Checkbutton(self.main_frame, text="Exclude gif's", variable=self.exclude_gifs_var)
        exclude_gifs_check.pack(anchor="w", pady=0)
        self.exclude_gifs_var.check_widget = exclude_gifs_check
        
        # Create a frame for the Edge detection mode and its help icon
        edge_detec_frame = tk.Frame(self.main_frame)
        edge_detec_frame.pack(anchor="w", pady=0)

        # Toggle Edge detection mode
        self.edge_detection_mode = tk.BooleanVar(value=False)
        edge_detection_check = tk.Checkbutton(edge_detec_frame, text="Edge detection (useless tbh, but was a cool idea :D )", 
                    variable=self.edge_detection_mode, command=self.update_edge_detection_ui_visibility)
        edge_detection_check.pack(side="left", pady=0)

        # Add help icon
        help_icon = tk.Label(edge_detec_frame, text="?", font=("Arial", 8), 
                            bg="#4a7a8c", fg="white", width=1, height=1,
                            relief="raised", cursor="question_arrow")
        help_icon.pack(side="left", pady=0)
        
        help_text = ("Edge detection mode tries to create sharper edges by ensuring a hgher contrast on the edges")
        ImageToEmojiUI.create_tooltip(help_icon, help_text)
        
        # Add edge detection preview (initially hidden)
        self.add_edge_detection_preview_to_ui()
        
        # # Weight size frame
        # weight_size_frame = tk.Frame(self.main_frame)
        # weight_size_frame.pack(fill="x", pady=5)
        # # Pattern weight control
        # pattern_frame = tk.Frame(weight_size_frame)
        # pattern_frame.pack(side="left", padx=(0, 10))
        # tk.Label(pattern_frame, text="Pattern weight:").pack(side="left")
        # self.pattern_var = tk.StringVar(value=str("0.0")) #0.3
        # self.pattern_entry = tk.Entry(pattern_frame, textvariable=self.pattern_var, width=5)
        # self.pattern_entry.pack(side="left", padx=5)
        # # Color weight control
        # color_frame = tk.Frame(weight_size_frame)
        # color_frame.pack(side="left")
        # tk.Label(color_frame, text="Color weight:").pack(side="left")
        # self.color_var = tk.StringVar(value=str("1.0")) #0.7
        # self.color_entry = tk.Entry(color_frame, textvariable=self.color_var, width=5)
        # self.color_entry.pack(side="left", padx=5)

        # Processing options
        options_frame = tk.Frame(self.main_frame)
        options_frame.pack(fill="x", pady=5)
        
        tk.Label(options_frame, text="Resampling mode:").pack(side="left")
        self.resampling_var = tk.StringVar(value="Nearest")
        
        resampling_combo = ttk.Combobox(options_frame, textvariable=self.resampling_var, width=15, 
                                    values=["Nearest", "Box", "Bilinear", "Hamming", "Bicubic", "Lanczos"])
        resampling_combo.pack(side="left", padx=5)
        resampling_combo.state(['readonly'])
        
        # Progress bar
        progress_frame = tk.Frame(self.main_frame)
        progress_frame.pack(fill="x", pady=10)
        
        tk.Label(progress_frame, text="Progress:").pack(side="left")
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)
        
        # Status message
        self.status_var = tk.StringVar(value="Ready to convert")
        status_label = tk.Label(self.main_frame, textvariable=self.status_var, anchor="w")
        status_label.pack(fill="x", pady=5)
        
        # Information text
        info_text = ("This tool will convert an image to a grid of emojis.\n"
                    "The process will analyze Slack emojis by color and map each\n"
                    "pixel to the closest matching emoji.")
        tk.Label(self.main_frame, text=info_text, justify="left", anchor="w").pack(fill="x", pady=10)
        
        # Controls frame
        controls_frame = tk.Frame(self.main_frame)
        controls_frame.pack(fill="x", pady=10)
        
        self.convert_button = tk.Button(controls_frame, text="Convert", command=self.start_conversion, width=10)
        self.convert_button.pack(side="left")
        
        self.cancel_button = tk.Button(controls_frame, text="Cancel", command=self.dialog.destroy, width=10)
        self.cancel_button.pack(side="right")
        
    @staticmethod
    def create_tooltip(widget, text):
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

    def browse_image(self):
        path = filedialog.askopenfilename(
            initialdir="/",
            title="Select Image to Convert",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif"), ("All Files", "*.*")]
        )
        if path:
            self.image_path_var.set(path)
            # Update edge detection preview if edge detection mode is enabled
            if hasattr(self, 'edge_detection_mode') and self.edge_detection_mode.get():
                self.update_edge_preview()
            
    def update_progress(self, value):
        self.progress_var.set(value)
        if value == 100:
            self.status_var.set("Processing complete!")
        #self.dialog.update_idletasks()
        self.progress_bar.update()

    def set_status_var(self, string):
        self.status_var.set(string)
        self.dialog.update_idletasks()
        
    # def get_target_weights(self):
    #     try:
    #         pattern_weight = float(self.pattern_var.get())
    #         color_weight = float(self.color_var.get())
            
    #         # TODO: add unrestricted mode where you can enter any value for weights
    #         pattern_weight = min(1.0, max(0.0, pattern_weight))
    #         color_weight = min(1.0, max(0.0, color_weight))
            
    #         return pattern_weight, color_weight
    #     except ValueError:
    #         messagebox.showerror("Invalid weights", "Weights must be decimal numbers.")
    #         return None, None

    def get_target_dimensions(self):
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            
            # Enforce limits
            width = min(100, max(1, width))
            height = min(100, max(1, height))
            
            return width, height
        except ValueError:
            messagebox.showerror("Invalid dimensions", "Width and height must be integers.")
            return None, None
            
    def disable_controls(self):
        self.convert_button.config(state=tk.DISABLED)
        self.image_path_entry.config(state=tk.DISABLED)
        self.width_entry.config(state=tk.DISABLED)
        self.height_entry.config(state=tk.DISABLED)
        
    def enable_controls(self):
        self.convert_button.config(state=tk.NORMAL)
        self.image_path_entry.config(state=tk.NORMAL)
        self.width_entry.config(state=tk.NORMAL)
        self.height_entry.config(state=tk.NORMAL)
        
    def start_conversion(self):
        image_path = self.image_path_var.get()
        if not image_path or not os.path.exists(image_path):
            messagebox.showerror("Error", "Please select a valid image file.")
            return
            
        # Check if Slack emojis are available
        if not self.app.slack_emojis:
            messagebox.showerror("Error", "No Slack emojis loaded. Please load Slack emojis first.")
            return
            
        target_width, target_height = self.get_target_dimensions()
        if target_width is None or target_height is None:
            return
        
        # We just update the preview one last time before actually generating anything
        self.update_edge_preview()
            
        # Disable controls during processing
        self.disable_controls()
        self.status_var.set("Initializing conversion...")
        self.progress_var.set(0)
        
        # Initialize converter
        self.converter = ImageToEmojiConverter(
            slack_emojis=self.app.slack_emojis,
            slack_emojis_version=self.app.slack_emojis_version,
            max_width=35,
            max_height=45,
            progress_callback=self.update_progress,
            status_label_callback=self.set_status_var
        )

        self.converter.set_resampling_mode(self.resampling_var.get())

        #self.converter.disable_edge_detection = self.disable_edge_detection_var.get()

        # target_pattern_weight, target_color_weight = self.get_target_weights()
        # if target_pattern_weight is None or target_color_weight is None:
        #     return
        # else:
        #     self.converter.pattern_weight = target_pattern_weight
        #     # TODO: add unrestricted mode where you can enter any value for weights
        #     self.converter.color_weight = 1.0 - target_pattern_weight

        self.converter.emoji_precomputer.exclude_gifs = self.exclude_gifs_var.get()
        
        # Set the pixel art mode and edge detection threshold
        edge_detection_enabled = self.edge_detection_mode.get()
        self.converter.enable_edge_detection_mode(edge_detection_enabled)
        
        # Set edge detection threshold if pixel art mode is enabled
        if edge_detection_enabled and hasattr(self, 'tolerance_var'):
            edge_tolerance = self.tolerance_var.get()
            self.converter.edge_detection_threshold = edge_tolerance
        
        # Run conversion in a separate thread to keep UI responsive
        thread = threading.Thread(
            target=self.process_image_thread,
            args=(image_path, target_width, target_height),
            daemon=True
        )
        thread.start()

    def process_image_thread(self, image_path, width, height):
        """Background thread for image processing"""
        try:
            self.status_var.set("Analyzing Slack emoji colors... (This can take a minute when running for the first time)")
            self.converter.emoji_precomputer.precompute_all_emoji_colors()
            
            self.status_var.set("Processing image...")
            emoji_grid = self.converter.process_image(
                image_path, 
                width, #if not self.keep_aspect_var.get() else None,
                height #if not self.keep_aspect_var.get() else None
            )
            
            self.status_var.set("Creating grid display...")
            # Convert to application format
            display_grid, emoji_mapping = self.converter.emoji_grid_to_display(emoji_grid)
            
            # Final step - update UI on main thread
            self.parent.after(0, lambda: self.finalize_conversion(display_grid, emoji_mapping))
            
        except Exception as e:
            self.handle_error(str(e))
            #self.parent.after(0, lambda: self.handle_error(str(e)))
    
    def handle_error(self, error_message):
        messagebox.showerror("Conversion Error", f"An error occurred during conversion:\n{error_message}")
        self.enable_controls()
        self.status_var.set("Conversion failed.")
        
    def finalize_conversion(self, display_grid, emoji_mapping):
        """Complete the conversion and update the main application"""
        try:
            # Update the main application's grid with our new emoji grid
            self.apply_to_app(display_grid, emoji_mapping)
            
            self.status_var.set("Conversion complete!")
            self.enable_controls()
            
            # Close dialog if successful
            self.dialog.destroy()
            
        except Exception as e:
            self.handle_error(str(e))
    
    def apply_to_app_old(self, display_grid, emoji_mapping):
        """Apply the converted grid to the main application"""
        
        self.status_var.set("Loading necessary emojis...")

        # First we remove all emojis as we are about to add a ton of new onces
        self.app.remove_all_emojis()
        
        # Then, ensure the app's grid size matches our converted image
        rows = len(display_grid)
        cols = len(display_grid[0]) if rows > 0 else 0
        
        # Update the app's grid size entries
        self.app.row_entry.delete(0, tk.END)
        self.app.row_entry.insert(0, str(rows))
        self.app.col_entry.delete(0, tk.END)
        self.app.col_entry.insert(0, str(cols))
        
        # Update the grid dimensions
        self.app.rows = rows
        self.app.cols = cols
        
        # Add the emoji mappings to the app
        for emoji_name, idx in emoji_mapping.items():
            self.update_progress(int(100 * idx / len(emoji_mapping)))
                
            # Find this emoji in slack_emojis
            name_without_colons = emoji_name.strip(':')
            if name_without_colons in self.app.slack_emojis:
                url = self.app.slack_emojis[name_without_colons]

                # Add the emoji to the app's palette if needed
                if idx >= self.app.emoji_count:
                    # Mark as Slack emoji and load it properly
                    self.app.slack_emoji_indices.add(idx)
                    self.app.add_slack_emoji_to_palette(name_without_colons, url)
        
        # Update the grid with emoji indices
        self.app.grid = display_grid
        
        # Rebuild the UI
        self.app.build_emoji_entries()
        self.app.reset_grid()
        self.app.refresh_grid_colors()
        #self.app.reload_slack_emojis()

    def apply_to_app(self, display_grid, emoji_mapping):
        self.status_var.set("Loading necessary emojis...")
        # First we remove all emojis as we are about to add a ton of new ones
        self.app.remove_all_emojis()
        
        # Update grid dimensions
        rows = len(display_grid)
        cols = len(display_grid[0]) if rows > 0 else 0
        
        # Update the app's grid size entries
        self.app.row_entry.delete(0, tk.END)
        self.app.row_entry.insert(0, str(rows))
        self.app.col_entry.delete(0, tk.END)
        self.app.col_entry.insert(0, str(cols))
        
        # Update the grid dimensions
        self.app.set_grid_size(rows, cols)
        
        # Create a work queue for emoji processing
        work_queue = queue.Queue()
        results = {}
        error_list = []
        images_list = {}
        
        # Function for worker threads to process emojis
        def process_emoji():
            while True:
                try:
                    emoji_name, idx = work_queue.get(block=False)
                except queue.Empty:
                    break
                try:
                    name_without_colons = emoji_name.strip(':')
                    
                    if name_without_colons in self.app.slack_emojis:
                        url = self.app.slack_emojis[name_without_colons]
                        # Only add if we need this index
                        if idx >= self.app.emoji_count:
                            # Add emoji to app's palette
                            name, img = self.app.add_slack_emoji_to_palette_parallel(name_without_colons, url)
                            if img == None:
                                nonlocal error_list
                                error_list.append(name)
                            images_list.update({name: img})
                    
                    results[emoji_name] = True
                except Exception as e:
                    print(f"Worker error: {e}")
                    break
                finally:
                    work_queue.task_done()
        
        # Add all emoji mappings to the queue
        for emoji_name, idx in emoji_mapping.items():
            work_queue.put((emoji_name, idx))
        
        # Start worker threads
        num_workers = min(8, len(emoji_mapping))  # Limit max threads
        threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=process_emoji, daemon=True)
            t.start()
            threads.append(t)
        
        # Wait for all threads to complete with a progress update loop
        while not work_queue.empty():
            processed = len(results)
            self.update_progress(int(100 * processed / len(emoji_mapping)))
            time.sleep(0.1)
        
        # Ensure all tasks are completed
        work_queue.join()

        # Finalize adding slack emojis to pallete (need to do it like this because tinker isnt thread safe!)
        # Theres probably a wayyy better way of doing this, but for now this is fine,
        # but we loop like this beacuse otherwise the order is wrong and images get places in the wrong place
        for emoji_name, idx in emoji_mapping.items():
            name_without_colons = emoji_name.strip(':')
            self.app.finalize_add_slack_emoji_to_palette(images_list[name_without_colons], name_without_colons)
        
        # Update the grid with emoji indices
        self.app.grid = display_grid
        
        # Rebuild the UI components
        self.app.build_emoji_entries()
        self.app.reset_grid()
        self.app.refresh_grid_colors()
        
        # Show warning if errors occurred
        if len(error_list) > 0:
            error_string = ""
            for emoji_name in error_list:
                error_string += (emoji_name + ", ")
            messagebox.showerror("Error", f"Failed to load emoji image(s): {error_string}\n"
                                 "You most likely need to re-generate slack_emojis.json (use the '?' next to \"Add Slack Emoji\" button)")
            self.status_var.set(f"Completed with {len(error_list)} emoji loading errors")

    def add_edge_detection_preview_to_ui(self):
        preview_frame = tk.Frame(self.main_frame)
        preview_frame.pack(fill="x", pady=5)
        
        # Edge detection preview
        self.preview_canvas = tk.Canvas(preview_frame, width=200, height=150, background="white")
        self.preview_canvas.pack(side="left", padx=5)
        
        # Controls for edge detection
        controls_frame = tk.Frame(preview_frame)
        controls_frame.pack(side="left", fill="y", padx=5)
        
        # Label for the tolerance slider
        tk.Label(controls_frame, text="Edge Detection Tolerance:").pack(anchor="w", pady=(0, 5))
        
        # Tolerance slider itself...
        self.tolerance_var = tk.IntVar(value=20)  # Default tolerance value
        tolerance_slider = tk.Scale(controls_frame, from_=1, to=100, orient="horizontal",
                                variable=self.tolerance_var, command=self.update_edge_preview)
        tolerance_slider.pack(fill="x")

        #self.disable_edge_detection_var = tk.BooleanVar(value=False)
        #tk.Checkbutton(controls_frame, text="Disable edge detection", variable=self.disable_edge_detection_var).pack(anchor="w", pady=0)
        
        # Refresh button
        refresh_button = tk.Button(controls_frame, text="Refresh Preview", command=self.update_edge_preview)
        refresh_button.pack(pady=5)
        
        # Label to show when preview is available
        self.preview_status = tk.StringVar(value="No image loaded")
        tk.Label(controls_frame, textvariable=self.preview_status).pack(anchor="w")
        
        # Hide preview by default (only show when pixel art mode is enabled)
        preview_frame.pack_forget()
        self.preview_frame = preview_frame

    def update_edge_detection_ui_visibility(self):
        if self.edge_detection_mode.get():
            self.preview_frame.pack(fill="x", pady=5, after=self.exclude_gifs_var.check_widget)
            # Update preview if we have an image
            if hasattr(self, 'image_path_var') and self.image_path_var.get():
                self.update_edge_preview()
        else:
            self.preview_frame.pack_forget()

    def update_edge_preview(self, *args):
        image_path = self.image_path_var.get()
        if not image_path or not os.path.exists(image_path):
            self.preview_status.set("No valid image loaded")
            return
        # if self.disable_edge_detection_var.get():
        #     self.preview_status.set("Edge detection disabled")
        #     # Clear canvas
        #     self.preview_canvas.delete("all")
        #     return
        try:
            img = Image.open(image_path).convert('RGB')
            img.thumbnail((200, 150))
            img_array = np.array(img)

            # Get grayscale image
            gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
            
            tolerance = self.tolerance_var.get()
            edges = self.get_edge_detection_preview(gray, tolerance)
            
            # Convert edges to an image
            edge_img = Image.fromarray((edges * 255).astype(np.uint8))
            
            # Convert to PhotoImage for display
            from PIL import ImageTk
            self.edge_preview_img = ImageTk.PhotoImage(edge_img)
            
            # Update canvas
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(100, 75, image=self.edge_preview_img)
            
            self.preview_status.set("")
        except Exception as e:
            self.preview_status.set(f"Error: {str(e)}")

    def get_edge_detection_preview(self, gray_array, threshold=20):
        return ImageToEmojiConverter.pixel_art_edge_detection_static(gray_array, threshold)
