"""
Frame interval selection for anchor generation.

This module provides functions to select optimal frame intervals
for annotation based on the temporal annotation range.
"""


def select_frame_interval_auto(start_frame, end_frame, candidates, min_K, max_K):
    """
    Automatically select optimal frame interval based on frame range.

    Args:
        start_frame (int): Start frame number (e.g., 160)
        end_frame (int): End frame number (e.g., 320)
        candidates (list): List of frame interval candidates (e.g., [30, 18, 6, 3])
        min_K (int): Minimum number of anchors (e.g., 3)
        max_K (int): Maximum number of anchors (e.g., 15)

    Returns:
        int: Selected frame interval

    Example:
        >>> select_frame_interval_auto(160, 320, [30, 18, 6, 3], 3, 15)
        30  # 160 frames / 30 = 5.3 → 6 anchors (within 3-15 range)
    """
    total_frames = end_frame - start_frame

    if total_frames <= 0:
        # If interval is invalid, return first candidate
        return candidates[0] if candidates else 30

    for interval in candidates:
        # Calculate how many anchors would be generated
        # +1 for the starting anchor
        K = (total_frames // interval) + 1

        if min_K <= K <= max_K:
            return interval

    # If no suitable interval found, return the first candidate
    # (this handles edge cases)
    return candidates[0] if candidates else 30


def calculate_anchor_count(start_frame, end_frame, frame_interval):
    """
    Calculate how many anchors will be generated for given parameters.

    Args:
        start_frame (int): Start frame
        end_frame (int): End frame
        frame_interval (int): Frame interval

    Returns:
        int: Number of anchors

    Example:
        >>> calculate_anchor_count(160, 320, 30)
        6  # anchors at frames: 160, 190, 220, 250, 280, 310
    """
    total_frames = end_frame - start_frame
    if total_frames <= 0:
        return 1  # At least the start frame

    return (total_frames // frame_interval) + 1
