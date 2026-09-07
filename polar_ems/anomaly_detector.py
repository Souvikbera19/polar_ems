"""Dependency-free anomaly detector with an IsolationForest-compatible role."""
from __future__ import annotations
from statistics import mean, pstdev

class AnomalyDetector:
    """Flags unexpected values using a fitted robust-enough z-score baseline.

    A production deployment may replace this class with sklearn IsolationForest while
    retaining the same `fit` and `detect` interface.
    """
    def __init__(self, threshold: float = 3.0): self.threshold=threshold; self.center=0.; self.scale=1.
    def fit(self, values: list[float]):
        self.center=mean(values) if values else 0.; self.scale=max(pstdev(values),1e-6) if len(values)>1 else 1.; return self
    def detect(self, value: float, label="measurement") -> dict:
        z=abs(value-self.center)/self.scale
        return {"anomaly":z>self.threshold,"label":label,"z_score":round(z,2),"message":f"{label} is {z:.1f} standard deviations from expected"}
