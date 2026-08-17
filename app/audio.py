import json
import subprocess


def run_ffprobe(file_path):
    """Get audio metadata using ffprobe."""

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,bit_rate:stream=codec_type,sample_rate,bit_rate",
        "-of",
        "json",
        str(file_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def get_loudness(file_path):
    """Measure integrated loudness using FFmpeg loudnorm."""

    command = [
        "ffmpeg",
        "-i",
        str(file_path),
        "-af",
        "loudnorm=print_format=json",
        "-f",
        "null",
        "-",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    output = result.stderr

    start = output.rfind("{")
    end = output.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        loudness_data = json.loads(
            output[start:end + 1]
        )

        return float(loudness_data["input_i"])

    except (
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ):
        return None


def estimate_quality(
    duration,
    sample_rate,
    bitrate,
    loudness,
):
    """
    Rough quality estimate.

    This is a heuristic, not a scientific noise measurement.
    """

    if duration is None:
        return "unknown"

    if duration < 0.5:
        return "very_short"

    if sample_rate is not None and sample_rate < 16000:
        return "low_sample_rate"

    if bitrate is not None and bitrate < 32000:
        return "low_bitrate"

    if loudness is not None and loudness < -40:
        return "very_quiet"

    return "acceptable"


def get_audio_metadata(file_path):
    """
    Extract the required audio properties:

    - duration
    - sample rate
    - bitrate
    - loudness
    - rough quality estimate
    """

    data = run_ffprobe(file_path)

    duration = None
    bitrate = None
    sample_rate = None

    # ---------------------------------------------
    # Format-level information
    # ---------------------------------------------

    format_data = data.get("format", {})

    if format_data.get("duration"):
        duration = float(format_data["duration"])

    if format_data.get("bit_rate"):
        bitrate = int(float(format_data["bit_rate"]))

    # ---------------------------------------------
    # Audio stream information
    # ---------------------------------------------

    streams = data.get("streams", [])

    for stream in streams:

        if stream.get("codec_type") != "audio":
            continue

        if stream.get("sample_rate"):
            sample_rate = int(
                stream["sample_rate"]
            )

        # Prefer stream bitrate if format bitrate
        # wasn't available.
        if bitrate is None and stream.get("bit_rate"):
            bitrate = int(
                float(stream["bit_rate"])
            )

        break

    # ---------------------------------------------
    # Loudness
    # ---------------------------------------------

    loudness = get_loudness(file_path)

    # ---------------------------------------------
    # Quality estimate
    # ---------------------------------------------

    quality = estimate_quality(
        duration,
        sample_rate,
        bitrate,
        loudness,
    )

    return {
        "duration_seconds": duration,
        "sample_rate_hz": sample_rate,
        "bitrate_bps": bitrate,
        "loudness_db": loudness,
        "noise_estimate": quality,
    }