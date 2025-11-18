"""
Convert 1fps-based annotations to 30fps frame-based annotations.

Usage:
    python convert_1fps_to_30fps.py <input_file> <output_file> <target_fps>

Example:
    python convert_1fps_to_30fps.py \
        annotations/old_run/video_interval0.txt \
        annotations/new_run/video_interval0.txt \
        30
"""

import sys
import os


def convert_annotation_file(input_file, output_file, target_fps):
    """
    Convert 1fps annotation file to target fps frame numbers.

    Args:
        input_file: Path to old annotation file (second-based)
        output_file: Path to new annotation file (frame-based)
        target_fps: Target FPS (e.g., 30 for 30fps videos)
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return False

    converted_lines = []
    conversion_log = []

    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                parts = line.split(', ')

                # Parse old value (second)
                old_second = int(parts[0])

                # Convert to frame number
                new_frame = old_second * target_fps

                # Reconstruct line with new frame number
                new_parts = [str(new_frame)] + parts[1:]
                new_line = ', '.join(new_parts)

                converted_lines.append(new_line)
                conversion_log.append({
                    'line': line_num,
                    'old_second': old_second,
                    'new_frame': new_frame,
                    'entity': parts[1] if len(parts) > 1 else 'unknown',
                    'type': parts[2] if len(parts) > 2 else 'unknown'
                })

            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse line {line_num}: {line}")
                print(f"  Error: {e}")
                continue

    # Write converted file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write('\n'.join(converted_lines))

    # Print conversion summary
    print(f"\n{'='*60}")
    print(f"Conversion Complete!")
    print(f"{'='*60}")
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print(f"Target FPS: {target_fps}")
    print(f"Total annotations converted: {len(converted_lines)}")
    print(f"\n{'='*60}")
    print(f"Conversion Examples:")
    print(f"{'='*60}")

    # Show first 5 conversions as examples
    for log in conversion_log[:5]:
        print(f"Line {log['line']}: "
              f"{log['old_second']}s → Frame {log['new_frame']} "
              f"({log['entity']}, {log['type']})")

    if len(conversion_log) > 5:
        print(f"... and {len(conversion_log) - 5} more annotations")

    print(f"{'='*60}\n")

    return True


def convert_directory(input_dir, output_dir, target_fps):
    """
    Convert all annotation files in a directory.

    Args:
        input_dir: Directory containing old annotation files
        output_dir: Directory to save converted files
        target_fps: Target FPS
    """
    if not os.path.exists(input_dir):
        print(f"Error: Input directory not found: {input_dir}")
        return

    # Find all .txt files
    txt_files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]

    if not txt_files:
        print(f"No .txt files found in {input_dir}")
        return

    print(f"Found {len(txt_files)} annotation files to convert\n")

    success_count = 0
    for filename in txt_files:
        input_file = os.path.join(input_dir, filename)
        output_file = os.path.join(output_dir, filename)

        print(f"Converting: {filename}")
        if convert_annotation_file(input_file, output_file, target_fps):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Batch Conversion Complete!")
    print(f"Successfully converted: {success_count}/{len(txt_files)} files")
    print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nExamples:")
        print("  # Convert single file")
        print("  python convert_1fps_to_30fps.py old.txt new.txt 30")
        print()
        print("  # Convert entire directory")
        print("  python convert_1fps_to_30fps.py annotations/old/ annotations/new/ 30")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    target_fps = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    # Check if input is directory or file
    if os.path.isdir(input_path):
        convert_directory(input_path, output_path, target_fps)
    elif os.path.isfile(input_path):
        convert_annotation_file(input_path, output_path, target_fps)
    else:
        print(f"Error: {input_path} is neither a file nor a directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
