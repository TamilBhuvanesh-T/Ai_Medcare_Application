from collections import Counter

def interpret_knn(neighbor_labels):
    """
    Converts k-NN neighbors into an interpretable risk insight.
    """
    count = Counter(neighbor_labels)
    most_common = count.most_common(1)[0][0]

    return {
        "dominant_pattern": most_common,
        "distribution": dict(count)
    }
