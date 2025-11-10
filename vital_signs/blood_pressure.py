"""
Blood Pressure Estimation Module
Estimates blood pressure using heart rate and pulse wave analysis

Note: This is an estimation based on PPG signal analysis.
For accurate blood pressure measurement, use calibrated medical devices.
"""

import numpy as np
from scipy import signal
from collections import deque


class BloodPressureEstimator:
    def __init__(self, buffer_size=300):
        """
        Initialize blood pressure estimator

        Args:
            buffer_size: Number of samples to store for analysis
        """
        self.buffer_size = buffer_size
        self.ppg_signal = deque(maxlen=buffer_size)
        self.heart_rates = deque(maxlen=50)  # Store recent HR values

        # Calibration parameters (would need personalization in production)
        self.baseline_sbp = 120  # Baseline systolic BP
        self.baseline_dbp = 80   # Baseline diastolic BP
        self.baseline_hr = 70    # Baseline heart rate

    def add_ppg_sample(self, green_value):
        """
        Add PPG signal sample

        Args:
            green_value: Green channel intensity value
        """
        self.ppg_signal.append(green_value)

    def add_heart_rate(self, heart_rate):
        """
        Add heart rate measurement

        Args:
            heart_rate: Heart rate in BPM
        """
        if heart_rate is not None:
            self.heart_rates.append(heart_rate)

    def estimate_blood_pressure(self, current_hr=None):
        """
        Estimate blood pressure from PPG signal characteristics

        Args:
            current_hr: Current heart rate (optional)

        Returns:
            dict with systolic and diastolic pressure estimates
        """
        if len(self.ppg_signal) < self.buffer_size * 0.8:
            return {
                'success': False,
                'systolic': None,
                'diastolic': None,
                'message': 'Insufficient data for estimation'
            }

        # Calculate pulse wave features
        features = self._extract_pulse_features()

        # Use heart rate if available
        if current_hr is not None:
            avg_hr = current_hr
        elif len(self.heart_rates) > 0:
            avg_hr = np.mean(list(self.heart_rates))
        else:
            avg_hr = self.baseline_hr

        # Estimate based on heart rate variation and PPG features
        # Higher HR typically correlates with higher BP
        hr_factor = (avg_hr - self.baseline_hr) / self.baseline_hr

        # PPG waveform analysis
        pulse_width_factor = features.get('pulse_width_factor', 0)
        amplitude_factor = features.get('amplitude_factor', 0)

        # Empirical estimation (simplified model)
        # In production, this would use machine learning trained on calibrated data
        systolic = self.baseline_sbp + (hr_factor * 15) + (pulse_width_factor * 10) + (amplitude_factor * 5)
        diastolic = self.baseline_dbp + (hr_factor * 8) + (pulse_width_factor * 5) + (amplitude_factor * 3)

        # Clamp to realistic ranges
        systolic = np.clip(systolic, 90, 180)
        diastolic = np.clip(diastolic, 60, 110)

        # Ensure systolic > diastolic
        if systolic <= diastolic:
            systolic = diastolic + 20

        return {
            'success': True,
            'systolic': round(systolic, 1),
            'diastolic': round(diastolic, 1),
            'message': 'Blood pressure estimated (requires calibration)',
            'pulse_pressure': round(systolic - diastolic, 1),
            'mean_arterial_pressure': round(diastolic + (systolic - diastolic) / 3, 1)
        }

    def _extract_pulse_features(self):
        """
        Extract features from PPG signal

        Returns:
            dict of pulse wave features
        """
        signal_data = np.array(self.ppg_signal)

        # Detrend and normalize
        detrended = signal.detrend(signal_data)
        normalized = (detrended - np.mean(detrended)) / (np.std(detrended) + 1e-6)

        # Find peaks (systolic points)
        peaks, properties = signal.find_peaks(
            normalized,
            height=0.3,
            distance=15,  # Minimum distance between peaks
            prominence=0.2
        )

        if len(peaks) < 2:
            return {
                'pulse_width_factor': 0,
                'amplitude_factor': 0
            }

        # Calculate pulse width (time between systolic and diastolic points)
        peak_heights = normalized[peaks]
        avg_amplitude = np.mean(peak_heights)

        # Calculate inter-peak intervals
        intervals = np.diff(peaks)
        avg_interval = np.mean(intervals) if len(intervals) > 0 else 30

        # Normalize features
        pulse_width_factor = (avg_interval - 30) / 10  # Normalized around 30 frames
        amplitude_factor = (avg_amplitude - 0.5) * 2   # Normalized around 0.5

        return {
            'pulse_width_factor': np.clip(pulse_width_factor, -1, 1),
            'amplitude_factor': np.clip(amplitude_factor, -1, 1),
            'peak_count': len(peaks)
        }

    def calibrate(self, actual_systolic, actual_diastolic, current_hr):
        """
        Calibrate the estimator with actual blood pressure reading

        Args:
            actual_systolic: Measured systolic pressure
            actual_diastolic: Measured diastolic pressure
            current_hr: Heart rate at time of measurement
        """
        self.baseline_sbp = actual_systolic
        self.baseline_dbp = actual_diastolic
        self.baseline_hr = current_hr

        return {
            'success': True,
            'message': 'Calibration updated'
        }

    def reset(self):
        """Reset the estimator buffers"""
        self.ppg_signal.clear()
        self.heart_rates.clear()
