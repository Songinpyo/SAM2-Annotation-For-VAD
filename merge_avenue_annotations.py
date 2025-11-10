"""
Merge Avenue dataset annotations by combining intervals with small gaps.

Intervals with gaps smaller than gap_threshold (default: 90 frames = 3s at 30fps)
are merged into a single interval.
"""

def merge_intervals(intervals, gap_threshold=90):
    """
    Merge intervals if the gap between them is less than gap_threshold.

    Args:
        intervals: List of (start, end) tuples
        gap_threshold: Minimum gap in frames to keep intervals separate

    Returns:
        List of merged (start, end) tuples
    """
    if not intervals:
        return []

    # Sort intervals by start frame
    sorted_intervals = sorted(intervals, key=lambda x: x[0])

    merged = []
    current_start, current_end = sorted_intervals[0]

    for start, end in sorted_intervals[1:]:
        gap = start - current_end

        if gap <= gap_threshold:
            # Merge: extend current interval
            current_end = max(current_end, end)
        else:
            # Gap is too large: save current and start new
            merged.append((current_start, current_end))
            current_start, current_end = start, end

    # Don't forget the last interval
    merged.append((current_start, current_end))

    return merged


def main():
    input_file = "data/avenue/avenue.txt"
    output_file = "data/avenue/avenue_merge.txt"
    gap_threshold = 90  # 3 seconds at 30fps

    # Read and parse annotations
    video_intervals = {}

    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            video_num = parts[0]
            try:
                start_frame = int(parts[1])
                end_frame = int(parts[2])
            except (ValueError, IndexError):
                continue

            if video_num not in video_intervals:
                video_intervals[video_num] = []

            video_intervals[video_num].append((start_frame, end_frame))

    # Merge intervals for each video
    merged_annotations = {}

    for video_num, intervals in video_intervals.items():
        merged = merge_intervals(intervals, gap_threshold)
        merged_annotations[video_num] = merged

        print(f"Video {video_num}: {len(intervals)} intervals -> {len(merged)} merged intervals")

    # Write merged annotations
    with open(output_file, 'w') as f:
        for video_num in sorted(merged_annotations.keys()):
            for start, end in merged_annotations[video_num]:
                f.write(f"{video_num} {start} {end}\n")

    print(f"\nMerged annotations saved to: {output_file}")
    print(f"Gap threshold: {gap_threshold} frames")


if __name__ == "__main__":
    main()
