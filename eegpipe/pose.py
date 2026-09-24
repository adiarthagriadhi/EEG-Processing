"""Lintasan vertikal batang tubuh partisipan per frame (MediaPipe Tasks API).
Pose dibatasi ke area partisipan. Dua langkah (2026-09-24):
  detect(): semua kandidat orang per frame (≤ num_poses × 33 titik, koordinat gambar penuh) → disimpan di
            pose.npz (`cand_xy`, `cand_vis`) agar aturan pemilihan dapat diulang tanpa MediaPipe.
  select(): memilih partisipan per frame → trunk_y, x, hip_y, shoulder_y, wrists."""
import numpy as np

from .video import crop, iter_frames

TRUNK = [11, 12, 23, 24]      # bahu & pinggul (lutut tertutup kamen)
HIPS = [23, 24]
SHOULDERS = [11, 12]
WRISTS = [15, 16]
FEET = [27, 28, 29, 30, 31, 32]  # pergelangan kaki, tumit, ujung kaki


def detect(video_path, box, model_path, frame_step=1, num_poses=3, image_mode=True):
    """image_mode: deteksi independen per frame (RunningMode.IMAGE); mode VIDEO cenderung terus mengikuti
    orang yang sudah dilacak sehingga partisipan tidak terdeteksi ±28% frame bila ada penonton (P35)."""
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision

    x0, y0 = box[0], box[1]
    opts = vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE if image_mode else vision.RunningMode.VIDEO,
        num_poses=num_poses, min_pose_detection_confidence=0.2, min_pose_presence_confidence=0.2,
        min_tracking_confidence=0.5)
    ts, motion, cxy, cvis = [], [], [], []
    prev_g = None
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        for k, (t, img) in enumerate(iter_frames(video_path)):
            if k % frame_step:
                continue
            c = crop(img, box)
            h, w = c.shape[:2]
            g = c.mean(axis=2, dtype=np.float32)
            motion.append(np.nan if prev_g is None else float(np.abs(g - prev_g).mean()))
            prev_g = g
            mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=c)
            res = lm.detect(mpi) if image_mode else lm.detect_for_video(mpi, int(t * 1000))
            xy = np.full((num_poses, 33, 2), np.nan, np.float32)
            vis = np.zeros((num_poses, 33), np.float16)
            for j, p in enumerate(res.pose_landmarks[:num_poses]):
                xy[j] = [[q.x * w + x0, q.y * h + y0] for q in p]
                vis[j] = [q.visibility for q in p]
            ts.append(t)
            cxy.append(xy)
            cvis.append(vis)
    return dict(t=np.array(ts), motion=np.array(motion), cand_xy=np.array(cxy), cand_vis=np.array(cvis),
                box=np.array(box))


def select(det, select="front", max_jump=0.15, feet_margin=25, feet_tol=40, x_tol=50, edge_px=30):
    """select="front" (2026-09-24): partisipan = orang dengan kaki paling BAWAH di gambar (berdiri di penanda
    lantai, paling dekat kamera; penonton di belakang kakinya lebih tinggi). Kontinuitas dipertahankan bila
    kandidat lain tidak lebih depan > feet_margin px. Kandidat DITOLAK hanya bila kakinya > feet_tol px di atas
    DAN batang tubuhnya > x_tol px ke samping dari posisi partisipan berjalan (EMA) — penonton. Syarat kaki saja
    keliru: kaki tertutup kamen diperkirakan MediaPipe ikut naik saat jongkok (P16/P22/P23 kehilangan 27–76%
    frame gerak pada versi pertama). Kerangka dengan kaki > 2×edge_px di bawah area (ekstrapolasi MediaPipe) atau
    batang tubuh < edge_px dari tepi kiri/kanan area (operator terpotong) tidak dipertimbangkan (P16: 26 frame
    seperti ini merusak acuan kaki → 90% frame ditolak).
    select="continuity": metode lama (kontinuitas kerangka; inisialisasi = orang tertinggi)."""
    xy, vis = det["cand_xy"], det["cand_vis"].astype(float)
    bx = np.asarray(det["box"], float)
    w = float(bx[2] - bx[0])
    n = len(det["t"])
    ys, xs, hip_y, sh_y = (np.full(n, np.nan) for _ in range(4))
    wr = np.full((n, 4), np.nan)
    prev, lost, feet_ref, x_ref = None, 0, None, None
    for i in range(n):
        cand = [xy[i, j] for j in range(xy.shape[1])
                if np.isfinite(xy[i, j, 0, 0]) and vis[i, j, TRUNK].mean() > 0.5]
        if select == "front":                         # buang kerangka tak masuk akal: kaki diekstrapolasi jauh
            cand = [L for L in cand                   # di bawah area atau orang terpotong di tepi area (operator)
                    if L[FEET, 1].max() <= bx[3] + edge_px * 2 and bx[0] + edge_px < L[TRUNK, 0].mean() < bx[2] - edge_px]
        ok, best = False, None
        if cand and select == "front":
            feet = [L[FEET, 1].max() for L in cand]
            front = int(np.argmax(feet))
            best, ok = cand[front], True
            if prev is not None and lost <= 15:
                d = [np.nanmean(np.linalg.norm(L - prev, axis=1)) for L in cand]
                j = int(np.argmin(d))
                if j != front and feet[front] - feet[j] <= feet_margin and d[j] <= max_jump * w:
                    best = cand[j]                   # sama-sama depan → pertahankan identitas
            fb, xb = best[FEET, 1].max(), best[TRUNK, 0].mean()
            if feet_ref is not None and fb < feet_ref - feet_tol and abs(xb - x_ref) > x_tol:
                ok = False                           # hanya penonton terlihat
            if ok:
                feet_ref = fb if feet_ref is None else 0.95 * feet_ref + 0.05 * fb
                x_ref = xb if x_ref is None else 0.95 * x_ref + 0.05 * xb
        elif cand:
            if prev is None or lost > 15:              # (re)inisialisasi: orang tertinggi
                best, ok = max(cand, key=lambda L: L[:, 1].max() - L[:, 1].min()), True
            else:
                d = [np.nanmean(np.linalg.norm(L - prev, axis=1)) for L in cand]
                best = cand[int(np.argmin(d))]
                ok = min(d) <= max_jump * w
        if ok:
            prev, lost = best, 0
            xs[i], ys[i] = best[TRUNK, 0].mean(), best[TRUNK, 1].mean()
            hip_y[i], sh_y[i] = best[HIPS, 1].mean(), best[SHOULDERS, 1].mean()
            wr[i] = best[WRISTS].ravel()
        else:
            lost += 1
    return dict(t=det["t"], trunk_y=ys, x=xs, motion=det["motion"], hip_y=hip_y, shoulder_y=sh_y, wrists=wr)


def track(video_path, box, model_path, frame_step=1, select_mode="front", num_poses=3, image_mode=True):
    det = detect(video_path, box, model_path, frame_step, num_poses, image_mode and select_mode == "front")
    return {**det, **select(det, select_mode)}
