import sounddevice as sd
import numpy as np
import os
from scipy.fft import fft, fftfreq
import datetime
import cv2
from flask import Flask, render_template, send_file, redirect

app = Flask(__name__)

SAMPLE_RATE = 44100  # Sample rate (Hz)
DURATION = 5  # Duration of each audio chunk (seconds)
THRESHOLD = 10  # Minimum frequency
MIN_FREQ = 250  # Minimum frequency of interest (Hz)
MAX_FREQ = 5000  # Maximum frequency of interest (Hz)

video_path = None
frames = []

def audio_callback(indata, audio_frames, time, status):
    global video_path, frames

    # Apply spectral analysis on the audio chunk
    audio_data = indata.flatten()
    frequencies = fftfreq(len(audio_data)) * SAMPLE_RATE
    spectrum = np.abs(fft(audio_data))

    # Extract the relevant frequency range
    mask = np.logical_and(frequencies >= MIN_FREQ, frequencies <= MAX_FREQ)
    frequencies_of_interest = frequencies[mask]
    spectrum_of_interest = spectrum[mask]

    # Check if the spectrum contains significant energy in the frequency range
    if np.max(spectrum_of_interest) > THRESHOLD and video_path is None:
        # Print the detected information
        print("Accident noise detected!")
        print("Time:", datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"))

        # Record video
        frames = record_video()
        video_path = 'accident.mp4'


@app.route('/')
def home():
    if video_path is not None:
        return redirect('/playback')
    return render_template('index.html')

@app.route('/record')
def record():
    global video_path
    if video_path is not None:
        return redirect('/playback')
    frames = record_video()
    video_path = 'accident.mp4'
    return redirect('/playback')

@app.route('/playback')
def playback():
    return render_template('playback.html', video_path=video_path)

def record_video():
    global frames  # Declare the variable as global

    # Set video duration
    video_duration = 10  # 5 seconds before and after the accident

    # Initialize video recording
    cap = cv2.VideoCapture(0)  # Use default camera

    # Start recording
    start_time = datetime.datetime.now()
    while (datetime.datetime.now() - start_time).total_seconds() < video_duration:
        ret, frame = cap.read()
        frames.append(frame)

        # Display the resulting frame
        cv2.imshow('Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release video recording resources
    cap.release()
    cv2.destroyAllWindows()

    # Save the frames as a video file
    video_path = 'accident.mp4'
    save_video(frames, video_path)

    return frames

def save_video(frames, output_path):
    if len(frames) > 0:
        frame_height, frame_width, _ = frames[0].shape
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc('H', '2', '6', '4'), 30, (frame_width, frame_height))
        for frame in frames:
            out.write(frame)
        out.release()

        # Move the video file to the template folder
        template_folder = os.path.join(app.root_path, 'templates')
        new_video_path = os.path.join(template_folder, os.path.basename(output_path))
        
        if os.path.exists(new_video_path):
            os.remove(new_video_path)  # Remove the existing file
            
        os.rename(output_path, new_video_path)



if __name__ == '__main__':
    # Start audio recording
    stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLE_RATE)
    stream.start()

    # Start Flask application
    app.run()

    # Stop audio recording
    stream.stop()
