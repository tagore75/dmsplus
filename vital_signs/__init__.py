"""
Vital Signs Detection Package
Provides modules for detecting heart rate, respiratory rate, and estimating blood pressure
"""

from .heart_rate import HeartRateDetector
from .respiratory_rate import RespiratoryRateDetector
from .blood_pressure import BloodPressureEstimator

__all__ = [
    'HeartRateDetector',
    'RespiratoryRateDetector',
    'BloodPressureEstimator'
]
