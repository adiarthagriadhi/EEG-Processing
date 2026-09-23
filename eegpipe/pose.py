"""Lintasan vertikal batang tubuh partisipan per frame (MediaPipe Tasks API).
Pose dibatasi ke area partisipan; pose yang melompat jauh ditolak agar pelacak tidak
berpindah ke operator (terbukti terjadi pada uji foto setting)."""
import numpy as np

from .video import crop, iter_frames

TRUNK = [11, 12, 23, 24]      # bahu & pinggul (lutut tertutup kamen)


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
    ts, ys, xs, motion = [], [], [], []
    prev_x, prev_g = None, None
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
            cand = [(np.mean([p[i].x for i in TRUNK]) * w, np.mean([p[i].y for i in TRUNK]) * h)
                    for p in res.pose_landmarks
                    if np.mean([p[i].visibility for i in TRUNK]) > 0.5]
            ts.append(t)
            y = x = np.nan
            if cand:
                ref = prev_x if prev_x is not None else w / 2
                cx, cy = min(cand, key=lambda q: abs(q[0] - ref))
                if abs(cx - ref) <= max_jump * w:
                    prev_x, x, y = cx, cx + x0, cy + y0
            ys.append(y)
            xs.append(x)
    return dict(t=np.array(ts), trunk_y=np.array(ys), x=np.array(xs), motion=np.array(motion))
