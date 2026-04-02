import numpy as np
from backend.trends.knn_risk import HealthKNN
from backend.trends.feature_builder import normalize_features
from backend.trends.knn_insights import interpret_knn

# Dataset: [Total, LDL, HDL, Triglycerides]
data = np.array([
    [180, 120, 45, 150],   # Low risk
    [220, 160, 35, 200],   # Moderate risk
    [260, 190, 30, 280],   # High risk
])

labels = ["Low Risk", "Moderate Risk", "High Risk"]

normalized_data = normalize_features(data)

knn = HealthKNN(k=3)
knn.fit(normalized_data, labels)

user_profile = np.array([240, 170, 32, 230])
user_profile_norm = normalize_features(
    np.vstack([data, user_profile])
)[-1]

neighbors, distances = knn.predict(user_profile_norm)

insight = interpret_knn(neighbors)

print("k-NN Insight:")
print(insight)
