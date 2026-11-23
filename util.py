def bars_to_beats(bars, signature_numerator):
    try:
        bar_count = int(bars)
    except (TypeError, ValueError):
        return None

    try:
        signature = int(signature_numerator) if signature_numerator else 4
    except (TypeError, ValueError):
        signature = 4

    return max(0, bar_count - 1) * signature


def bars_beats_to_position(bars, beats, signature_numerator):
    base = bars_to_beats(bars, signature_numerator)
    if base is None:
        return None
    try:
        beat_offset = max(0, int(beats) - 1)
    except (TypeError, ValueError):
        beat_offset = 0
    return base + beat_offset
