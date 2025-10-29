def generate_anchors(t0_prime, t1_prime, dt):
    """Generate anchor frames with equal interval dt"""
    anchors = []
    t = t0_prime
    while t <= t1_prime:
        anchors.append(t)
        t += dt
    return anchors


def subsample_anchors(anchors, max_K):
    """Subsample anchors to max_K"""
    if len(anchors) <= max_K:
        return anchors

    step = len(anchors) / max_K
    subsampled = []
    for i in range(max_K):
        idx = int(i * step)
        subsampled.append(anchors[idx])

    return subsampled


def pad_anchors(anchors, min_K):
    """Pad anchors to min_K by duplicating last anchor"""
    if len(anchors) >= min_K:
        return anchors

    padded = anchors.copy()
    while len(padded) < min_K:
        padded.append(padded[-1])

    return padded
