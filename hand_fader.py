import cv2
import mediapipe as mp
import mido
import time

def main():
    # --- Configuration ---
    # MIDI Settings
    MIDI_PORT_NAME = 'AntigravityPort'
    CC_MODULATION = 1  # Y-Axis (Inverted)
    CC_BREATH = 2      # X-Axis
    
    # Smoothing
    EMA_ALPHA = 0.2
    
    # --- Initialization ---
    
    # MIDI Setup
    try:
        # Try creating a virtual port (works on Mac/Linux)
        midi_port = mido.open_output(MIDI_PORT_NAME, virtual=True)
        print(f"Created virtual MIDI port: {MIDI_PORT_NAME}")
    except NotImplementedError:
        # Windows fallback: connecting to an existing port
        output_names = mido.get_output_names()
        # Find a port that contains the desired name
        target_port = next((name for name in output_names if MIDI_PORT_NAME in name), None)
        
        if target_port:
             try:
                midi_port = mido.open_output(target_port)
                print(f"Connected to MIDI port: {target_port}")
             except IOError as e:
                print(f"Error: Could not open MIDI port '{target_port}': {e}")
                return
        else:
            # Fallback to the first available port (e.g. MS Synth)
            if output_names:
                 print(f"Warning: '{MIDI_PORT_NAME}' not found. Using '{output_names[0]}'.")
                 midi_port = mido.open_output(output_names[0])
            else:
                 print(f"Error: No MIDI ports found. Please install a MIDI driver or loopMIDI.")
                 return

    # MediaPipe Hands Setup
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        model_complexity=0,  # Fastest
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    # Webcam Setup
    # Trying multiple indices because 0 might be blocked or virtual
    camera_indices = [1, 0, 2, 3, 4, 5]
    cap = None
    
    for idx in camera_indices:
        print(f"Attempting to open camera index {idx}...")
        # Try DSHOW first (Windows specific, low latency)
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
             # Fallback to default
             cap = cv2.VideoCapture(idx)
             
        if cap.isOpened():
            # Try reading a frame to ensure it actually works
            ret, _ = cap.read()
            if ret:
                print(f"Successfully opened camera index {idx}")
                break
            else:
                print(f"Opened index {idx} but failed to read frame. releasing.")
                cap.release()
                cap = None
        
    if cap is None or not cap.isOpened():
        print("Error: Could not open any webcam.")
        return

    # Crucial: Minimize latency
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("Hand Fader started. Press 'q' to exit.")

    # State for EMA
    smooth_x = 0.5
    smooth_y = 0.5

    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # Flip the image horizontally for a later selfie-view display
            # and convert BGR to RGB.
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the image and find hands
            results = hands.process(rgb_frame)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Track Landmark 9 (Middle Finger MCP)
                    # Coordinates are normalized [0.0, 1.0]
                    lm = hand_landmarks.landmark[9]
                    raw_x = lm.x
                    raw_y = lm.y
                    
                    # Apply EMA Smoothing
                    # New = Alpha * Raw + (1 - Alpha) * Old
                    smooth_x = EMA_ALPHA * raw_x + (1 - EMA_ALPHA) * smooth_x
                    smooth_y = EMA_ALPHA * raw_y + (1 - EMA_ALPHA) * smooth_y
                    
                    # Clamp values 0.0-1.0 just in case
                    val_x = max(0.0, min(1.0, smooth_x))
                    val_y = max(0.0, min(1.0, smooth_y))
                    
                    # MIDI Mapping
                    # X-Axis -> CC 2 (Breath), 0-127
                    midi_val_x = int(val_x * 127)
                    
                    # Y-Axis (Inverted) -> CC 1 (Modulation), 0-127
                    # Inverted means 0.0 (top) -> 127, 1.0 (bottom) -> 0
                    midi_val_y = int((1.0 - val_y) * 127)
                    
                    # Send MIDI messages
                    msg_mod = mido.Message('control_change', control=CC_MODULATION, value=midi_val_y)
                    msg_breath = mido.Message('control_change', control=CC_BREATH, value=midi_val_x)
                    
                    midi_port.send(msg_mod)
                    midi_port.send(msg_breath)
                    
                    # Visual feedback (optional but helpful)
                    h, w, _ = frame.shape
                    cx, cy = int(smooth_x * w), int(smooth_y * h)
                    cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)
                    cv2.putText(frame, f"Mod: {midi_val_y} Breath: {midi_val_x}", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Display
            cv2.imshow('Hand Fader', frame)
            
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        hands.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Cleaned up.")

if __name__ == "__main__":
    main()
