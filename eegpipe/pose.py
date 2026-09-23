"""Lintasan vertikal batang tubuh partisipan per frame (MediaPipe Tasks API).
Pose dibatasi ke area partisipan; pose yang melompat jauh ditolak agar pelacak tidak
berpindah ke operator (terbukti terjadi pada uji foto setting)."""
import numpy as np

from .video import crop, iter_frames

TRUNK = [11, 12, 23, 24]      # bahu & pinggul (lutut tertutup kamen)
HIPS = [23, 24]
SHOULDERS = [11, 12]
WRISTS = [15, 16]


def track(video_path, box, model_path, frame_step=1, max_jump=0.15):
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision

    x0, y0 = box[0], box[1]
    opts = vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO, num_poses=2,
        min_pose_detection_confidence=0.2, min_pose_presence_confidence=0.2,
        min_tracking_confidence=0.5)
    ts, ys, xs, motion, hip_y, sh_y, wr = [], [], [], [], [], [], []
    prev, prev_g, lost = None, None, 0
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        for k, (t, img) in enumerate(iter_frames(video_path)):
            if k % frame_step:
                continue
            c = crop(img, box)
            h, w = c.shape[:2]
            g = c.mean(axis=2, dtype=np.float32)
            motion.append(np.nan if prev_g is None else float(np.abs(g - prev_g).mean()))
            prev_g = g
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=c),
                                      int(t * 1000))
            # Identitas dilacak dari KESELURUHAN kerangka (33 titik), bukan ukuran batang
            # tubuh saja: saat partisipan berjongkok (agem) batang tubuhnya memendek dan
            # pengamat duduk di belakangnya (P10) bisa tampak "lebih besar".
            cand = [np.array([[q.x * w, q.y * h] for q in p]) for p in res.pose_landmarks
                    if np.mean([p[i].visibility for i in TRUNK]) > 0.5]
            ts.append(t)
            y = x = hy = sy = np.nan
            w_xy = [np.nan] * 4
            if cand:
                if prev is None or lost > 15:          # (re)inisialisasi: orang tertinggi
                    best = max(cand, key=lambda L: L[:, 1].max() - L[:, 1].min())
                    ok = True
                else:
                    d = [np.nanmean(np.linalg.norm(L - prev, axis=1)) for L in cand]
                    best = cand[int(np.argmin(d))]
                    ok = min(d) <= max_jump * w
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
