import cv2

def list_cameras():
    print("Testing camera indices 0 through 5...")
    for i in range(6):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"Index {i}: SUCCEEDED (Backend: CAP_DSHOW)")
            ret, frame = cap.read()
            if ret:
                print(f"  - Read frame success. Shape: {frame.shape}")
            else:
                print(f"  - Failed to read frame.")
            cap.release()
        else:
            # Try default backend if DSHOW fails
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"Index {i}: SUCCEEDED (Backend: CAP_DEFAULT)")
                ret, frame = cap.read()
                if ret:
                    print(f"  - Read frame success. Shape: {frame.shape}")
                else:
                     print(f"  - Failed to read frame.")
                cap.release()
            else:
                print(f"Index {i}: Failed")

if __name__ == "__main__":
    list_cameras()
