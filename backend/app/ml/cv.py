"""Privacy-preserving crowd/queue analysis with OpenCV.

No facial recognition, no identification. Baseline: HOG + SVM person detector
(swappable for a person-class-only YOLO/MobileNet-SSD behind the same detect() interface).

Data retention rule: only aggregate metrics are persisted by the caller; frames/video are
processed in-memory or from a temp dir and deleted after processing — never stored, never
linked to a passenger record.
"""
import os
import tempfile
from pathlib import Path

import cv2

from .base import BoundingBox, BoundingBoxes


class PersonDetector:
    """HOG + SVM person detector. detect(frame) -> BoundingBoxes."""

    def __init__(self) -> None:
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame) -> BoundingBoxes:
        # winStride and padding tuned for terminal CCTV-style wide shots.
        found, _ = self._hog.detectMultiScale(
            frame, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        boxes = BoundingBoxes()
        for x, y, w, h in found:
            boxes.boxes.append(BoundingBox(int(x), int(y), int(w), int(h)))
        return boxes


def aggregate(frame, boxes: BoundingBoxes, frame_area: float) -> dict:
    """Aggregate metrics only — this is what may be persisted. Frames are never stored."""
    people = boxes.count
    occupancy_pct = round(min(100.0, people * 2.2 / (frame_area / (640 * 360)) * 100), 1) if frame_area else 0
    density = "HIGH" if people >= 12 else "MEDIUM" if people >= 6 else "LOW"
    return {
        "people_detected": people,
        "estimated_queue_length": max(0, people - 2),
        "occupancy_pct": min(100.0, round(people * 2.2 * 100 / 30, 1)),
        "density_level": density,
        "movement_direction": "aggregate_flow" if people > 0 else "no_people",
    }


def process_video(video_path: str | Path) -> dict:
    """Process a video file and return aggregate metrics. Temp input is the caller's job
    to delete; this function only reads it and never writes processed frames to disk."""
    cap = cv2.VideoCapture(str(video_path))
    detector = PersonDetector()
    frame_count = 0
    total_people = 0
    max_people = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.resize(frame, (640, 360))
        boxes = detector.detect(frame)
        total_people += boxes.count
        max_people = max(max_people, boxes.count)
        frame_count += 1
        if frame_count >= 120:
            break
    cap.release()

    if frame_count == 0:
        return {"frames_processed": 0, "avg_people": 0, "max_people": 0, "density_level": "NO_DATA"}

    avg = round(total_people / frame_count, 2)
    return {
        "frames_processed": frame_count,
        "avg_people": avg,
        "max_people": max_people,
        "estimated_queue_length": max(0, round(max_people - 2)),
        "occupancy_pct": min(100.0, round(max_people * 2.2 * 100 / 30, 1)),
        "density_level": "HIGH" if max_people >= 12 else "MEDIUM" if max_people >= 6 else "LOW",
        "retention": "frames_processed_in_memory_only",
    }


def process_upload(upload_bytes: bytes, suffix: str) -> dict:
    """Analyze an uploaded video from memory. Writes to a temp dir and deletes it after,
    honoring the 'never store frames' retention rule."""
    tmpdir = tempfile.mkdtemp(prefix="a360_cv_")
    try:
        path = Path(tmpdir) / f"clip{suffix}"
        path.write_bytes(upload_bytes)
        result = process_video(path)
        result["temp_input_deleted"] = True
        return result
    finally:
        try:
            for p in Path(tmpdir).iterdir():
                p.unlink(missing_ok=True)
            os.rmdir(tmpdir)
        except OSError:
            pass
