"""
Respiratory Rate Detection Module
Detects breathing rate by analyzing chest/shoulder movement
"""

import cv2
import numpy as np
from scipy import signal
from collections import deque
import mediapipe as mp


class RespiratoryRateDetector:
    def __init__(self, buffer_size=300, fps=30):
        """
        Initialize respiratory rate detector

        Args:
            buffer_size: Number of frames to store for analysis
            fps: Frames per second of video input
        """
        self.buffer_size = buffer_size
        self.fps = fps
        self.motion_values = deque(maxlen=buffer_size)
        self.timestamps = deque(maxlen=buffer_size)

        # Initialize MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def process_frame(self, frame, timestamp):
        """
        Process a video frame to extract respiratory signal

        Args:
            frame: Input video frame (BGR)
            timestamp: Timestamp of the frame

        Returns:
            dict with respiratory rate and processing status
        """
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame
        results = self.pose.process(rgb_frame)

        if not results.pose_landmarks:
            return {
                'success': False,
                'respiratory_rate': None,
                'message': 'No body pose detected',
                'landmarks': None
            }

        # Extract shoulder landmarks
        landmarks = results.pose_landmarks.landmark
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]

        # Calculate midpoint of shoulders (chest area)
        chest_y = (left_shoulder.y + right_shoulder.y) / 2
        chest_x = (left_shoulder.x + right_shoulder.x) / 2

        # Track vertical movement (breathing causes chest to rise/fall)
        self.motion_values.append(chest_y)
        self.timestamps.append(timestamp)

        # Need enough samples to calculate respiratory rate
        if len(self.motion_values) < self.buffer_size * 0.8:
            return {
                'success': False,
                'respiratory_rate': None,
                'message': f'Collecting data... {len(self.motion_values)}/{self.buffer_size}',
                'landmarks': results.pose_landmarks
            }

        # Calculate respiratory rate
        respiratory_rate = self.calculate_respiratory_rate()

        return {
            'success': True,
            'respiratory_rate': respiratory_rate,
            'message': 'Respiratory rate detected',
            'landmarks': results.pose_landmarks
        }

    def calculate_respiratory_rate(self):
        """
        Calculate respiratory rate from chest movement using FFT

        Returns:
            Respiratory rate in breaths per minute
        """
        # Detrend the signal
        signal_data = np.array(self.motion_values)
        detrended = signal.detrend(signal_data)

        # Apply Hamming window
        windowed = detrended * np.hamming(len(detrended))

        # FFT
        fft_data = np.fft.rfft(windowed)
        fft_freq = np.fft.rfftfreq(len(windowed), 1.0 / self.fps)

        # Bandpass filter: 0.1 Hz to 0.5 Hz (6-30 breaths per minute)
        freq_mask = (fft_freq >= 0.1) & (fft_freq <= 0.5)
        fft_data_filtered = fft_data * freq_mask

        # Find peak frequency
        power_spectrum = np.abs(fft_data_filtered) ** 2
        peak_freq_idx = np.argmax(power_spectrum)
        peak_freq = fft_freq[peak_freq_idx]

        # Convert to breaths per minute
        respiratory_rate_bpm = peak_freq * 60.0

        # Validate range (normal: 12-20, acceptable: 8-35)
        if 8 <= respiratory_rate_bpm <= 35:
            return round(respiratory_rate_bpm, 1)

        return None

    def reset(self):
        """Reset the detector buffers"""
        self.motion_values.clear()
        self.timestamps.clear()

    def __del__(self):
        """Cleanup MediaPipe resources"""
        self.pose.close()
