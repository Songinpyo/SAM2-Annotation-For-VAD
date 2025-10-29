import math

def select_dt_auto(interval_length, dt_candidates=[10, 4, 2, 1], min_K=3, max_K=15):
    """
    Pick the dt that gives K closest to max_K within [min_K, max_K]
    This produces more conservative (denser) sampling
    """
    best_dt = None
    best_K = 0

    for dt in dt_candidates:
        K = math.floor(interval_length / dt) + 1
        if min_K <= K <= max_K:
            # Choose dt that gives K closest to max_K
            if K > best_K:
                best_dt = dt
                best_K = K

    if best_dt is not None:
        return best_dt

    # Fallback: if nothing fits, return smallest dt
    return min(dt_candidates)
