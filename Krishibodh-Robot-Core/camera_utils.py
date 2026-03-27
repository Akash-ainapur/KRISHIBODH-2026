import cv2
import time
import os
import threading
from datetime import datetime

# Try to import analytics from the camera folder
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'camera'))
    import analytics
except ImportError:
    analytics = None
    print("Warning: Analytics module not found in camera/ folder.")

class CameraHandler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CameraHandler, cls).__new__(cls)
                    cls._instance.side_cam_index = 0
                    cls._instance.top_cam_index = 1
                    cls._instance.save_dir = os.path.join(os.path.dirname(__file__), 'captured_images')
                    if not os.path.exists(cls._instance.save_dir):
                        os.makedirs(cls._instance.save_dir)
        return cls._instance

    def capture_dual_analysis(self, output_dir=None):
        """
        Captures from both cameras, runs analytics (Side->Height, Top->Health).
        Saves raw and analyzed images to output_dir (or default save_dir).
        Returns a dict with paths and stats.
        """
        # Ensure directory exists for this experiment if provided
        target_dir = output_dir if output_dir else self.save_dir
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # 1. Enumerate available cameras
        print(f"DEBUG: Attempting capture from indices {self.side_cam_index} & {self.top_cam_index}")
        
        # First, enumerate all available cameras
        available_cameras = []
        for i in range(10):  # Check first 10 indices
            test_cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if test_cap.isOpened():
                available_cameras.append(i)
                test_cap.release()
        
        print(f"DEBUG: Available camera indices: {available_cameras}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            "timestamp": timestamp,
            "side": {"raw": None, "analyzed": None, "stats": None},
            "top": {"raw": None, "analyzed": None, "stats": None}
        }

        # 2. CAPTURE SIDE CAMERA (INDEX 0) - Sequential to avoid conflicts
        print("DEBUG: Opening side camera...")
        cap1 = cv2.VideoCapture(self.side_cam_index, cv2.CAP_DSHOW)
        ret1 = False
        frame1 = None
        
        if cap1.isOpened():
            time.sleep(1.0)  # Warmup
            ret1, frame1 = cap1.read()
            cap1.release()  # Release immediately
            print(f"DEBUG: Side camera capture: {ret1}")
        else:
            print(f"ERROR: Failed to open Side Camera at index {self.side_cam_index}")

        # 3. CAPTURE TOP CAMERA (INDEX 1) - After releasing first camera
        print("DEBUG: Opening top camera...")
        cap2 = cv2.VideoCapture(self.top_cam_index, cv2.CAP_DSHOW)
        ret2 = False
        frame2 = None
        
        if cap2.isOpened():
            time.sleep(1.0)  # Warmup
            ret2, frame2 = cap2.read()
            cap2.release()  # Release immediately
            print(f"DEBUG: Top camera capture: {ret2}")
        else:
            print(f"WARNING: Failed to open Top Camera at index {self.top_cam_index}")


        # --- PROCESS SIDE CAM (HEIGHT) ---
        if ret1:
            raw_name = f"{timestamp}_side_raw.jpg"
            analyzed_name = f"{timestamp}_side_analyzed.jpg"
            
            # Save Raw
            raw_path = os.path.join(target_dir, raw_name)
            success = cv2.imwrite(raw_path, frame1)
            print(f"DEBUG: Saved raw image to {raw_path} - Success: {success}")
            results["side"]["raw"] = raw_name
            
            # Analyze
            if analytics:
                processed, stats = analytics.process_image(frame1, mode="height", px_per_cm=37.8)
                analyzed_path = os.path.join(target_dir, analyzed_name)
                success = cv2.imwrite(analyzed_path, processed)
                print(f"DEBUG: Saved analyzed image to {analyzed_path} - Success: {success}")
                results["side"]["analyzed"] = analyzed_name
                results["side"]["stats"] = stats
        
        # --- PROCESS TOP CAM (HEALTH) ---
        if ret2:
            raw_name = f"{timestamp}_top_raw.jpg"
            analyzed_name = f"{timestamp}_top_analyzed.jpg"
            
            # Save Raw
            raw_path = os.path.join(target_dir, raw_name)
            success = cv2.imwrite(raw_path, frame2)
            print(f"DEBUG: Saved top raw image to {raw_path} - Success: {success}")
            results["top"]["raw"] = raw_name
            
            # Analyze
            if analytics:
                processed, stats = analytics.process_image(frame2, mode="health")
                analyzed_path = os.path.join(target_dir, analyzed_name)
                success = cv2.imwrite(analyzed_path, processed)
                print(f"DEBUG: Saved top analyzed image to {analyzed_path} - Success: {success}")
                results["top"]["analyzed"] = analyzed_name
                results["top"]["stats"] = stats
        
        return results

if __name__ == "__main__":
    cam = CameraHandler()
    print(cam.capture_dual_analysis())
