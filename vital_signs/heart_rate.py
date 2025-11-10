"""
Heart Rate Detection Module
Uses remote photoplethysmography (rPPG) technique to detect heart rate from facial video
"""

import cv2
import numpy as np
from scipy import signal
from collections import deque


class HeartRateDetector:
    def __init__(self, buffer_size=300, fps=30):
        """
        Initialize heart rate detector

        Args:
            buffer_size: Number of frames to store for analysis
            fps: Frames per second of video input
        """
        self.buffer_size = buffer_size
        self.fps = fps
        self.green_values = deque(maxlen=buffer_size)
        self.timestamps = deque(maxlen=buffer_size)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def detect_face(self, frame):
        """
        Detect face in frame

        Args:
            frame: Input video frame

        Returns:
            Face ROI coordinates (x, y, w, h) or None
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(faces) > 0:
            return faces[0]  # Return first detected face
        return None

    def extract_forehead_roi(self, frame, face):
        """
        Extract forehead region from face for better PPG signal

        Args:
            frame: Input video frame
            face: Face coordinates (x, y, w, h)

        Returns:
            Forehead ROI
        """
        x, y, w, h = face
        # Forehead is approximately top 1/3 of face, centered
        forehead_x = x + int(w * 0.25)
        forehead_y = y + int(h * 0.1)
        forehead_w = int(w * 0.5)
        forehead_h = int(h * 0.25)

        roi = frame[forehead_y:forehead_y+forehead_h,
                   forehead_x:forehead_x+forehead_w]

        return roi, (forehead_x, forehead_y, forehead_w, forehead_h)

    def process_frame(self, frame, timestamp):
        """
        Process a video frame to extract heart rate signal

        Args:
            frame: Input video frame (BGR)
            timestamp: Timestamp of the frame

        Returns:
            dict with heart rate and processing status
        """
        face = self.detect_face(frame)

        if face is None:
            return {
                'success': False,
                'heart_rate': None,
                'message': 'No face detected',
                'roi': None
            }

        roi, roi_coords = self.extract_forehead_roi(frame, face)

        # Extract green channel (most sensitive to blood volume changes)
        green_channel = roi[:, :, 1]
        green_mean = np.mean(green_channel)

        # Add to buffer
        self.green_values.append(green_mean)
        self.timestamps.append(timestamp)

        # Need enough samples to calculate heart rate
        if len(self.green_values) < self.buffer_size * 0.8:
            return {
                'success': False,
                'heart_rate': None,
                'message': f'Collecting data... {len(self.green_values)}/{self.buffer_size}',
                'roi': roi_coords
            }

        # Calculate heart rate
        heart_rate = self.calculate_heart_rate()

        return {
            'success': True,
            'heart_rate': heart_rate,
            'message': 'Heart rate detected',
            'roi': roi_coords,
            'face': face
        }

    def calculate_heart_rate(self):
        """
        Calculate heart rate from collected green channel values using FFT

        Returns:
            Heart rate in BPM
        """
        # Detrend the signal
        signal_data = np.array(self.green_values)
        detrended = signal.detrend(signal_data)

        # Apply Hamming window
        windowed = detrended * np.hamming(len(detrended))

        # FFT
        fft_data = np.fft.rfft(windowed)
        fft_freq = np.fft.rfftfreq(len(windowed), 1.0 / self.fps)

        # Bandpass filter: 0.8 Hz to 3 Hz (48-180 BPM)
        freq_mask = (fft_freq >= 0.8) & (fft_freq <= 3.0)
        fft_data_filtered = fft_data * freq_mask

        # Find peak frequency
        power_spectrum = np.abs(fft_data_filtered) ** 2
        peak_freq_idx = np.argmax(power_spectrum)
        peak_freq = fft_freq[peak_freq_idx]

        # Convert to BPM
        heart_rate_bpm = peak_freq * 60.0

        # Validate range
        if 45 <= heart_rate_bpm <= 200:
            return round(heart_rate_bpm, 1)

        return None

    def reset(self):
        """Reset the detector buffers"""
        self.green_values.clear()
        self.timestamps.clear()
