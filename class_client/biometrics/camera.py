import time
import cv2

# formas do OpenCV conversar com a câmera no Windows, cada câmera aceita apenas um
CAMERA_BACKENDS = {"auto": cv2.CAP_ANY, "msmf": cv2.CAP_MSMF, "dshow": cv2.CAP_DSHOW}

class CameraUnavailableError(RuntimeError):
    pass

def open_camera(camera_index: int = 0, backend: str = "auto", wait_seconds: float = 20.0):
    
    capture = cv2.VideoCapture(camera_index, CAMERA_BACKENDS[backend])
    
    if not capture.isOpened():
        capture.release()

        raise CameraUnavailableError(f"Câmera {camera_index} ({backend}) não abriu.")

    deadline = time.monotonic() + wait_seconds

    while time.monotonic() < deadline:
        frame_read, frame = capture.read()

        if frame_read and is_real_frame(frame):
            return capture
        
        time.sleep(0.05)

    capture.release()

    raise CameraUnavailableError(
        f"Câmera {camera_index} ({backend}) abriu, mas não mandou imagem em {wait_seconds:.0f}s. ")

def is_real_frame(frame) -> bool:
    
    if frame is None or not frame.size:
        return False
    
    grayscale = frame.mean(axis=2) if frame.ndim == 3 else frame
    
    lit_area_fraction = float((grayscale > 25).mean())
    
    return lit_area_fraction >= 0.30

def open_video(video_path: str):
    
    capture = cv2.VideoCapture(video_path)

    if not capture.isOpened():
        raise CameraUnavailableError(f"Não consegui abrir o vídeo {video_path}.")
    
    return capture
