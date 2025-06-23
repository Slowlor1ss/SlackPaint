import sys
import os
import tkinter as tk
from tkinter import messagebox
import json
import subprocess
import webbrowser
import urllib.request
import shutil
import tempfile
import threading
import time
import re

class Updater:
    def __init__(self, version):
        self.github_repo = "Slowlor1ss/SlackPaint"
        # We use the GitHub API for everything
        self.github_api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        self.commits_api_url = f"https://api.github.com/repos/{self.github_repo}/commits"
        self.py_download_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/SlackPaint.py"
        self.version_file_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/version.txt"
        self.current_version = version 
        # When you bundle a script into an executable, tools like PyInstaller will set sys.frozen = True
        # might need to find something more robust for this but fo rnow more then fine
        # https://pyinstaller.org/en/stable/runtime-information.html
        self.is_exe = getattr(sys, 'frozen', False) 
        
    def check_for_update(self, silent=False):
        """
        Check if a newer version is available using GitHub API
        Returns: (has_update, latest_version)
        """
        try:
            # Get the latest release info
            with urllib.request.urlopen(self.github_api_url, timeout=10) as response:
                release_info = json.loads(response.read().decode('utf-8'))
                
            # The tag_name usually contains the version (e.g., "v1.2.3" or "1.2.3")
            if self.is_exe:
              latest_version = release_info.get('tag_name', '')
            else:
              latest_version = self.get_most_recent_version()

            # Compare versions
            if latest_version and latest_version != self.current_version:
                if latest_version.startswith('v'):
                    latest_version = latest_version[1:]  # Remove 'v' prefix if present

                if silent:
                    return True, latest_version
                    
                # Get changelog based on version type
                if self.is_exe:
                    # For exe, get changelog from release info
                    changelog = release_info.get('body', 'No changelog available')
                    if changelog:
                        changelog = self.clean_changelog(changelog)
                else:
                    # For Python script, get commits since current version
                    changelog = self.get_latest_commits()
                    
                # Ask user if they want to update
                should_update = self.show_update_dialog(latest_version, changelog)
                if should_update:
                    self.perform_update(latest_version, release_info)
                    
                return True, latest_version
                
            return False, self.current_version if not latest_version else latest_version
            
        except Exception as e:
            if not silent:
                messagebox.showwarning("Update Check Failed", 
                                      f"Could not check for updates: {str(e)}")
            print(f"Update check failed: {e}")
            return False, None
    
    def get_latest_commits(self):
        """
        Get commit messages from the current version to the latest version
        """
        try:
            # First, try to find the commit that corresponds to the current version
            current_version_commit = self.find_commit_for_version(self.current_version)
            
            if not current_version_commit:
                # Fallback to showing a limited number of recent commits
                return self.get_recent_commits(20)
            
            # Get commits between current version and latest
            with urllib.request.urlopen(f"{self.commits_api_url}?sha=HEAD", timeout=10) as response:
                commits_info = json.loads(response.read().decode('utf-8'))
            
            # Format the commit messages
            changelog = ""
            include_commits = True
            included_count = 0
            
            for commit in commits_info:
                commit_sha = commit.get('sha', '')
                
                # Stop once we hit our current version's commit
                if commit_sha == current_version_commit:
                    break
                
                date = commit.get('commit', {}).get('author', {}).get('date', '')
                if date:
                    # Convert ISO date to more readable format
                    try:
                        date_obj = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
                        date = date_obj.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                # Get the full commit message (including description)
                message = commit.get('commit', {}).get('message', '')
                
                # Process the message:
                # If it has multiple lines, format them properly
                # Bold the first line (title)
                message_lines = message.split('\n')
                formatted_message = message_lines[0].strip()  # First line is the title
                
                # If there are more lines (description), include them with proper formatting
                if len(message_lines) > 1:
                    # Skip empty lines after the title
                    description_lines = [line for line in message_lines[1:] if line.strip()]
                    if description_lines:
                        # Add the description with proper indentation
                        description = '\n    '.join(description_lines)
                        formatted_message += f"\n    {description}"
                
                author = commit.get('commit', {}).get('author', {}).get('name', '')
                
                changelog += f"• {date} - {formatted_message}"
                if author:
                    changelog += f" ({author})"
                changelog += "\n\n"
                
                included_count += 1
            
            if included_count == 0:
                return "No new changes since your version."
            
            return changelog
        except Exception as e:
            print(f"Failed to get commit history: {e}")
            return "Could not retrieve changes since your version. Please check GitHub for details."
    
    def get_recent_commits(self, count=20):
        """
        Fallback method to get a limited number of recent commits (title only)
        """
        try:
            # Get the latest commits
            with urllib.request.urlopen(f"{self.commits_api_url}?per_page={count}", timeout=10) as response:
                commits_info = json.loads(response.read().decode('utf-8'))
                
            # Format the commit messages - titles only for brevity since we're showing many
            changelog = "(could not determine changes since your version):\n\n"
            for commit in commits_info:
                date = commit.get('commit', {}).get('author', {}).get('date', '')
                if date:
                    try:
                        date_obj = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
                        date = date_obj.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                message = commit.get('commit', {}).get('message', '')
                # Get only the first line of commit message for the fallback view
                message = message.split('\n')[0] if message else 'No message'
                
                author = commit.get('commit', {}).get('author', {}).get('name', '')
                
                changelog += f"• {date} - {message}"
                if author:
                    changelog += f" ({author})"
                changelog += "\n\n"
                
            return changelog
        except Exception as e:
            print(f"Failed to get recent commits: {e}")
            return "Could not retrieve recent changes. Please check GitHub for details."
    
    def find_commit_for_version(self, version):
        """
        Find the commit SHA that corresponds to the current version
        """
        try:
            # First try to find a tag matching our version
            with urllib.request.urlopen(f"https://api.github.com/repos/{self.github_repo}/tags", timeout=10) as response:
                tags = json.loads(response.read().decode('utf-8'))
            
            # Look for tag with our version
            for tag in tags:
                tag_name = tag.get('name', '')
                if tag_name == version:
                    return tag.get('commit', {}).get('sha', '')
            
            # If not found in releases Check version.txt commit history
            commits_url = f"https://api.github.com/repos/{self.github_repo}/commits?path=version.txt"
            with urllib.request.urlopen(commits_url, timeout=10) as response:
                commits = json.loads(response.read().decode('utf-8'))

            for commit in commits:
                sha = commit['sha']
                raw_url = f"https://raw.githubusercontent.com/{self.github_repo}/{sha}/version.txt"
                try:
                    with urllib.request.urlopen(raw_url, timeout=10) as version_file:
                        content = version_file.read().decode('utf-8').strip()
                        if content == version:
                            return sha
                except Exception as inner_err:
                    print(f"Error reading version.txt at commit {sha}: {inner_err}")
        
        except Exception as e:
            print(f"Failed to find commit for version {version}: {e}")
            return None
            
    def get_most_recent_version(self):
        """
        Find the most recent version number from the version .txt file,
        should only be used for users running the .py file
        """
        try:
            with urllib.request.urlopen(self.version_file_url, timeout=10) as response:
                latest_version = response.read().decode('utf-8').strip()
                return latest_version
        except Exception as e:
            print(f"Failed to find latest version number: {e}")
            return None

    def clean_changelog(self, changelog):
        """
        Clean up the changelog text for better display
        """
        # Remove HTML comments if any
        changelog = re.sub(r'<!--.*?-->', '', changelog, flags=re.DOTALL)
        
        # Replace multiple newlines with double newlines for better readability
        changelog = re.sub(r'\n{3,}', '\n\n', changelog)

        return changelog.strip()
    
    def show_update_dialog(self, latest_version, changelog):
        """
        Show a dialog with update information and changelog
        """
        dialog = tk.Toplevel()
        dialog.title("Update Available")
        dialog.geometry("500x400")
        dialog.grab_set()  # Make it modal
        dialog.lift() # Bring to top
        
        # Configure the dialog
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        
        # Header
        header_frame = tk.Frame(dialog)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        tk.Label(
            header_frame, 
            text=f"A new version is available: {latest_version}",
            font=("Arial", 12, "bold")
        ).pack(anchor="w")
        
        tk.Label(
            header_frame,
            text=f"You are currently using: {self.current_version}"
        ).pack(anchor="w")
        
        # Changelog
        changelog_frame = tk.Frame(dialog)
        changelog_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        
        changelog_header = "What's new:" if self.is_exe else "Recent changes:"
        tk.Label(
            changelog_frame,
            text=changelog_header,
            font=("Arial", 10, "bold")
        ).pack(anchor="w")
        
        changelog_text = tk.Text(changelog_frame, height=15, wrap="word")
        changelog_text.pack(fill="both", expand=True)
        changelog_text.insert("1.0", changelog)
        changelog_text.config(state="disabled")
        
        # Add a scrollbar
        scrollbar = tk.Scrollbar(changelog_text)
        scrollbar.pack(side="right", fill="y")
        changelog_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=changelog_text.yview)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        update_button = tk.Button(
            button_frame, 
            text="Update Now", 
            command=lambda: [dialog.destroy(), dialog.result.set(True)]
        )
        update_button.pack(side="right", padx=5)
        
        skip_button = tk.Button(
            button_frame, 
            text="Skip This Update", 
            command=lambda: [dialog.destroy(), dialog.result.set(False)]
        )
        skip_button.pack(side="right", padx=5)
        
        # Store the result
        dialog.result = tk.BooleanVar(value=False)
        
        # Wait for dialog to close
        dialog.wait_window()
        return dialog.result.get()
    
    def perform_update(self, latest_version, release_info=None):
        """
        Perform the actual update process
        """
        progress_dialog = tk.Toplevel()
        progress_dialog.title("Updating")
        progress_dialog.geometry("300x100")
        progress_dialog.grab_set()
        
        tk.Label(
            progress_dialog, 
            text=f"Downloading and installing update...",
        ).pack(pady=10)
        
        progress = tk.Label(progress_dialog, text="Please wait...")
        progress.pack(pady=10)
        
        # Run update in a separate thread to keep UI responsive
        def update_thread():
            try:
                if self.is_exe:
                    self.update_exe_version(progress, release_info)
                else:
                    self.update_py_version(progress)
                    
                progress.config(text="Update complete! Restarting...")
                progress_dialog.after(1500, self.restart_application)
                
            except Exception as e:
                progress_dialog.destroy()
                messagebox.showerror("Update Failed", 
                                    f"Error during update: {str(e)}\n\n"
                                    f"Please update manually.")
                webbrowser.open(f"https://github.com/{self.github_repo}/releases/latest")
        
        threading.Thread(target=update_thread, daemon=True).start()
        
    def update_py_version(self, progress_label):
      """
      Update all .py files in the local folder from GitHub
      """
      self.update_all_py_files(progress_label)


    def update_all_py_files(self, progress_label):
      """
      Download and replace all .py files in the current directory with latest versions from GitHub.
      """
      progress_label.config(text="Scanning for .py files...")

      # Get current script directory
      base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

      # Find all .py files 
      # (We might run in to issues updating the Updater.py itsef as this code is running while were updating it
      # python typically loads the entire script into memory before running it I think, so we ~should be fine, but might cause issues later;
      # leaving it for now as this is out of scope of this project)
      py_files = []
      for root, dirs, files in os.walk(base_dir):
          for file in files:
              if file.endswith('.py'):
                  full_path = os.path.join(root, file)
                  py_files.append(full_path)

      if not py_files:
          raise Exception("No .py files found to update.")

      progress_label.config(text="Downloading updated scripts...")

      # For every python file we find we try to find the latest verion on github, and update 
      # (This assumes the same foler structure locally as on github)
      for py_file in py_files:
          relative_path = os.path.relpath(py_file, base_dir).replace("\\", "/")
          github_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/{relative_path}"

          try:
              with urllib.request.urlopen(github_url, timeout=10) as response:
                  new_code = response.read()

              # Backup old version
              backup_path = py_file + ".backup"
              shutil.copy2(py_file, backup_path)

              # Write new version
              with open(py_file, "wb") as f:
                  f.write(new_code)

              print(f"Updated: {relative_path}")
          except Exception as e:
              print(f"Failed to update {relative_path}: {e}")

      progress_label.config(text="All scripts updated successfully.")
    
    def update_exe_version(self, progress_label, release_info=None):
        """
        Update the executable version
        """
        progress_label.config(text="Getting download information...")
        
        # Get the latest release info if not provided
        if not release_info:
            with urllib.request.urlopen(self.github_api_url, timeout=10) as response:
                release_info = json.loads(response.read().decode())
            
        # Find the asset that is the .exe file
        exe_asset = None
        for asset in release_info.get('assets', []):
            if asset['name'].endswith('.exe'):
                exe_asset = asset
                break
                
        if not exe_asset:
            raise Exception("Couldn't find executable in the latest release")
            
        # Download the new executable
        progress_label.config(text="Downloading executable...")
        download_url = exe_asset['browser_download_url']
        
        # Create a temp directory that will persist
        temp_dir = os.path.join(tempfile.gettempdir(), "slackpaint_update")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, "SlackPaint_new.exe")
        
        try:
            with urllib.request.urlopen(download_url, timeout=30) as response:
                # This could be a large file, so we'll read in chunks
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1MB chunks
                
                with open(temp_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                            
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        if total_size:
                            percent = int((downloaded / total_size) * 100)
                            progress_label.config(text=f"Downloading: {percent}%")
                            progress_label.update()  # Force update the UI
            
            # Get current executable path
            current_path = os.path.abspath(sys.executable)
            current_dir = os.path.dirname(current_path)
            current_exe = os.path.basename(current_path)
            
            # Prepare for replacement
            progress_label.config(text="Preparing installation...")
            
            # Create a batch script that will replace the exe after we exit
            bat_path = os.path.join(temp_dir, "update_slackpaint.bat")
            with open(bat_path, 'w') as f:
                f.write('@echo off\n')
                f.write('echo Updating SlackPaint...\n')
                f.write(f'cd /d "{current_dir}"\n')  # Change to the exe directory
                f.write('taskkill /F /IM "%~2" >nul 2>&1\n')  # Force close the app if still running
                f.write('timeout /t 2 /nobreak >nul\n')  # Wait 2 seconds
                f.write('echo Replacing executable...\n')
                f.write('copy /Y "%~1" "%~2" >nul\n')  # Replace the exe
                f.write('if errorlevel 1 (\n')
                f.write('  echo Update failed! Please download the new version manually.\n')
                f.write('  timeout /t 3\n')
                f.write('  exit /b 1\n')
                f.write(')\n')
                f.write('echo Starting updated application...\n')
                f.write('start "" "%~2"\n')  # Start the updated app
                f.write('timeout /t 1 /nobreak >nul\n')
                f.write('echo Cleaning up...\n')
                f.write('del "%~1" >nul 2>&1\n')  # Delete the temp file
                f.write('exit\n')
                
            # Execute the batch file
            progress_label.config(text="Finalizing update... The application will restart.")
            
            subprocess.Popen(
                ['cmd.exe', '/c', bat_path, temp_path, current_exe],
                cwd=current_dir,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # We'll now exit the application
            progress_label.config(text="Update ready. Closing application...")
            progress_label.update()
            # Wait a moment for the user to see the message
            progress_label.after(1500, lambda: os._exit(0))
            
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise e
    
    def restart_application(self):
        """
        Restart the application
        """
        try:
            if self.is_exe:
                # For exe, restart directly
                executable_path = os.path.abspath(sys.executable)
                subprocess.Popen([executable_path] + sys.argv[1:])
                # Give it time to start before we exit
                time.sleep(0.5)
                os._exit(0)
            else:
                # For Python script, restart directly
                python = sys.executable
                script = os.path.abspath(sys.argv[0])
                
                # Make sure we're passing the actual file path, not just a directory
                if os.path.isdir(script):
                    script = os.path.join(script, "SlackPaint.py")
                    
                print(f"Restarting with: {python} {script}")
                
                # Use subprocess instead of os.execl for more reliability
                subprocess.Popen([python, script] + sys.argv[1:])
                # Give it time to start before we exit
                time.sleep(0.5)
                os._exit(0)
        except Exception as e:
            print(f"Error restarting application: {e}")
            # If restart fails, just continue running current instance
            messagebox.showerror("Restart Failed", 
                             f"Could not restart application: {str(e)}\n\nUpdate was installed successfully, but you'll need to restart the application manually.")
