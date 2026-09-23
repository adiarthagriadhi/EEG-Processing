import av
import numpy as np


def iter_frames(path, fmt="rgb24", step=None):
    """(waktu_PTS_detik, ndarray) per frame. Video browser bersifat VFR, jadi waktu
    selalu diambil dari PTS. `step` (detik) = ambil sampel paling rapat tiap `step`."""
    next_t = 0.0
    with av.open(str(path)) as c:
        for fr in c.decode(video=0):
            if fr.time is None:
                continue
            if step is not None:
                if fr.time < next_t:
                    continue
                next_t = fr.time + step
            yield fr.time, fr.to_ndarray(format=fmt)


def crop(img, box):
    x0, y0, x1, y1 = box
    return np.ascontiguousarray(img[y0:y1, x0:x1])
