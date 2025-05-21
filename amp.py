import pyaudio
import numpy as np
import threading
import tkinter as tk
from PIL import Image, ImageTk
import os
import math
import wave 
import tkinter.filedialog as filedialog
import time

# Audio settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 22050
CHUNK = 300 

# CHUNK/RATE = 0.0136 seconds (latency)

# Record global variables
recording = False
recorded_frames = []
output_dir = r"C:\Users\AD\Documents\python\record" # Your record audio file directory here

# Initialize PyAudio
a = pyaudio.PyAudio()

# Gain settings
bass_gain = 1.0
mid_gain = 1.0
treble_gain = 1.0
master_gain = 1.0  
master_volume = 1.0  
audio_processing = True  
overdrive_on = False  
overdrive_gain = 1.0  

# Process audio data
def process_audio(data):
    audio_data = np.frombuffer(data, dtype=np.int16)
    audio_data = audio_data * master_gain * master_volume
    if overdrive_on:
        audio_data = audio_data * overdrive_gain  
    audio_data = np.clip(audio_data, -32768, 32767)  
    return audio_data.astype(np.int16).tobytes()

# Open audio streams
stream_in = a.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
stream_out = a.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
print("Starting audio processing...")

# Save the recorded audio to a file
def save_recording():
    global recorded_frames
    if not recorded_frames:
        print("No frames recorded. Skipping save.")
        return
    
    os.makedirs(output_dir, exist_ok=True)  
    file_name = f"recording_{int(time.time())}.wav"
    file_path = os.path.join(output_dir, file_name)

    try:
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(a.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(recorded_frames))
        print(f"Recording saved to: {file_path}")
    except Exception as e:
        print(f"Error saving recording: {e}")

# Audio thread function
def audio_thread_func():
    global recorded_frames
    while True:
        if audio_processing:
            try:
                input_data = stream_in.read(CHUNK, exception_on_overflow=False)
                processed_data = process_audio(input_data)
                stream_out.write(processed_data)  
                if recording:
                    recorded_frames.append(processed_data)  
            except Exception as e:
                print(f"Error in audio processing: {e}")

# Toggle recording
def toggle_recording():
    global recording, recorded_frames
    if recording:
        recording = False
        record_button.config(text="Start Recording")
        save_recording() 
    else:
        recorded_frames = [] 
        recording = True
        record_button.config(text="Stop Recording")
        
# Audio info text output
def update_output_label():
    global output_label
    output_text = (
        f"Master Volume: {master_volume:.1f}, Gain: {master_gain:.1f}, "
        f"Treble: {treble_gain:.1f}, Mid: {mid_gain:.1f}, Bass: {bass_gain:.1f}, "
        f"Overdrive Gain: {overdrive_gain:.1f}"
    )
    if output_label:
        output_label.config(text=output_text)

# Function to adjust gains
def adjust_gain(param, value):
    global bass_gain, mid_gain, treble_gain, master_gain, master_volume, overdrive_gain
    if param == 'bass':
        bass_gain = value
    elif param == 'mid':
        mid_gain = value
    elif param == 'treble':
        treble_gain = value
    elif param == 'gain':
        master_gain = value
    elif param == 'volume':
        master_volume = value 
    elif param == 'overdrive_gain':
        overdrive_gain = value
    update_output_label()

# Toggle standby
def toggle_standby():
    global audio_processing
    audio_processing = not audio_processing
    if audio_processing:
        standby_switch_canvas.coords(toggle_rect, 5, 5, 45, 25) 
        led_label.config(bg="red")  
    else:
        standby_switch_canvas.coords(toggle_rect, 5, 25, 45, 45)  
        led_label.config(bg="darkred")  

# Toggle overdrive
def toggle_overdrive():
    global overdrive_on
    overdrive_on = not overdrive_on
    if overdrive_on:
        overdrive_led_label.config(bg="red")  
    else:
        overdrive_led_label.config(bg="darkred")  

