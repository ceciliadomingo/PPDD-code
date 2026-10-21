import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re #to use regex for word search matching words instead of substrings

# CLASS: interface to visualize JSON turns
class JSONViewer(tk.Tk):
    def __init__(self, turns_data):
        super().__init__()
        self.title("JSON Viewer")
        self.geometry("1200x800")
        self.turns_data = turns_data # Dialogue json
        self.current_index = 0 # To locate current turn

        # Search bar - find turn by TURN_ID
        self.search_frame = tk.Frame(self)
        self.search_frame.grid(row=0, column=0, columnspan=1, padx=10, pady=10, sticky="ew")
        self.search_label = tk.Label(self.search_frame, text="Search TURN_ID:")
        self.search_label.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry = tk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_button = tk.Button(self.search_frame, text="Search", command=self.search_turn)
        self.search_button.pack(side=tk.LEFT, padx=(10, 0))

        # Search bar - find word in transcript
        self.search_frame2 = tk.Frame(self)
        self.search_frame2.grid(row=0, column=1, columnspan=1, padx=10, pady=10, sticky="ew")
        self.search_label2 = tk.Label(self.search_frame2, text="Search word in transcript (searches through turns backwards):")
        self.search_label2.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry2 = tk.Entry(self.search_frame2)
        self.search_entry2.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_button2 = tk.Button(self.search_frame2, text="Search", command=self.search_word)
        self.search_button2.pack(side=tk.LEFT, padx=(10, 0))

        # Previous label and scrollbar: box showing previous turn
        self.previous_frame = tk.Frame(self)
        self.previous_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        self.previous_label = tk.Text(self.previous_frame, wrap="word", height=30, width=30, bg="lightgray")
        self.previous_label.pack(side=tk.LEFT, fill=tk.Y)
        self.previous_scrollbar = tk.Scrollbar(self.previous_frame, command=self.previous_label.yview)
        self.previous_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.previous_label.config(yscrollcommand=self.previous_scrollbar.set)

        # Current text and scrollbar: box showing current turn
        self.current_frame = tk.Frame(self)
        self.current_frame.grid(row=1, column=1, padx=10, pady=10)
        self.current_text = tk.Text(self.current_frame, wrap="word", height=30, width=70)
        self.current_text.pack(side=tk.LEFT, fill=tk.Y)
        self.current_scrollbar = tk.Scrollbar(self.current_frame, command=self.current_text.yview)
        self.current_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.current_text.config(yscrollcommand=self.current_scrollbar.set)

        # Next label and scrollbar: box showing next turn
        self.next_frame = tk.Frame(self)
        self.next_frame.grid(row=1, column=2, padx=10, pady=10, sticky="nw")
        self.next_label = tk.Text(self.next_frame, wrap="word", height=30, width=30, bg="lightgray")
        self.next_label.pack(side=tk.LEFT, fill=tk.Y)
        self.next_scrollbar = tk.Scrollbar(self.next_frame, command=self.next_label.yview)
        self.next_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.next_label.config(yscrollcommand=self.next_scrollbar.set)

        # Previous and Next buttons to navigate through turns
        self.prev_button = tk.Button(self, text="Previous", command=self.show_previous)
        self.prev_button.grid(row=2, column=0, padx=10, pady=10)

        self.next_button = tk.Button(self, text="Next", command=self.show_next)
        self.next_button.grid(row=2, column=2, padx=10, pady=10)

        # Transcript button to show the character indexes of the current turn transcript
        self.transcript_button = tk.Button(self, text="Show word indexes", command=self.show_transcript)
        self.transcript_button.grid(row=2, column=1, padx=10, pady=10)

        self.update_view()

	# Function to update the displayed turns
    def update_view(self):
        self.current_text.delete(1.0, tk.END)
        current_value = self.turns_data[self.current_index]
        self.current_text.insert(tk.END, json.dumps(current_value, indent=4))

        prev_text = ""
        if self.current_index > 0:
            prev_value = self.turns_data[self.current_index - 1]
            prev_text = json.dumps(prev_value, indent=4)
        self.previous_label.config(state=tk.NORMAL)
        self.previous_label.delete(1.0, tk.END)
        self.previous_label.insert(tk.END, prev_text)
        self.previous_label.config(state=tk.DISABLED)

        next_text = ""
        if self.current_index < len(self.turns_data) - 1:
            next_value = self.turns_data[self.current_index + 1]
            next_text = json.dumps(next_value, indent=4)
        self.next_label.config(state=tk.NORMAL)
        self.next_label.delete(1.0, tk.END)
        self.next_label.insert(tk.END, next_text)
        self.next_label.config(state=tk.DISABLED)

	# Function for the Previous button
    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_view()

	# Function for the Next button
    def show_next(self):
        if self.current_index < len(self.turns_data) - 1:
            self.current_index += 1
            self.update_view()

	# Function for the Search by TURN_ID
    def search_turn(self):
        turn_id = self.search_entry.get()
        found = False
        for index, turn in enumerate(self.turns_data):
            if str(turn['TURN_ID']) == turn_id:
                self.current_index = index
                self.update_view()
                found = True
                break
        if not found:
            messagebox.showerror("Error", f"TURN_ID {turn_id} not found.")

	# Function for the backwards word search (with optional speaker)
    def search_word(self):
        search_word_entry = self.search_entry2.get().lower()
        search_word = search_word_entry.split("*")[0] # * is used to separate word and speaker
        try:
            search_speaker = search_word_entry.split("*")[1]
        except IndexError:
            search_speaker = None
        search_word_pattern = r'\b' + re.escape(search_word) + r'\b'  # Create regex pattern for whole word match
        found = False
        start_index = self.current_index
        for index in range(start_index - 1, -1, -1):
            turn = self.turns_data[index]
            transcript = turn['TURN'].get('TRANSCRIPT', '').lower()
            # Check if speaker is specified in search terms
            if search_speaker:
                speaker = turn['TURN']['DIARIZATION'].get('SPEAKER', '').lower()
                if re.search(search_word_pattern, transcript) and (speaker == str(search_speaker)):
                    self.current_index = index
                    self.update_view()
                    found = True
                    break
            elif re.search(search_word_pattern, transcript):
                self.current_index = index
                self.update_view()
                found = True
                break
        if not found:
            messagebox.showerror("Error", f"Word {search_word} not found.")

	# Function to show the transcript with character indexes
    def show_transcript(self):
        current_value = self.turns_data[self.current_index]
        transcript = current_value['TURN'].get('TRANSCRIPT', '')
        transcript_with_indexes = '\n'.join(f"{i}: {char}" for i, char in enumerate(transcript))

        transcript_window = tk.Toplevel(self)
        transcript_window.title("Transcript")
        transcript_window.geometry("600x400")

        transcript_text = tk.Text(transcript_window, wrap="word")
        transcript_scrollbar = tk.Scrollbar(transcript_window, command=transcript_text.yview)
        transcript_text.config(yscrollcommand=transcript_scrollbar.set)

        transcript_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        transcript_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        transcript_text.insert(tk.END, transcript_with_indexes)
        transcript_text.config(state=tk.DISABLED)

# Function to load the dialogue JSON file
def load_json_file():
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, "r") as file:
            data = json.load(file)
            return data['SESSION']['TURNS']
    else:
        messagebox.showerror("Error", "Failed to load JSON file.")
        return None

# MAIN FUNCTION
def main():
    turns_data = load_json_file()
    if turns_data:
        app = JSONViewer(turns_data)
        app.mainloop()

if __name__ == "__main__":
    main()
