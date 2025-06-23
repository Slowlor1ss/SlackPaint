import numpy as np
from PIL import Image, ImageFilter
import math
import time
#
#   Class to convert an image to a grid of emojis
#

from EmojiPrecomputer import EmojiPrecomputer

class ImageToEmojiConverter:
    
    def __init__(self, slack_emojis, slack_emojis_version, progress_callback, status_label_callback, max_width=35, max_height=45):
        self.max_width = max_width
        self.max_height = max_height
        self.progress_callback = progress_callback
        self.status_label_callback = status_label_callback
        #self.pattern_weight = 0.3  # Weight for pattern matching (0 to 1)
        #self.color_weight = 0.7  # Weight for color matching (0 to 1)
        self.edge_detection_mode = False  # Flag for pixel art optimization
        self.edge_detection_threshold = 20  # Default threshold for edge detection
        #self.disable_edge_detection = False 
        self.resampling_mode = Image.Resampling.NEAREST

        self.emoji_precomputer = EmojiPrecomputer(slack_emojis, slack_emojis_version, self.progress_callback)
        
    def set_resampling_mode(self, resampling_mode):
        if(resampling_mode == "Nearest"):
            self.resampling_mode = Image.Resampling.NEAREST
        elif(resampling_mode == "Box"):
            self.resampling_mode = Image.Resampling.BOX
        elif(resampling_mode == "Bilinear"):
            self.resampling_mode = Image.Resampling.BILINEAR
        elif(resampling_mode == "Hamming"):
            self.resampling_mode = Image.Resampling.HAMMING
        elif(resampling_mode == "Bicubic"):
            self.resampling_mode = Image.Resampling.BICUBIC
        elif(resampling_mode == "Lanczos"):
            self.resampling_mode = Image.Resampling.LANCZOS

    def enable_edge_detection_mode(self, enabled=True): #, pattern_importance=0.5
        self.edge_detection_mode = enabled
        #if enabled:
        #    self.pattern_weight = pattern_importance
        #    # TODO: maybe add unrestricted mode where you can enter any value for weights
        #    self.color_weight = 1.0 - pattern_importance
        #    print(f"edge detection mode enabled - Pattern weight: {self.pattern_weight}, Color weight: {self.color_weight}")

    # TBH Pretty useless, and as simple as it gets
    def pixel_art_edge_detection(self, gray_array, threshold=None):
        """
        Edge detection using 4-neighbor intensity difference.
        Args:
            gray_array (np.ndarray): 2D grayscale image
            threshold (float): Difference threshold to classify as an edge
        Returns:
            np.ndarray: Binary edge map
        """
        #if self.disable_edge_detection:
        #    return None

        # Use configured threshold if not explicitly provided
        if threshold is None:
            threshold = self.edge_detection_threshold

        return ImageToEmojiConverter.pixel_art_edge_detection_static(gray_array, threshold)

    @staticmethod
    def pixel_art_edge_detection_static(gray_array, threshold=None):
        height, width = gray_array.shape
        edges = np.zeros_like(gray_array, dtype=bool)

        # Compare with right and bottom neighbors
        for y in range(height - 1):
            for x in range(width - 1):
                pixel = gray_array[y, x]
                right = gray_array[y, x + 1]
                down = gray_array[y + 1, x]

                if abs(int(pixel) - int(right)) > threshold or abs(int(pixel) - int(down)) > threshold:
                    edges[y, x] = True

        return edges

    # TODO: come back to this and tweak
    def _color_distance(self, color1, color2):
        r1, g1, b1 = [int(c) for c in color1]
        r2, g2, b2 = [int(c) for c in color2]
        
        r1, g1, b1 = r1/255.0, g1/255.0, b1/255.0
        r2, g2, b2 = r2/255.0, g2/255.0, b2/255.0
        
        # Apply gamma correction
        r1 = ((r1 + 0.055) / 1.055) ** 2.4 if r1 > 0.04045 else r1 / 12.92
        g1 = ((g1 + 0.055) / 1.055) ** 2.4 if g1 > 0.04045 else g1 / 12.92
        b1 = ((b1 + 0.055) / 1.055) ** 2.4 if b1 > 0.04045 else b1 / 12.92
        
        r2 = ((r2 + 0.055) / 1.055) ** 2.4 if r2 > 0.04045 else r2 / 12.92
        g2 = ((g2 + 0.055) / 1.055) ** 2.4 if g2 > 0.04045 else g2 / 12.92
        b2 = ((b2 + 0.055) / 1.055) ** 2.4 if b2 > 0.04045 else b2 / 12.92
        
        # Simple perceptual distance
        l1 = 0.2126 * r1 + 0.7152 * g1 + 0.0722 * b1
        l2 = 0.2126 * r2 + 0.7152 * g2 + 0.0722 * b2
        
        # Calculate Luminance difference
        lumDiff = (l1 - l2) * 3  # Emphasize luminance differences
        
        # Calculate color differences
        rDiff = r1 - r2
        gDiff = g1 - g2
        bDiff = b1 - b2
        
        # Combine for final distance (weighted for human perception)
        return math.sqrt(lumDiff**2 + rDiff**2 + gDiff**2 + bDiff**2)
        
    def find_closest_emoji(self, color, neighbors=None):
        """Find the emoji that best matches a given color (and optionally, context via neighbors)."""
        if not self.emoji_precomputer.emoji_colors:
            raise ValueError("No emoji features calculated yet something must have gone really wrong!")
            
        color_key = tuple(color)
        context_key = None

        # If we have neighbors, create a context key
        if neighbors and self.edge_detection_mode:
            # Simple hash of neighbor colors for context
            context_key = hash(tuple(sorted(n for n in neighbors if n)))
            full_key = (color_key, context_key)
            
            if full_key in self.emoji_precomputer.color_to_emoji_cache:
                return self.emoji_precomputer.color_to_emoji_cache[full_key]
        elif color_key in self.emoji_precomputer.color_to_emoji_cache:
            return self.emoji_precomputer.color_to_emoji_cache[color_key]

        # Quantize the input color 
        # (The int here is quite important because color is num py uint8 
        # and we'll go our of bounds in the next section if we dont cast to int)
        quantized = tuple(int(c) // 4 for c in color)

        # Search nearby color buckets
        buckets_to_check = []
        for i in range(-1, 2):
            for j in range(-1, 2):
                for k in range(-1, 2):
                    r = max(0, quantized[0] + i)
                    g = max(0, quantized[1] + j)
                    b = max(0, quantized[2] + k)
                    buckets_to_check.append((r, g, b))

        candidates = []
        for bucket in buckets_to_check:
            if bucket in self.emoji_precomputer.color_buckets:
                candidates.extend(self.emoji_precomputer.color_buckets[bucket])

        # Fallback to all emojis if no candidates found
        if not candidates:
            for name, colors in self.emoji_precomputer.emoji_colors.items():
                if colors:
                    candidates.append((name, colors[0][0]))  # use top dominant color

        # Find the best match by color distance
        best_emoji = None
        min_distance = float('inf')
        for name, emoji_color in candidates:
            dist = self._color_distance(color, emoji_color)
            if dist < min_distance:
                min_distance = dist
                best_emoji = name

        # Cache the result using color key or full context key
        if context_key is not None:
            self.emoji_precomputer.color_to_emoji_cache[(color_key, context_key)] = best_emoji
        else:
            self.emoji_precomputer.color_to_emoji_cache[color_key] = best_emoji

        return best_emoji
    
    def _get_neighbor_colors(self, img_array, x, y, size=3):
        height, width = img_array.shape[:2]
        neighbors = []
        
        half = size // 2
        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                nx = x + dx
                ny = y + dy
                if (dx != 0 or dy != 0) and 0 <= nx < width and 0 <= ny < height:
                    neighbors.append(tuple(img_array[ny, nx]))
                    
        return neighbors
    
    def process_image(self, image_path, width_percentage=None, height_percentage=None):
        """Convert an image to a grid of emoji names"""
        start_time = time.time()

        self.emoji_precomputer.reset_cache()
        
        # Open and resize the image
        img = Image.open(image_path).convert('RGB')
        
        # Calculate the target dimensions
        width, height = img.size
        
        # If neither is specified, use max dimensions but maintain aspect ratio
        if width > height:
            # Wide image
            target_width = min(width, self.max_width)
            target_height = int(height * (target_width / width))
            if target_height > self.max_height:
                target_height = self.max_height
                target_width = int(width * (target_height / height))
        else:
            # Tall image
            target_height = min(height, self.max_height)
            target_width = int(width * (target_height / height))
            if target_width > self.max_width:
                target_width = self.max_width
                target_height = int(height * (target_width / width))

        target_width = int(target_width * (width_percentage / 100))
        target_height = int(target_height * (height_percentage / 100))

        # Ensure dimensions don't exceed maximums
        target_width = min(target_width, self.max_width)
        target_height = min(target_height, self.max_height)
        
        # For pixel art mode, use nearest neighbor resampling and sharpen image
        if self.edge_detection_mode:
            img = img.resize((target_width, target_height), Image.Resampling.NEAREST)
            img = img.filter(ImageFilter.SHARPEN)
        else:
            # Regular mode - use user defined resizing
            img = img.resize((target_width, target_height), self.resampling_mode)
        
        # Make sure we have emoji features
        if not self.emoji_precomputer.emoji_colors:
            print("Precomputing emoji features...")
            self.emoji_precomputer.precompute_all_emoji_colors()
        
        img_array = np.array(img)
        
        # Detect edges (if enabled)
        edge_map = None
        if self.edge_detection_mode:
            # For pixel art, detect edges to preserve important features
            gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
            edge_map = self.pixel_art_edge_detection(gray, self.edge_detection_threshold)
            #edge_map = self.simple_edge_detection(gray)
        
        print("Processing image...")
        emoji_grid = []
        
        image_size = target_height * target_width

        # Find unique colors in the image to reduce redundant calculations
        unique_contexts = {}
        
        # First pass - process color mapping with context
        # TODO: optimize
        self.status_label_callback("Process color mapping with context...")
        processed_pixels = 0
        for y in range(target_height):
            row = []
            for x in range(target_width):
                processed_pixels += 1
                self.progress_callback(int(100 * processed_pixels / image_size))
                pixel = tuple(img_array[y, x])
                
                # Get local context for better matching
                #local_pattern = local_patterns.get((x, y)) if self.pattern_weight > 0 else None
                neighbors = self._get_neighbor_colors(img_array, x, y) if self.edge_detection_mode else None
                
                # Create a context key
                context_key = (pixel, hash(tuple(sorted(neighbors))) if neighbors else None)
                
                # Check if we've already processed this context
                if context_key not in unique_contexts:
                    #emoji_name = self.find_closest_emoji(pixel, local_pattern, neighbors)
                    emoji_name = self.find_closest_emoji(pixel, neighbors)
                    unique_contexts[context_key] = emoji_name
                
                row.append(unique_contexts[context_key])
            emoji_grid.append(row)
        
        # For edge detection mode, perform a second pass to ensure edge contrast
        # TODO: clean up this nested if mess...
        if self.edge_detection_mode and edge_map is not None:
            self.status_label_callback("Ensure edge coherence...")
            processed_pixels = 0
            # Second pass - ensure edges are preserved
            for y in range(target_height):
                for x in range(target_width):
                    processed_pixels += 1
                    self.progress_callback(int(100 * processed_pixels / image_size))
                    # If this pixel is on an edge, make sure it has good contrast with neighbors
                    if edge_map[y, x]:
                        curr_emoji = emoji_grid[y][x]
                        
                        # Check neighbors to ensure contrast
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dx == 0 and dy == 0:
                                    continue
                                    
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < target_width and 0 <= ny < target_height:
                                    # If neighbor is on the other side of edge, ensure contrast
                                    if not edge_map[ny, nx]:
                                        # Get current and neighbor emoji colors
                                        if curr_emoji in self.emoji_precomputer.emoji_colors and self.emoji_precomputer.emoji_colors[curr_emoji]:
                                            curr_color = self.emoji_precomputer.emoji_colors[curr_emoji][0][0]
                                            
                                            neighbor_emoji = emoji_grid[ny][nx]
                                            if neighbor_emoji in self.emoji_precomputer.emoji_colors and self.emoji_precomputer.emoji_colors[neighbor_emoji]:
                                                neighbor_color = self.emoji_precomputer.emoji_colors[neighbor_emoji][0][0]
                                                
                                                # Calculate contrast ratio
                                                contrast = self._color_distance(curr_color, neighbor_color)
                                                
                                                # If contrast is too low, try to find a better emoji
                                                if contrast < 0.2:  # Threshold for minimum contrast
                                                    # Get the pixel color
                                                    pixel = tuple(img_array[y, x])
                                                    
                                                    # Find a higher contrast emoji with similar color
                                                    better_emoji = self._find_contrasting_emoji(
                                                        pixel, neighbor_color, curr_emoji)
                                                    
                                                    if better_emoji:
                                                        emoji_grid[y][x] = better_emoji
        
        print(f"Image processing completed in {time.time() - start_time:.2f} seconds")
        return emoji_grid
    
    def _find_contrasting_emoji(self, target_color, avoid_color, current_emoji):
        """Find an emoji with good contrast against avoid_color while staying close to target_color"""
        best_emoji = current_emoji
        best_score = -float('inf')
        
        # Get potential candidates
        quantized = (int(target_color[0]) // 16, int(target_color[1]) // 16, int(target_color[2]) // 16)
        candidates = []
        
        # Check color groups for similar emojis
        if quantized in self.emoji_precomputer.emoji_clusters:
            candidates.extend(self.emoji_precomputer.emoji_clusters[quantized])
        
        # If we don't have enough candidates, add more from adjacent buckets
        if len(candidates) < 5:
            for i in range(-1, 2):
                for j in range(-1, 2):
                    for k in range(-1, 2):
                        if i == 0 and j == 0 and k == 0:
                            continue
                        adj_bucket = (quantized[0] + i, quantized[1] + j, quantized[2] + k)
                        if adj_bucket in self.emoji_precomputer.emoji_clusters:
                            candidates.extend(self.emoji_precomputer.emoji_clusters[adj_bucket])
        
        # Evaluate each candidate
        for name in candidates:
            if name not in self.emoji_precomputer.emoji_colors or not self.emoji_precomputer.emoji_colors[name]:
                continue
                
            emoji_color = self.emoji_precomputer.emoji_colors[name][0][0]
            
            # Score based on color similarity to target and contrast with avoid_color
            color_similarity = 1.0 / (1.0 + self._color_distance(target_color, emoji_color))
            contrast = self._color_distance(emoji_color, avoid_color)
            
            # Combined score (prefer high contrast while staying reasonably close to target color) TODO: tweak values
            score = contrast * 0.6 + color_similarity * 0.4
            
            if score > best_score:
                best_score = score
                best_emoji = name
        
        return best_emoji

    def emoji_grid_to_display(self, emoji_grid):
        """Convert an emoji grid to a format suitable for our UI."""
        # Create a mapping of emoji names to indices for our grid
        emoji_to_index = {}

        # Make sure we have emoji index 0 as the default/empty
        if ":_:" not in emoji_to_index:
            emoji_to_index[":_:"] = 0

        display_grid = []
        processed_count = 0
        for row in emoji_grid:
            display_row = []
            for emoji_name in row:
                self.progress_callback(int(100 * processed_count / len(emoji_grid)))

                # Add colon prefix/suffix if not already present
                full_name = emoji_name
                if not full_name.startswith(':'):
                    full_name = ':' + full_name
                if not full_name.endswith(':'):
                    full_name = full_name + ':'

                # Get or assign an index for this emoji
                if full_name not in emoji_to_index:
                    emoji_to_index[full_name] = len(emoji_to_index)

                display_row.append(emoji_to_index[full_name])
            display_grid.append(display_row)

        # Return both the grid and the mappings we've created
        return display_grid, emoji_to_index