# Knobs
class Knob:
    def __init__(self, master, x, y, param, radius=30):
        self.master = master
        self.radius = radius
        self.angle = 0  
        self.value = 0
        self.param = param
        self.canvas = tk.Canvas(master, width=radius*2, height=radius*2, bg="#18171a")
        self.canvas.place(x=x, y=y)
        self.knob = self.canvas.create_oval(0, 0, radius*2, radius*2, fill='#d1d0d3', outline='black')
        self.update_knob()
        self.canvas.bind("<Button-3>", lambda e: self.rotate_knob("left"))  
        self.canvas.bind("<Button-1>", lambda e: self.rotate_knob("right"))  
        self.canvas.create_text(radius + 20, radius + 10, text="-", fill="black", font=("Arial", 19))
        self.canvas.create_text(radius - 20, radius + 10, text="+", fill="black", font=("Arial", 19))

    def update_knob(self):
        self.canvas.delete("indicator")
        indicator_length = self.radius - 5
        x_end = self.radius + indicator_length * math.cos(math.radians(self.angle))
        y_end = self.radius - indicator_length * math.sin(math.radians(self.angle))
        self.canvas.create_line(self.radius, self.radius, x_end, y_end, fill='black', width=3, tags="indicator")
        self.value = round(((self.angle + 60) / 300) * 10, 1)
        adjust_gain(self.param, self.value)

    def rotate_knob(self, direction):
        increment = 15
        if direction == "right":
            self.angle = min(240, self.angle + increment)
        elif direction == "left":
            self.angle = max(-60, self.angle - increment)
        self.update_knob()

# GUI 
def create_gui():
    global root, standby_switch_canvas, toggle_rect, led_label, output_label, overdrive_led_label, record_button
    root = tk.Tk()
    root.title("Mike's Virtual Amp")

    # Close the program when the window is closed
    def on_close():
        print("Exiting application.")
        stream_in.stop_stream()
        stream_in.close()
        stream_out.stop_stream()
        a.terminate()
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Create canvas
    canvas_width = 3000  
    canvas_height = 1000  
    main_canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="#18171a")
    main_canvas.grid(row=0, column=0, padx=10, pady=10)

    # Output label 
    output_label = tk.Label(root, text="", fg="white", bg="#18171a", font=("Arial", 14))
    main_canvas.create_window(canvas_width // 3.2, 950, window=output_label)
    update_output_label()

   # Amp image
    amp_img_path = r"C:\Users\AD\Documents\python\amp.png" # Your amp image directory here
    amp_img = Image.open(amp_img_path)
    amp_img_resized = amp_img.resize((900, 800))  
    amp_img_tk = ImageTk.PhotoImage(amp_img_resized)
    amp_label = tk.Label(root, image=amp_img_tk)
    amp_label.image = amp_img_tk
    main_canvas.create_window(canvas_width // 6.1, 500, window=amp_label)
    
    # Overdrive Image
    od_img_path = r"C:\Users\AD\Documents\python\overdrive.jpg" # Your overdrive image directory here
    od_img = Image.open(od_img_path)
    od_img_resized = od_img.resize((175, 425))
    od_img_tk = ImageTk.PhotoImage(od_img_resized)

    od_label = tk.Label(root, image=od_img_tk)
    od_label.image = od_img_tk 
    main_canvas.create_window(1100, 500, window=od_label)

    # Standby switch
    standby_switch_canvas = tk.Canvas(root, width=50, height=50, bg="#18171a", highlightthickness=0)
    standby_switch_canvas.place(x=810, y=242)
    standby_switch_canvas.create_rectangle(5, 5, 45, 45, fill="#d1d0d3", outline="gray", width=2)
    toggle_rect = standby_switch_canvas.create_rectangle(5, 5, 45, 25, fill="black", outline="gray")
    standby_switch_canvas.bind("<Button-1>", lambda e: toggle_standby())

    # LED standby
    led_label = tk.Label(root, width=2, height=1, bg="red", relief="sunken", borderwidth=2) 
    led_label.place(x=826, y=217)

    # Overdrive toggle button
    overdrive_button = tk.Button(root, text="Overdrive", command=toggle_overdrive, bg="#d1d0d3", font=("Arial", 9))
    main_canvas.create_window(1100, 604, window=overdrive_button)

    # Overdrive LED
    overdrive_led_label = tk.Label(root, width=2, height=1, bg="darkred", relief="sunken", borderwidth=2)
    overdrive_led_label.place(x=1100, y=436)

    # Record button
    record_button = tk.Button(root, text="Start Recording", command=toggle_recording, bg="#d1d0d3", font=("Arial", 9))
    record_button.place(x=134, y=955)

    # Exit Button
    exit_button = tk.Button(root, text="Exit", command=on_close, width=10, height=2, bg="#d1d0d3")
    exit_button.place(x=45, y=950)

    # Knobs
    Knob(root, x=188, y=229, param='volume')
    Knob(root, x=258, y=229, param='gain')
    Knob(root, x=548, y=229, param='bass')
    Knob(root, x=413, y=229, param='treble')
    Knob(root, x=481, y=229, param='mid')
    Knob(root, x=1080, y=332, param='overdrive_gain')

    root.mainloop()

# Start audio thread and GUI
audio_thread = threading.Thread(target=audio_thread_func)
audio_thread.daemon = True
audio_thread.start()

create_gui()
