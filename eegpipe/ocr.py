"""Tahap 1: timeline task dari panel HUD video (OCR). Waktu dalam detik VIDEO (PTS)."""
import os
import re
from multiprocessing.pool import ThreadPool   # bukan fork: PyAV + fork → deadlock

import numpy as np
import pandas as pd
import pytesseract
from PIL import Image
from rapidfuzz import fuzz, process

from .video import crop, iter_frames

MOVES = ["NGEED", "AGEM KANAN", "AGEM KIRI"]
PHASES = ["TURUN", "TAHAN", "NAIK"]
OTHER = ["BERSIAP", "ISTIRAHAT UTAMA", "BERDIRI RILEKS", "BERDIRI ISTIRAHAT",
         "BERDIRI FOKUS MATA TERBUKA", "BERDIRI MATA TERTUTUP"]
TASKS = MOVES + OTHER


def _is_phase(w):
    m = process.extractOne(w, PHASES, scorer=fuzz.ratio)
    return m[0] if m and m[1] >= 80 else None


def parse_label(text, min_score=85):
    """Teks OCR mentah → (task, subphase). Label dicocokkan per baris (dan gabungan 2–3
    baris untuk label multi-baris seperti 'Berdiri / Mata Tertutup'); angka countdown,
    '(30 Detik)', dan derau diabaikan."""
    lines = []
    for ln in text.upper().splitlines():
        ln = re.sub(r"\(?\d+\s*DETIK\)?", " ", ln)
        words = re.findall(r"[A-Z]{3,}", ln)
        if words:
            lines.append(words)
    if not lines:
        return "UNKNOWN", None
    phase = next((p for ws in lines for w in ws if (p := _is_phase(w))), None)
    cands = []
    for i in range(len(lines)):
        for k in (1, 2, 3):
            ws = [w for ln in lines[i:i + k] for w in ln if not _is_phase(w)]
            if ws:
                cands.append(" ".join(ws))
    best = max(((t, fuzz.token_sort_ratio(c, t)) for c in cands for t in TASKS),
               key=lambda x: x[1], default=(None, 0))
    if best[1] < min_score:
        return "UNKNOWN", None
    task = best[0]
    return task, (phase if task in MOVES else None)


def _ocr_image(g, scale=2):
    """Upscale 2× (LANCZOS): teks kecil (judul ISTIRAHAT UTAMA, sub-fase di dalam
    lingkaran) terbaca tanpa menambah waktu OCR (uji P02)."""
    g = np.asarray(Image.fromarray(g).resize((g.shape[1] * scale, g.shape[0] * scale),
                                             Image.LANCZOS))
    return pytesseract.image_to_string(g, config="--psm 6")


def run_ocr(video_path, box, coarse_step=0.5, threads=4):
    """OCR efisien: sampel kasar tiap `coarse_step`, lalu pencarian biner pada frame di
    antara dua sampel yang labelnya berbeda → batas presisi 1 frame (~33 ms).
    Mengembalikan satu baris per frame yang di-OCR (waktu PTS, teks, label)."""
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")   # tesseract 1 thread; paralel via pool
    times, crops = [], []
    for t, img in iter_frames(video_path, fmt="gray"):
        times.append(t)
        crops.append(crop(img, box))
    times = np.array(times)
    cache = {}

    def ocr_many(idx):
        idx = [i for i in dict.fromkeys(idx) if i not in cache]
        with ThreadPool(threads) as p:
            for i, txt in zip(idx, p.map(lambda i: _ocr_image(crops[i]), idx)):
                cache[i] = (txt, parse_label(txt))

    coarse = np.searchsorted(times, np.arange(0, times[-1], coarse_step))
    ocr_many(list(coarse))
    lab = lambda i: cache[i][1]
    todo = [(a, b) for a, b in zip(coarse[:-1], coarse[1:]) if lab(a) != lab(b)]
    while todo:                                   # pencarian biner, beberapa interval paralel
        mids = [(a + b) // 2 for a, b in todo if b - a > 1]
        ocr_many(mids)
        nxt = []
        for a, b in todo:
            if b - a <= 1:
                continue
            m = (a + b) // 2
            if lab(m) != lab(a):
                nxt.append((a, m))
            if lab(m) != lab(b):
                nxt.append((m, b))
        todo = nxt
    rows = [dict(frame=i, t=times[i], raw=cache[i][0], task=cache[i][1][0],
                 subphase=cache[i][1][1]) for i in sorted(cache)]
    return pd.DataFrame(rows)


def segments(samples, max_gap_sec=1.2):
    """Sampel OCR → segmen (task, subphase, start, end). UNKNOWN singkat di dalam segmen
    yang sama diabaikan. Di sekitar perubahan label, sampel sudah rapat per frame, jadi
    batas = titik tengah dua frame yang berbeda label."""
    s = samples[samples.task != "UNKNOWN"].reset_index(drop=True)
    # Panel SELALU menampilkan sub-fase (hitungan 1–8: TURUN 1–3, TAHAN 4–5, NAIK 6–8);
    # sub-fase kosong = OCR gagal membaca teks kecil → isi dengan sub-fase sebelumnya
    # dalam blok gerakan yang sama.
    block = (s.task != s.task.shift()).cumsum()
    is_move = s.task.isin(MOVES)
    s.loc[is_move, "subphase"] = s[is_move].groupby(block[is_move]).subphase.ffill()
    key = s.task + "|" + s.subphase.fillna("")
    new = (key != key.shift()) | (s.t.diff() > max_gap_sec)
    s["seg"] = new.cumsum()
    seg = s.groupby("seg").agg(task=("task", "first"), subphase=("subphase", "first"),
                               t_first=("t", "first"), t_last=("t", "last"),
                               n=("t", "size")).reset_index(drop=True)
    seg["start"] = seg.t_first
    seg["end"] = seg.t_last
    # rapatkan batas antar segmen berurutan ke titik tengahnya
    for i in range(1, len(seg)):
        gap = seg.at[i, "t_first"] - seg.at[i - 1, "t_last"]
        if gap <= max_gap_sec:
            mid = (seg.at[i, "t_first"] + seg.at[i - 1, "t_last"]) / 2
            seg.at[i - 1, "end"], seg.at[i, "start"] = mid, mid
    seg["start"] = seg.start.clip(lower=0)
    return number_reps(seg.drop(columns=["t_first", "t_last"]))


def number_reps(seg):
    """Nomor repetisi per gerakan: repetisi baru dimulai tiap TURUN."""
    seg = seg.copy()
    seg["rep"] = np.nan
    counters, current = {}, {}
    for i, r in seg.iterrows():
        if r.task in MOVES and r.subphase:
            if r.subphase == "TURUN" or r.task not in current:
                counters[r.task] = counters.get(r.task, 0) + 1
                current[r.task] = counters[r.task]
            seg.at[i, "rep"] = current[r.task]
    return seg
