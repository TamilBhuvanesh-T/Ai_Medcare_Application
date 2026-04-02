import numpy as np
from sklearn.neighbors import NearestNeighbors

class HealthKNN:
    def __init__(self, k=3):
        self.k = k
        self.model = NearestNeighbors(n_neighbors=k, metric='euclidean')
        self.features = None
        self.labels = None

    def fit(self, feature_vectors, labels):
        self.features = feature_vectors
        self.labels = labels
        self.model.fit(feature_vectors)

    def predict(self, user_vector):
        distances, indices = self.model.kneighbors([user_vector])
        neighbor_labels = [self.labels[i] for i in indices[0]]
        return neighbor_labels, distances[0]
