import numpy as np
from typing import List, Dict, Any, Optional


class CUSUMDetector:
    """
    Cumulative Sum (CUSUM) change-point detector for identifying abrupt shifts
    in telemetry time series (e.g., latency jumps, error rate explosions).
    """

    def __init__(self, drift: float = 0.5, threshold: float = 4.0):
        self.drift = drift
        self.threshold = threshold

    def detect_change_point(self, values: List[float]) -> Optional[int]:
        if len(values) < 5:
            return None

        arr = np.array(values, dtype=np.float64)
        mean = np.mean(arr[:5])
        std = np.std(arr[:5]) + 1e-6

        # Standardize
        z = (arr - mean) / std

        s_pos = 0.0
        for i, val in enumerate(z):
            s_pos = max(0.0, s_pos + val - self.drift)
            if s_pos > self.threshold:
                return i
        return None


cusum_detector = CUSUMDetector()
