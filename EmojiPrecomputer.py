import time
import numpy as np
from PIL import Image
import io
import os
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
import asyncio
import urllib.request
from urllib.parse import urlparse
import pickle
import threading
import concurrent.futures
import math
from collections import defaultdict, Counter

#
#   This class precomputes all emojis so it can we can create multiple images without having to recompute every time
#   saved in emoji_feature_cache.pkl
#

class EmojiPrecomputer:
    def __init__(self, slack_emojis, slack_emojis_version, background_color, progress_callback):
        self.slack_emojis = slack_emojis
        self.slack_emojis_version = slack_emojis_version
        self.background_color = background_color
        self.exclude_gifs = False
        self.progress_callback = progress_callback
        
        self.emoji_colors = {}      # Cache for emoji average colors
        #self.emoji_patterns = {}    # Cache for emoji patterns/textures
        self.emoji_images = {}      # Cache for emoji PIL images
        
        self.processed_count = 0
        self.total_emojis = len(self.slack_emojis)
        
        self.color_to_emoji_cache = {} # Cache for color to emoji mapping # TODO: still used?
        self.emoji_clusters = {} # Cache for emoji clusters with similar visual properties
        
        self.color_buckets = defaultdict(list) # TODO

    def reset_cache(self):
        self.emoji_colors = {}
        #self.emoji_patterns = {}
        self.emoji_images = {}
        self.color_to_emoji_cache = {}
        self.emoji_clusters = {}

    def _download_emoji_image(self, name, url):
        try:
            if name in self.emoji_images:
                return self.emoji_images[name]
            with urllib.request.urlopen(url, timeout=5) as response:
                img_data = response.read()
            img = Image.open(io.BytesIO(img_data)).convert('RGBA')
            self.emoji_images[name] = img
            return img
        except Exception as e:
            print(f"Failed to download emoji {name}: {e}")
            return None

    # All the async functions were an attempt at making the precomuting go faster before realizing slack is probably just ratelimiting us...
    # however it does make it a bit faster at the cost of a additional library so leaving it but only using it if the library is already installed 
    async def _download_emoji_image_async(self, name, url):
        try:
            # Add small delay to be nice to Slack's servers
            #await asyncio.sleep(0.01)  # 10ms delay between requests

            # Initialize session if needed
            if self.session is None:
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
                
            # Parse URL to check if it's valid
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                print(f"Invalid URL for emoji {name}: {url}")
                return None
                
            async with self.session.get(url) as response:
                if response.status != 200:
                    print(f"Failed to download emoji {name}: HTTP {response.status}")
                    return None
                    
                img_data = await response.read()
                
            # Process the image
            img = Image.open(io.BytesIO(img_data)).convert('RGBA')
            self.emoji_images[name] = img
            return img
        except asyncio.TimeoutError:
            print(f"Timeout downloading emoji {name}")
            return None
        except Exception as e:
            print(f"Failed to download emoji {name}: {e}")
            return None

    def _download_emoji_batch(self, emoji_batch):
        #max_workers = min(os.cpu_count() * 2 or 8, 32)  # Increased workers for I/O bound task
        # Reduced workers to avoid overwhelming Slack's servers
        max_workers = min(8, len(emoji_batch))  # Max 10 concurrent downloads
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_emoji = {
                executor.submit(self._download_emoji_image, name, url): name
                for name, url in emoji_batch.items()
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_emoji):
                name = future_to_emoji[future]
                try:
                    img = future.result()
                    if img is not None:
                        self._calculate_emoji_features(name, img)
                except Exception as e:
                    print(f"Error processing {name}: {e}")

                self.processed_count += 1
                if self.processed_count % 10 == 0: # We update in intervals
                    self.progress_callback(int(100 * self.processed_count / self.total_emojis))

    async def _download_emoji_batch_async(self, emoji_batch):
        tasks = []
        for name, url in emoji_batch.items():
            tasks.append(self._download_emoji_image_async(name, url))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for (name, _), result in zip(emoji_batch.items(), results):
            if isinstance(result, Exception):
                print(f"Error downloading {name}: {result}")
            elif result is not None:
                self._calculate_emoji_features(name, result)
            
            self.processed_count += 1
            if self.processed_count % 10 == 0:  # Update progress less frequently
                self.progress_callback(int(100 * self.processed_count / self.total_emojis))
                        
    def _calculate_emoji_features(self, name, img):
        self._calculate_emoji_color_kmeans(name, img)
        #self._calculate_emoji_color_freq(name, img)
        # Calculate pattern features (texture descriptor)
        #self._calculate_emoji_pattern(name, img)

    def extract_dominant_color(self, name, img, num_colors=5):
        # Convert image to 'P' mode with adaptive palette of num_colors colors
        palette_img = img.convert('P', palette=Image.ADAPTIVE, colors=num_colors)
        
        # Get palette colors as RGB tuples
        palette = palette_img.getpalette()[:num_colors * 3]  # RGB triplets
        
        # Count pixels per palette color index
        color_counts = palette_img.histogram()[:num_colors]
        
        # Find the palette color with max count (dominant)
        dominant_index = np.argmax(color_counts)
        
        dominant_color = palette[dominant_index*3 : dominant_index*3+3]
        
        self.emoji_colors[name] = [(tuple(map(int, dominant_color)), 1.0)]

    def _calculate_emoji_color_freq(self, name, img):
        img_array = np.array(img).astype(np.uint8)

        # Extract RGB and Alpha
        rgb = img_array[..., :3]
        alpha = img_array[..., 3] / 255.0

        # Slack dark mode background (optional)
        #bg = np.array([34, 37, 41], dtype=np.uint8)
        # Turns hex in to rgb
        bg = np.array([int(self.background_color[i:i+2], 16) for i in (1, 3, 5)], dtype=np.uint8)
        bg = np.broadcast_to(bg, rgb.shape)

        # Blend with background using alpha
        alpha_expanded = alpha[..., None]
        blended = (rgb * alpha_expanded + bg * (1 - alpha_expanded)).astype(np.uint8)

        # Use only visible pixels
        significant_alpha = alpha > 0.1
        if np.any(significant_alpha):
            pixels = blended[significant_alpha].reshape(-1, 3)

            # Count color frequency
            color_counts = Counter(map(tuple, pixels))
            total_pixels = sum(color_counts.values())

            # Get top N dominant colors
            top_colors = color_counts.most_common(5)
            self.emoji_colors[name] = [
                (color, count / total_pixels) for color, count in top_colors
            ]
        else:
            # Fully transparent; use background
            self.emoji_colors[name] = [(tuple(bg[0, 0]), 1.0)]

    def _calculate_emoji_color_kmeans(self, name, img):
        img_array = np.array(img).astype(np.float32)
        
        # Extract RGB and Alpha
        rgb = img_array[..., :3]
        alpha = img_array[..., 3] / 255.0
        
        # Background color (Slack dark mode)
        #bg = np.array([34, 37, 41], dtype=np.float32)
        # Turns hex in to rgb
        bg = np.array([int(self.background_color[i:i+2], 16) for i in (1, 3, 5)], dtype=np.float32)
        bg = np.broadcast_to(bg, rgb.shape)
        
        # Linear interpolation with alpha
        alpha_expanded = alpha[..., None]
        blended = rgb * alpha_expanded + bg * (1 - alpha_expanded)
        
        # Convert to Lab color space for better perceptual representation
        # We use a simplified RGB to Lab conversion since we don't need full accuracy
        # First, get only pixels with significant alpha (non-transparent)
        significant_alpha = alpha > 0.001 # TODO: maybe use transparency aswell
        if np.any(significant_alpha):
            pixels = blended[significant_alpha].reshape(-1, 3)
            
            # Calculate dominant colors using K-means for better representation
            # E.g. for pixel art, dominant colors are more important than averages
            if len(pixels) > 100:  # Only if we have enough pixels
                try:
                    k = min(5, len(pixels) // 10)
                    colors, labels = self.simple_kmeans(pixels, k)
                    counts = np.bincount(labels)
                    proportions = counts / len(pixels)
                    
                    # Store as a list of (color, proportion) tuples
                    self.emoji_colors[name] = [(tuple(map(int, color)), prop) for color, prop in zip(colors, proportions)]
                except:
                    # Fallback to simple average
                    avg_color = np.mean(pixels, axis=0)
                    self.emoji_colors[name] = [(tuple(map(int, avg_color)), 1.0)]
            else:
                # Fallback to simple average for small images
                avg_color = np.mean(pixels, axis=0)
                self.emoji_colors[name] = [(tuple(map(int, avg_color)), 1.0)]
        else:
            # Completely transparent image, use background color
            self.emoji_colors[name] = [(tuple(map(int, bg[0, 0])), 1.0)]
    
    def simple_kmeans(self, pixels, k=3, max_iter=20, tol=1e-4, seed=0):
        np.random.seed(seed)
        n_samples = pixels.shape[0]

        # K-means++ initialization
        centroids = [pixels[np.random.choice(n_samples)]]
        for _ in range(1, k):
            dists = np.min(np.linalg.norm(pixels[:, None] - np.array(centroids)[None, :], axis=2)**2, axis=1)
            total = np.sum(dists)
            if total == 0:
                probs = np.ones_like(dists) / len(dists)
            else:
                probs = dists / total
            centroids.append(pixels[np.random.choice(n_samples, p=probs)])
        centroids = np.array(centroids)

        for _ in range(max_iter):
            # Assign labels
            distances = np.linalg.norm(pixels[:, None] - centroids[None, :], axis=2)
            labels = np.argmin(distances, axis=1)

            # Update centroids
            new_centroids = []
            for i in range(k):
                cluster_points = pixels[labels == i]
                if len(cluster_points) > 0:
                    centroid = cluster_points.mean(axis=0)
                else:
                    # Reinitialize empty cluster with a random pixel
                    centroid = pixels[np.random.choice(n_samples)]
                new_centroids.append(centroid)
            new_centroids = np.array(new_centroids)


            # Check for convergence
            if np.linalg.norm(new_centroids - centroids) < tol:
                break
            centroids = new_centroids

        # Compute proportions
        counts = np.bincount(labels, minlength=k)
        proportions = counts / n_samples

        return list(zip([tuple(map(int, c)) for c in centroids], proportions))

    def save_emoji_feature_cache(self, filename="emoji_feature_cache.pkl"):
        cache_data = {
            "version": self.slack_emojis_version,
            "colors": self.emoji_colors,
            "clusters": self.emoji_clusters, # TODO: check what else needs saving
            "color_buckets": self.color_buckets,
            #"patterns": self.emoji_patterns,
            "is_gif_flags": {
                name: self.slack_emojis[name].lower().endswith('.gif')
                for name in self.emoji_colors
            }
        }
        with open(filename, "wb") as f:
            pickle.dump(cache_data, f)

    def load_emoji_feature_cache(self, filename="emoji_feature_cache.pkl"):
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                cache_data = pickle.load(f)
                version = cache_data.get("version", None)
                if(version == None or version != self.slack_emojis_version):
                    return False
                all_colors = cache_data.get("colors", {})
                #all_patterns = cache_data.get("patterns", {})
                all_clusters = cache_data.get("clusters", {})
                all_buckets = cache_data.get("color_buckets", {})
                is_gif_flags = cache_data.get("is_gif_flags", {})

                if self.exclude_gifs:
                    # Filter out GIFs using the flag dictionary
                    filtered_keys = [k for k in all_colors if not is_gif_flags.get(k, False)]
                else:
                    filtered_keys = list(all_colors.keys())

                self.emoji_colors = {k: all_colors[k] for k in filtered_keys}
                #self.emoji_patterns = {k: all_patterns.get(k, {}) for k in filtered_keys}
                self.emoji_clusters = {
                    cluster_key: filtered_emojis
                    for cluster_key, emoji_list in all_clusters.items()
                    if (filtered_emojis := [e for e in emoji_list if e in filtered_keys])
                }
                self.color_buckets = {
                    bucket_key: filtered_emojis
                    for bucket_key, emoji_list in all_buckets.items()
                    if (filtered_emojis := [e for e in emoji_list if e in filtered_keys])
                }


                if self.emoji_colors:
                    self._build_color_index()
                    print(f"Loaded {len(self.emoji_colors)} emoji features from cache.")
                    return True
        return False

    def precompute_all_emoji_colors(self):  # Reduced batch size
        start_time = time.time()
        if self.load_emoji_feature_cache():
            return  # Skip download if loaded from cache
        
        #batch_size=500
        batch_size = math.ceil(self.total_emojis / 8)

        # techniqually we check load_emoji_feature_cache in the cahce function aswell,
        # but no point in unessesarly starting asyncio
        if HAS_AIOHTTP:
            asyncio.run(self.precompute_all_emoji_colors_async(batch_size))
            print(f"Precomputeing all emojis completed in {time.time() - start_time:.2f} seconds")
            return
            
        self.processed_count = 0
        self.total_emojis = len(self.slack_emojis)
        
        # Process emojis in smaller batches to avoid overwhelming Slack
        emoji_items = list(self.slack_emojis.items())
        for i in range(0, self.total_emojis, batch_size):
            batch = dict(emoji_items[i:i+batch_size])
            self._download_emoji_batch(batch)
            
            # Add a small delay between batches to be extra nice to Slack
            #time.sleep(0.1)  # 100ms delay between batches
            
        # Build index for faster lookup
        if len(self.emoji_colors) > 0:
            self._build_color_index()
            self._build_emoji_clusters()
            
        # Save the result for this run
        self.save_emoji_feature_cache()
        # we reload so we can exclude gifs if wanted
        self.load_emoji_feature_cache()
        print(f"Precomputeing all emojis completed in {time.time() - start_time:.2f} seconds")

    def _build_emoji_clusters(self):
        # This is especially useful for pixel art where we want visually similar alternatives
        if not self.emoji_colors:
            return
            
        # Group emojis by dominant color similarity
        color_groups = defaultdict(list)
        
        # Use the first (dominant) color for grouping
        for name, colors in self.emoji_colors.items():
            if not colors:
                continue
                
            # Quantize the dominant color to create buckets
            dominant_color, _ = colors[0]  # (color, proportion)
            quantized = (dominant_color[0] // 16, dominant_color[1] // 16, dominant_color[2] // 16)
            color_groups[quantized].append(name)
        
        # Store the clusters
        self.emoji_clusters = dict(color_groups)
    
    def _build_color_index(self):
        """Build a color to emoji lookup structure for faster matching"""
        # Quantize colors to reduce search space
        self.color_buckets = defaultdict(list)
        
        for name, colors in self.emoji_colors.items():
            if not colors:
                continue
                
            # Use the first (dominant) color for indexing
            dominant_color, proportion = colors[0]
            quantized = (dominant_color[0] // 4, dominant_color[1] // 4, dominant_color[2] // 4)
            self.color_buckets[quantized].append((name, dominant_color))

    async def precompute_all_emoji_colors_async(self, batch_size=100):
        """Precompute features for all emojis using async IO"""
        if self.load_emoji_feature_cache():
            return  # Skip download if loaded from cache
            
        self.processed_count = 0
        self.total_emojis = len(self.slack_emojis)
        
        # Limit concurrent downloads to avoid Slack rate limiting
        semaphore = asyncio.Semaphore(10)  # Only 10 concurrent downloads
        
        async def download_with_semaphore(name, url):
            async with semaphore:
                return await self._download_emoji_image_async(name, url)
        
        # Create connector with conservative limits for Slack's rate limiting
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        
        # Create a single session for all requests
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            self.session = session
            
            # Create tasks for all emojis with semaphore limiting
            tasks = []
            for name, url in self.slack_emojis.items():
                tasks.append(download_with_semaphore(name, url))
            
            # Process all images concurrently (but limited by semaphore)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and update progress
            for (name, _), result in zip(self.slack_emojis.items(), results):
                if isinstance(result, Exception):
                    print(f"Error downloading {name}: {result}")
                elif result is not None:
                    self._calculate_emoji_features(name, result)
                
                self.processed_count += 1
                if self.processed_count % 50 == 0:  # Update progress every 50 images
                    self.progress_callback(int(100 * self.processed_count / self.total_emojis))
                
        # Build index for faster lookup
        if len(self.emoji_colors) > 0:
            self._build_color_index()
            self._build_emoji_clusters()
            
        # Save the result for this run
        self.save_emoji_feature_cache()
        # we reload so we can exclude gifs if wanted
        self.load_emoji_feature_cache()
