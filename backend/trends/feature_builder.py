import numpy as np

def normalize_features(feature_vectors):
    """
    Min-max normalization for k-NN
    """
    min_vals = feature_vectors.min(axis=0)
    max_vals = feature_vectors.max(axis=0)
    return (feature_vectors - min_vals) / (max_vals - min_vals + 1e-8)
