import os
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk
import json
import threading

# =====================================================
# CONFIGURATION
# =====================================================

# ৪টি ফিল্টার প্রিসেট
FILTER_PRESETS = {
    "1. Cinematic (Darker, Sharper)": 
        'eq=brightness=-0.05:contrast=1.2:saturation=1.4,unsharp=5:5:1.0:5:5:0.0,setpts=PTS/1.05',
    
    "2. Bright & Sharpened": 
        'unsharp=5:5:1.0:5:5:0.0,eq=brightness=0.02:contrast=1.05:saturation=1.4,setpts=PTS/1.05',
    
    "3. 4K Look (High Detail & Contrast)": 
        'unsharp=5:5:1.5:5:5:0.0,eq=saturation=1.5:contrast=1.2:gamma=1.1,setpts=PTS/1.05',
    
    "4. Simple Speed Change (Safe Bypass)": 
        'setpts=PTS/1.05'
}

CONFIG_FILE = 'tt_config.json'
default_input_dir = os.path.join(os.getcwd(), "input")
OUTPUT_FOLDER = "output"

def load_config():
    """Loads configuration from tt_config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    """Saves configuration to tt_config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

class FfmpegGuiApp:
    def __init__(self, master):
        self.master = master
        master.title("TikTok Video Processor (GUI)")
        
        self.config = load_config()
        initial_ffmpeg_path = self.config.get('ffmpeg_path', '')
        
        self.ffmpeg_path = tk.StringVar(value=initial_ffmpeg_path)
        self.input_dir = tk.StringVar(value=self.config.get('input_path', default_input_dir))
        self.selected_filter_name = tk.StringVar(value=list(FILTER_PRESETS.keys())[0])
        self.processing_thread = None 
        
        # প্রসেস বার ভ্যালু
        self.progress_value = tk.DoubleVar() 

        # --- GUI Elements Setup ---
        self.setup_ffmpeg_path_row()
        self.setup_input_dir_row()
        self.setup_filter_dropdown_row()
        self.setup_log_window()
        self.setup_run_button() # Button at the end for better layout

        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)

    def setup_ffmpeg_path_row(self):
        row = ttk.Frame(self.master, padding="10 0 10 0")
        row.pack(fill='x')
        ttk.Label(row, text="FFmpeg Path:").pack(side='left', padx=5, pady=5)
        ttk.Entry(row, textvariable=self.ffmpeg_path, width=40).pack(side='left', fill='x', expand=True, padx=5, pady=5)
        ttk.Button(row, text="Browse .exe", command=self.browse_ffmpeg).pack(side='right', padx=5, pady=5)

    def setup_input_dir_row(self):
        row = ttk.Frame(self.master, padding="10 0 10 0")
        row.pack(fill='x')
        ttk.Label(row, text="Input Folder:").pack(side='left', padx=5, pady=5)
        ttk.Entry(row, textvariable=self.input_dir, width=40).pack(side='left', fill='x', expand=True, padx=5, pady=5)
        ttk.Button(row, text="Browse Folder", command=self.browse_input_dir).pack(side='right', padx=5, pady=5)
        self.input_dir.trace_add("write", lambda *args: self.save_current_config())

    def setup_filter_dropdown_row(self):
        row = ttk.Frame(self.master, padding="10 0 10 0")
        row.pack(fill='x')
        ttk.Label(row, text="Select Filter:").pack(side='left', padx=5, pady=5)
        self.filter_dropdown = ttk.Combobox(
            row,
            textvariable=self.selected_filter_name,
            values=list(FILTER_PRESETS.keys()),
            state="readonly",
            width=50
        )
        self.filter_dropdown.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.filter_dropdown.current(0)

    def setup_log_window(self):
        # Log Window
        ttk.Label(self.master, text="Processing Log:").pack(padx=10, anchor='w')
        self.log_text = tk.Text(self.master, height=10, width=60, state='disabled')
        self.log_text.pack(padx=10, pady=5, fill='both', expand=True)

        # Progress Bar
        self.progressbar = ttk.Progressbar(
            self.master, 
            orient="horizontal", 
            length=400, 
            mode="determinate",
            variable=self.progress_value
        )
        self.progressbar.pack(padx=10, pady=5, fill='x')
        self.progressbar_label = ttk.Label(self.master, text="Ready.")
        self.progressbar_label.pack(padx=10, pady=2, anchor='w')

    def setup_run_button(self):
        self.run_button = ttk.Button(self.master, text="START PROCESSING", command=self.process_videos_threaded)
        self.run_button.pack(pady=10)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + "\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.master.update()

    def save_current_config(self):
        self.config['ffmpeg_path'] = self.ffmpeg_path.get()
        self.config['input_path'] = self.input_dir.get()
        save_config(self.config)

    def browse_ffmpeg(self):
        filename = filedialog.askopenfilename(
            defaultextension=".exe",
            filetypes=[("Executable files", "*.exe")]
        )
        if filename:
            self.ffmpeg_path.set(filename)
            self.log(f"FFmpeg Path Set and Saved: {filename}")
            self.save_current_config()

    def browse_input_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_dir.set(directory)
            self.log(f"Input Directory Set and Saved: {directory}")

    # --- থ্রেডিং লজিক ---
    def check_thread(self):
        if self.processing_thread and self.processing_thread.is_alive():
            self.master.after(100, self.check_thread)
        else:
            self.run_button.config(state='normal', text="START PROCESSING")
            self.log("--- BATCH COMPLETE! ---")
            self.progressbar_label.config(text="Processing complete!") # Final update

    def process_videos_threaded(self):
        self.run_button.config(state='disabled', text="Processing...")
        self.log("\n--- Starting New Batch (GUI is now responsive) ---")
        
        # Reset progress bar
        self.progress_value.set(0)
        self.progressbar_label.config(text="Checking files...")

        self.processing_thread = threading.Thread(target=self._run_ffmpeg_process, daemon=True)
        self.processing_thread.start()
        
        self.master.after(100, self.check_thread)

    def _run_ffmpeg_process(self):
        ffmpeg_path = self.ffmpeg_path.get()
        input_dir = self.input_dir.get()
        
        selected_filter_name = self.selected_filter_name.get()
        VIDEO_FILTER_CODE = FILTER_PRESETS[selected_filter_name].replace(' ', '')

        if not os.path.exists(ffmpeg_path) or not os.path.exists(input_dir):
            self.log("❌ ERROR: Path not valid. Check FFmpeg Path and Input Folder.")
            return
        
        files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
        if not files:
            self.log("No video files found in the Input folder!")
            return

        # --- প্রসেস বার ইনিশিয়ালাইজেশন ---
        total_files = len(files)
        self.progressbar['maximum'] = total_files
        processed_count = 0
        # ---------------------------------

        for file in files:
            input_path = os.path.join(input_dir, file)
            output_path = os.path.join(OUTPUT_FOLDER, f"Fixed_{file}")

            self.log(f"Processing: {file} with filter: {selected_filter_name}...")
            
            command = [
                ffmpeg_path, '-y', '-i', input_path,
                '-vf', VIDEO_FILTER_CODE,
                '-af', 'atempo=1.05',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '128k',
                '-map_metadata', '-1',
                output_path
            ]

            try:
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log(f"✅ Done: {output_path}")
                
                # --- প্রসেস বারে আপডেট ---
                processed_count += 1
                self.progress_value.set(processed_count)
                self.progressbar_label.config(text=f"Processed {processed_count} of {total_files} videos.")
                # -------------------------
                
            except subprocess.CalledProcessError as e:
                self.log(f"❌ ERROR: FFmpeg failed for {file}. Try the 'Simple Speed Change' filter.")
                self.log(f"Filter used: {VIDEO_FILTER_CODE}")
            except Exception as e:
                self.log(f"❌ Python Error: {e}")

# --- Main App Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FfmpegGuiApp(root)
    root.mainloop()