"""
Experiment configuration: loading, validation, and defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    seed: int = 20260715
    scale_factor: float = 0.01
    csv_slice_percent: int = 1
    slide_percent: int = 5
    window_percent: int = 10
    repetitions: int = 3
    engines: list = field(default_factory=lambda: ["duckdb"])
    methods: list = field(default_factory=lambda: ["recompute", "logical_views", "ivm"])
    scenarios: list = field(default_factory=lambda: [
        "insertion_only", "sliding_window", "preloaded_replacement_sliding"
    ])
    experiment_dir: str = ""

    def __post_init__(self):
        if not self.experiment_dir:
            self.experiment_dir = str(Path(__file__).resolve().parent.parent)
        self.validate()

    def validate(self):
        assert 100 % self.csv_slice_percent == 0, \
            f"100 must be divisible by csv_slice_percent={self.csv_slice_percent}"
        assert self.slide_percent % self.csv_slice_percent == 0, \
            f"slide_percent={self.slide_percent} must be divisible by csv_slice_percent={self.csv_slice_percent}"
        assert self.window_percent % self.csv_slice_percent == 0, \
            f"window_percent={self.window_percent} must be divisible by csv_slice_percent={self.csv_slice_percent}"
        assert self.window_percent >= self.slide_percent, \
            f"window_percent={self.window_percent} must be >= slide_percent={self.slide_percent}"
        assert 100 % self.slide_percent == 0, \
            f"100 must be divisible by slide_percent={self.slide_percent}"
        assert self.scale_factor > 0, "scale_factor must be positive"
        assert self.repetitions >= 1, "repetitions must be >= 1"
        for e in self.engines:
            assert e in ("opengauss", "duckdb"), f"Unknown engine: {e}"
        for m in self.methods:
            assert m in ("recompute", "logical_views", "ivm", "crown"), f"Unknown method: {m}"
        for s in self.scenarios:
            assert s in ("insertion_only", "sliding_window",
                         "preloaded_replacement_sliding"), f"Unknown scenario: {s}"

    @property
    def slices_per_step(self):
        return self.slide_percent // self.csv_slice_percent

    @property
    def total_slices(self):
        return 100 // self.csv_slice_percent

    @property
    def total_steps(self):
        return 100 // self.slide_percent

    @property
    def data_dir(self):
        return Path(self.experiment_dir) / "data" / f"scale_{self.scale_factor}"

    @property
    def static_dir(self):
        return Path(self.experiment_dir) / "data" / "static"

    @property
    def work_dir(self):
        return Path(self.experiment_dir) / "work"

    @property
    def sql_dir(self):
        return Path(self.experiment_dir) / "sql"

    @property
    def results_dir(self):
        return Path(self.experiment_dir) / "results"


def load_config(**overrides) -> Config:
    return Config(**overrides)
