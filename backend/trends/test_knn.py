import numpy as np
from backend.trends.knn_risk import HealthKNN

# Feature vectors: [Total Chol, LDL, HDL, Triglycerides]
data = np.array([
    [180, 120, 45, 150],  # healthier
    [220, 160, 35, 200],  # moderate risk
    [260, 190, 30, 280],  # high risk
])

labels = ["Low Risk", "Moderate Risk", "High Risk"]

knn = HealthKNN(k=2)
knn.fit(data, labels)

user_profile = [240, 170, 32, 230]
neighbors, distances = knn.predict(user_profile)

print("Similar profiles:", neighbors)
print("Distances:", distances)
