def generate_anchors(t0_prime, t1_prime, dt):
    """Generate anchor frames with equal interval dt (DEPRECATED - use generate_anchors_by_frame)

    Always includes at least t0_prime, even if interval is very short

    NOTE: This function is kept for backward compatibility but should not be used
    for new frame-based system. Use generate_anchors_by_frame instead.
    """
    anchors = []
    t = t0_prime

    # Always include starting point
    anchors.append(t0_prime)

    # Generate additional anchors
    t = t0_prime + dt
    while t <= t1_prime:
        anchors.append(t)
        t += dt

    return anchors


def generate_anchors_by_frame(start_frame, end_frame, frame_interval, expand_frames=None):
    """
    Generate anchor frames using frame numbers directly.

    Args:
        start_frame (int): Start frame of temporal annotation (e.g., 160)
        end_frame (int): End frame of temporal annotation (e.g., 320)
        frame_interval (int): Interval between anchors in frames (e.g., 30)
        expand_frames (int, optional): Number of frames to expand on both sides.
                                       If None, defaults to 2 × frame_interval

    Returns:
        list: List of anchor frame numbers

    Example:
        >>> generate_anchors_by_frame(160, 320, 30, 60)
        [120, 150, 180, 210, 240, 270, 300, 330, 360]
        # Expanded: 160-60=100 to 320+60=380
        # Aligned to 30-frame intervals: 120, 150, 180, ...
    """
    # Logic: Start at start_frame, step by interval, force end_frame.
    # Anchors will be [start, start+dt, start+2dt, ..., end]
    # The last interval might be smaller than dt.
    
    anchors = [start_frame]
    current = start_frame + frame_interval
    
    while current < end_frame:
        anchors.append(current)
        current += frame_interval
        
    # Always include the end frame
    if end_frame > start_frame:
        anchors.append(end_frame)
        
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
    """Pad anchors to min_K by duplicating last anchor

    If anchors is empty, creates min_K anchors starting from 0
    """
    if len(anchors) >= min_K:
        return anchors

    # Handle empty anchor list (shouldn't happen with new generate_anchors, but just in case)
    if len(anchors) == 0:
        return list(range(min_K))

    padded = anchors.copy()
    while len(padded) < min_K:
        padded.append(padded[-1])

    return padded
