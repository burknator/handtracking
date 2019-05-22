from typing import Dict, Any, List
from itertools import product

import yaml, numpy as np

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

class _CalibrationConfig(Dict[str, Any]):
    pass

class Calibration:
    """Represents a calibration file created by calibration.cpp
    
    Required fields of a calibration file are listed in `required_fields`."""

    required_fields = ["camera_matrix", "distortion_coefficients", "ml"]

    def __init__(self, file_):
        self.camera_matrix: List[List[float]]
        self.ml: float
        self.dist_coeffs: List[List[float]]
        self._load_file(file_)

    def _check_for_required_fields(self, calibration_config: _CalibrationConfig):
        missing_fields = [f for f in self.required_fields if f not in calibration_config]
        if missing_fields:
            raise ValueError("The calibration file needs these fields: {}".format(missing_fields))

    def _get_matrix(self, config: _CalibrationConfig):
        try:
            matrix: List[List[float]] = [[] for i in range(config["rows"])]
            for row_idx, col_idx in product(range(config["rows"]), range(config["cols"])):
                matrix[row_idx].append(config["data"][row_idx + col_idx])
            return np.array(matrix)
        except:
            raise ValueError("The matrix doesn't have the correct format. It needs rows, cols and"
                             " data.")

    def _load_file(self, file_):
        calibration: _CalibrationConfig = yaml.load(file_, Loader=Loader)

        self._check_for_required_fields(calibration)

        self.camera_matrix = self._get_matrix(calibration["camera_matrix"])
        self.dist_coeffs = self._get_matrix(calibration["distortion_coefficients"])
        self.ml = calibration["ml"]
