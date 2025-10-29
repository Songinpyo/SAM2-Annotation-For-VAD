import os

def get_video_path(videos_dir, video_name):
    """Get full path to video file"""
    return os.path.join(videos_dir, video_name)


def get_annotation_path(output_dir, run_name, video_name, interval_idx=None):
    """Get full path to annotation output file"""
    # Remove .mp4 extension if present
    if video_name.endswith('.mp4'):
        video_name = video_name[:-4]

    # Add interval suffix if provided
    if interval_idx is not None:
        video_name = f"{video_name}_interval{interval_idx + 1}"

    output_subdir = os.path.join(output_dir, run_name)
    os.makedirs(output_subdir, exist_ok=True)

    return os.path.join(output_subdir, f"{video_name}.txt")
