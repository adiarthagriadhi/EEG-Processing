"""Lintasan vertikal batang tubuh partisipan per frame (MediaPipe Tasks API).
Pose dibatasi ke area partisipan; pose yang melompat jauh ditolak agar pelacak tidak
berpindah ke operator (terbukti terjadi pada uji foto setting)."""
import numpy as np

from .video import crop, iter_frames

TRUNK = [11, 12, 23, 24]      # bahu & pinggul (lutut tertutup kamen)
HIPS = [23, 24]
SHOULDERS = [11, 12]
WRISTS = [15, 16]
FEET = [27, 28, 29, 30, 31, 32]  # pergelangan kaki, tumit, ujung kaki


def track(video_path, box, model_path, frame_step=1, max_jump=0.15, select="front",
          num_poses=3, feet_margin=25, feet_tol=40, image_mode=True):
    """select="front" (perbaikan 2026-09-24): partisipan = orang dengan kaki paling BAWAH di gambar
    (berdiri di penanda lantai, paling dekat kamera); penonton di belakang kakinya lebih tinggi.
    Kontinuitas dipertahankan bila kandidat lain tidak lebih depan > feet_margin px; kandidat
    ditolak bila kakinya > feet_tol px di atas posisi kaki partisipan yang sedang berjalan
    (partisipan tidak terdeteksi → frame hilang, bukan pindah ke penonton).
    image_mode: deteksi independen per frame (RunningMode.IMAGE); mode VIDEO cenderung terus mengikuti
    orang yang sudah dilacak sehingga partisipan tidak terdeteksi ±28% frame bila ada penonton (P35).
    select="continuity": metode lama (kontinuitas kerangka + orang tertinggi saat inisialisasi)."""
    image_mode = image_mode and select == "front"
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision

    x0, y0 = box[0], box[1]
    opts = vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE if image_mode else vision.RunningMode.VIDEO,
        num_poses=num_poses, min_pose_detection_confidence=0.2, min_pose_presence_confidence=0.2,
        min_tracking_confidence=0.5)
    ts, ys, xs, motion, hip_y, sh_y, wr = [], [], [], [], [], [], []
    prev, prev_g, lost, feet_ref = None, None, 0, None
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
            # Identitas dilacak dari KESELURUHAN kerangka (33 titik), bukan ukuran batang
            # tubuh saja: saat partisipan berjongkok (agem) batang tubuhnya memendek dan
            # pengamat duduk di belakangnya (P10) bisa tampak "lebih besar".
            cand = [np.array([[q.x * w, q.y * h] for q in p]) for p in res.pose_landmarks
                    if np.mean([p[i].visibility for i in TRUNK]) > 0.5]
            ts.append(t)
            y = x = hy = sy = np.nan
            w_xy = [np.nan] * 4
            if cand and select == "front":
                feet = [L[FEET, 1].max() for L in cand]
                front = int(np.argmax(feet))
                best, ok = cand[front], True
                if prev is not None and lost <= 15:
                    d = [np.nanmean(np.linalg.norm(L - prev, axis=1)) for L in cand]
                    j = int(np.argmin(d))
                    if j != front and feet[front] - feet[j] <= feet_margin and d[j] <= max_jump * w:
                        best = cand[j]                   # sama-sama depan → pertahankan identitas
                fb = best[FEET, 1].max()
                if feet_ref is not None and fb < feet_ref - feet_tol:
                    ok = False                           # hanya penonton terlihat
                if ok:
                    feet_ref = fb if feet_ref is None else 0.95 * feet_ref + 0.05 * fb
            elif cand:
                if prev is None or lost > 15:          # (re)inisialisasi: orang tertinggi
                    best = max(cand, key=lambda L: L[:, 1].max() - L[:, 1].min())
                    ok = True
                else:
                    d = [np.nanmean(np.linalg.norm(L - prev, axis=1)) for L in cand]
                    best = cand[int(np.argmin(d))]
                    ok = min(d) <= max_jump * w
            if cand:
                if ok:
                    prev, lost = best, 0
                    x = best[TRUNK, 0].mean() + x0
                    y = best[TRUNK, 1].mean() + y0
                    hy = best[HIPS, 1].mean() + y0
                    sy = best[SHOULDERS, 1].mean() + y0
                    w_xy = list(best[WRISTS].ravel() + [x0, y0, x0, y0])
                else:
                    lost += 1
            else:
                lost += 1
            ys.append(y)
            xs.append(x)
            hip_y.append(hy)
            sh_y.append(sy)
            wr.append(w_xy)
    return dict(t=np.array(ts), trunk_y=np.array(ys), x=np.array(xs), motion=np.array(motion),
                hip_y=np.array(hip_y), shoulder_y=np.array(sh_y),
                wrists=np.array(wr))
