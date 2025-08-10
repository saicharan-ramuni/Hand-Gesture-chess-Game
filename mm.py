import cv2
import mediapipe as mp
import pyautogui
import random
import util
import time
from pynput.mouse import Button, Controller

# Initialize mouse controller and screen dimensions
mouse = Controller()
screen_width, screen_height = pyautogui.size()
print(f"Screen dimensions: {screen_width}x{screen_height}")

# Configure MediaPipe hands
mpHands = mp.solutions.hands
hands = mpHands.Hands(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    max_num_hands=1
)

# Add smoothing for mouse movement
class MouseSmoother:
    def __init__(self, smoothing_factor=0.5):
        self.prev_x, self.prev_y = screen_width // 2, screen_height // 2
        self.smoothing_factor = smoothing_factor
        
    def smooth_move(self, x, y):
        # Apply smoothing
        smooth_x = self.prev_x + self.smoothing_factor * (x - self.prev_x)
        smooth_y = self.prev_y + self.smoothing_factor * (y - self.prev_y)
        
        # Update previous positions
        self.prev_x, self.prev_y = smooth_x, smooth_y
        
        return int(smooth_x), int(smooth_y)

smoother = MouseSmoother(smoothing_factor=0.7)

# Add cooldown for gestures to prevent multiple triggers
last_action_time = 0
COOLDOWN_TIME = 0.5  # seconds

def move_mouse(index_finger_tip):
    """Move mouse based on index finger tip position"""
    if index_finger_tip is not None:
        # Map hand coordinates (0-1) to screen coordinates
        # Adding offsets and scaling to reach corners
        x = int(index_finger_tip.x * screen_width * 1.5)  # Increased scaling for better corner reach
        y = int(index_finger_tip.y * screen_height * 1.5)  # Increased scaling for better corner reach
        
        # Adjust position to better reach all corners
        x = max(0, min(x, screen_width - 1))
        y = max(0, min(y, screen_height - 1))
        
        # Apply smoothing
        smooth_x, smooth_y = smoother.smooth_move(x, y)
        
        # Actually move the mouse - using both methods for compatibility
        pyautogui.moveTo(smooth_x, smooth_y)
        mouse.position = (smooth_x, smooth_y)

def can_perform_action():
    global last_action_time
    current_time = time.time()
    if current_time - last_action_time >= COOLDOWN_TIME:
        last_action_time = current_time
        return True
    return False

def is_thumb_closed(hand_landmarks):
    """Check if thumb is closed (tucked in)"""
    thumb_tip = hand_landmarks.landmark[mpHands.HandLandmark.THUMB_TIP]
    thumb_ip = hand_landmarks.landmark[mpHands.HandLandmark.THUMB_IP]
    thumb_mcp = hand_landmarks.landmark[mpHands.HandLandmark.THUMB_MCP]
    index_mcp = hand_landmarks.landmark[mpHands.HandLandmark.INDEX_FINGER_MCP]
    
    # Calculate the distance between thumb tip and index MCP
    thumb_index_dist = ((thumb_tip.x - index_mcp.x)**2 + (thumb_tip.y - index_mcp.y)**2)**0.5
    
    # Check if thumb is tucked in (close to palm)
    return thumb_index_dist < 0.1  # Adjust threshold as needed

def is_left_click(landmark_list, thumb_index_dist):
    return (
            util.get_angle(landmark_list[5], landmark_list[6], landmark_list[8]) < 50 and
            util.get_angle(landmark_list[9], landmark_list[10], landmark_list[12]) > 90 and
            thumb_index_dist > 50
    )


def is_mouse_control_mode(hand_landmarks):
    """
    Check if hand is in mouse control mode:
    - Index finger is extended
    - Thumb is tucked in (closed)
    """
    # Get relevant landmarks
    index_tip = hand_landmarks.landmark[mpHands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mpHands.HandLandmark.INDEX_FINGER_PIP]
    index_mcp = hand_landmarks.landmark[mpHands.HandLandmark.INDEX_FINGER_MCP]
    
    # Check if index finger is extended
    index_extended = index_tip.y < index_pip.y < index_mcp.y
    
    # Check if thumb is tucked in
    thumb_closed = is_thumb_closed(hand_landmarks)
    
    # Mouse control mode is active when index is extended and thumb is closed
    return index_extended and thumb_closed

def detect_gesture(frame, processed):
    """Detect hand gestures and perform corresponding actions"""
    if not processed.multi_hand_landmarks:
        return
    
    # Get the first detected hand
    hand_landmarks = processed.multi_hand_landmarks[0]
    
    # Extract landmark coordinates
    landmark_list = []
    for lm in hand_landmarks.landmark:
        landmark_list.append((lm.x, lm.y))
    
    if len(landmark_list) < 21:  # Need full hand with 21 landmarks
        return
    
    # Get index finger tip for mouse movement
    index_finger_tip = hand_landmarks.landmark[mpHands.HandLandmark.INDEX_FINGER_TIP]
    thumb_tip = hand_landmarks.landmark[mpHands.HandLandmark.THUMB_TIP]
    
    # Calculate distance between thumb and index finger
    thumb_index_dist = util.get_distance([
        (thumb_tip.x, thumb_tip.y), 
        (index_finger_tip.x, index_finger_tip.y)
    ])
    
    # Check if the hand is in mouse control mode
    if is_mouse_control_mode(hand_landmarks):
        # Only move mouse if in control mode
        move_mouse(index_finger_tip)
        cv2.putText(frame, "Cursor Control ON", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Cursor Control OFF", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # Check for gesture actions
    if is_left_click(landmark_list, thumb_index_dist) and can_perform_action():
        mouse.press(Button.left)
        mouse.release(Button.left)
        cv2.putText(frame, "Left Click", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


def main():
    draw = mp.solutions.drawing_utils
    
    # Try to set camera resolution for better tracking
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # For FPS calculation
    prev_time = 0
    
    # Safe mode for pyautogui
    pyautogui.FAILSAFE = False
    
    print("Hand mouse control starting...")
    print("To control mouse: Extend index finger and keep thumb tucked")
    print("To stop control: Extend thumb")
    
    while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                break
                
            # Calculate FPS
            current_time = time.time()
            fps = 1 / (current_time - prev_time) if prev_time > 0 else 0
            prev_time = current_time
            
            # Process frame
            frame = cv2.flip(frame, 1)  # Mirror image
            
            # Convert to RGB
            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            processed = hands.process(frameRGB)

            # Draw hand landmarks if detected
            if processed.multi_hand_landmarks:
                for hand_landmarks in processed.multi_hand_landmarks:
                    draw.draw_landmarks(frame, hand_landmarks, mpHands.HAND_CONNECTIONS)
                
                # Detect gestures and move mouse
                detect_gesture(frame, processed)
            else:
                cv2.putText(frame, "No hand detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Display FPS
            cv2.putText(frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Display instructions
            cv2.putText(frame, "Index finger: Move", (10, frame.shape[0] - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Thumb out: Stop control", (10, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Display frame
            cv2.imshow('Hand Mouse Control', frame)
            
            # Exit on 'q' press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

if __name__ == '__main__':
    main()
