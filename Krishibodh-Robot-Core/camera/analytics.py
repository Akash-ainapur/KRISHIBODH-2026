import cv2
import numpy as np

# Lazy import placeholder
remove = None

def detect_plant(image):
    """
    Wrapper to choose between AI (rembg) and Color-Based detection.
    Tries AI first. If it fails (or module missing), falls back to Color.
    """
    try:
        return _detect_plant_ai(image)
    except Exception as e:
        print(f"[Analytics] AI Detection failed/unavailable ({e}). Falling back to Color Detection.")
        return _detect_plant_color(image)

def _detect_plant_ai(image):
    """
    Detects the plant using AI Background Removal (rembg).
    """
    global remove
    if remove is None:
        print("[Analytics] Loading AI Model (rembg)... This may take a moment first time.")
        try:
            from rembg import remove as rembg_remove
            remove = rembg_remove
        except ImportError as e:
            raise RuntimeError(f"rembg not installed or crashed: {e}")

    try:
        from PIL import Image
        
        # Convert OpenCV image (BGR) to PIL Image (RGB)
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        # Remove background
        output_pil = remove(pil_img)
        
        # Convert back to numpy
        output_np = np.array(output_pil)
        
        # Extract Alpha channel (Mask)
        alpha_mask = output_np[:, :, 3]
        
        # Find contours
        contours, _ = cv2.findContours(alpha_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, alpha_mask
            
        largest_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest_contour) < 500:
            return None, alpha_mask
            
        x, y, w, h = cv2.boundingRect(largest_contour)
        return (x, y, w, h), alpha_mask
        
    except Exception as e:
        raise RuntimeError(f"AI Processing Error: {e}")

def _detect_plant_color(image):
    """
    Fallback: Detects plant using Color Thresholding (Green + Brown) + Morphology.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Green Mask
    lower_green = np.array([25, 40, 40])
    upper_green = np.array([90, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)
    
    # Brown Mask
    lower_brown = np.array([10, 50, 20])
    upper_brown = np.array([30, 255, 200])
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
    
    mask_combined = cv2.bitwise_or(mask_green, mask_brown)
    
    # Morphology to merge parts
    kernel_close = np.ones((15, 15), np.uint8) 
    mask = cv2.morphologyEx(mask_combined, cv2.MORPH_CLOSE, kernel_close)
    
    kernel_dilate = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(mask, kernel_dilate, iterations=2)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, mask
        
    largest_contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest_contour) < 1000:
        return None, mask
        
    x, y, w, h = cv2.boundingRect(largest_contour)
    return (x, y, w, h), mask

def analyze_health(image, mask, bbox):
    """
    Analyzes the health of the plant within the bounding box.
    Checks for yellow/brown pixels inside the plant mask (Alpha channel).
    """
    x, y, w, h = bbox
    
    # Extract ROI
    roi = image[y:y+h, x:x+w]
    roi_mask = mask[y:y+h, x:x+w] # Alpha mask of the ROI
    
    # Convert ROI to HSV
    roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # Define range for yellow/brown (unhealthy)
    lower_yellow = np.array([15, 50, 50])
    upper_yellow = np.array([35, 255, 255])
    
    lower_brown = np.array([8, 60, 20])
    upper_brown = np.array([20, 255, 200])
    
    # Create masks for unhealthy colors
    mask_yellow = cv2.inRange(roi_hsv, lower_yellow, upper_yellow)
    mask_brown = cv2.inRange(roi_hsv, lower_brown, upper_brown)
    
    mask_unhealthy = cv2.bitwise_or(mask_yellow, mask_brown)
    
    # Only count pixels that are ACTUAL PLANT parts (where alpha > 0)
    # intersection of "unhealthy color" AND "is plant"
    real_unhealthy_pixels = cv2.bitwise_and(mask_unhealthy, mask_unhealthy, mask=roi_mask)
    
    total_plant_pixels = cv2.countNonZero(roi_mask)
    unhealthy_pixel_count = cv2.countNonZero(real_unhealthy_pixels)
    
    if total_plant_pixels == 0:
        return "Unknown", 0
    
    unhealthy_ratio = unhealthy_pixel_count / total_plant_pixels
    
    # Text status
    if unhealthy_ratio > 0.15: # If more than 15% is yellow/brown
        return "Unhealthy", int((1 - unhealthy_ratio) * 100)
    else:
        return "Healthy", int((1 - unhealthy_ratio) * 100)

def draw_analytics(image, bbox, health_status, health_score, height_px, px_per_cm, mode="all"):
    """
    Draws the bounding box and relevant info based on mode.
    mode: "height", "health", or "all"
    """
    x, y, w, h = bbox
    
    # Draw Bounding Box (Green)
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    # Calculate Height
    if px_per_cm:
        height_cm = height_px / px_per_cm
        height_text = f"Height: {height_cm:.2f} cm"
    else:
        height_text = f"Height: {height_px} px"
    
    # Prepare Labels
    label_plant = "Plant Detected"
    
    # Background for text
    cv2.putText(image, label_plant, (x, y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    if mode == "height" or mode == "all":
        cv2.putText(image, height_text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    if mode == "health" or mode == "all":
        label_health = f"{health_status} ({health_score}%)"
        color = (0, 255, 0) if health_status == "Healthy" else (0, 0, 255)
        cv2.putText(image, label_health, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return image

def draw_timestamp(image):
    """
    Draws the current date and time on the top-right corner of the image.
    """
    import datetime
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Get image width to position text at top-right
    h, w, _ = image.shape
    text_size = cv2.getTextSize(timestamp_str, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    
    text_x = w - text_size[0] - 10
    text_y = 30
    
    # Draw dark background for better visibility
    cv2.rectangle(image, (text_x - 5, text_y - 25), (w, text_y + 10), (0, 0, 0), -1)
    
    # Draw White Text
    cv2.putText(image, timestamp_str, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return image

def process_image(image, mode="all", px_per_cm=None):
    """
    Main entry point to process a single image.
    mode: "height" (Cam 0), "health" (Cam 1), or "all"
    px_per_cm: Float, for height conversion.
    Returns the processed image and stats info as a dict.
    """
    # Always draw timestamp first so it's on every analyzed image
    image = draw_timestamp(image)
    
    bbox, mask = detect_plant(image)
    
    if bbox:
        health_status, health_score = analyze_health(image, mask, bbox)
        
        # Draw analytics based on mode
        processed_image = draw_analytics(
            image.copy(), 
            bbox, 
            health_status, 
            health_score, 
            bbox[3], # height in px
            px_per_cm,
            mode
        )
        
        # Calculate final height value for stats
        height_val = bbox[3] / px_per_cm if px_per_cm else bbox[3]
        
        return processed_image, {
            "found": True,
            "height": height_val,
            "height_unit": "cm" if px_per_cm else "px",
            "status": health_status,
            "score": health_score
        }
    else:
        return image, {"found": False}
