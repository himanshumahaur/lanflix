#ffmpeg -i input.mp4 -c copy -map 0 -f segment -segment_time 4 -reset_timestamps 1 chunks/part_%03d.mp4

import os
import cv2
import threading
import time
from collections import deque

# === CONFIGURATION ===
CHUNKS_DIR = "chunks"
BUFFER_SIZE = 3                 	# Number of chunks allowed in buffer
CHUNK_PREFIX = "part_"
CHUNK_EXT = ".mp4"
FRAME_DELAY = 33                	# ~30 fps (33ms per frame)
PREBUFFER_COUNT = 2

# === SHARED STATE ===
buffer = deque()
buffer_lock = threading.Lock()
playback_active = True
loading_complete = False


def get_chunk_list():
	"""Return sorted list of chunk filenames."""
	return sorted(
    	f for f in os.listdir(CHUNKS_DIR)
    	if f.startswith(CHUNK_PREFIX) and f.endswith(CHUNK_EXT)
	)


def buffer_loader(chunk_files):
	"""Background thread that loads video chunks into buffer."""
	global loading_complete

	for chunk_file in chunk_files:
    	if not playback_active:
        	break

    	# Wait if buffer is full
    	while True:
        	with buffer_lock:
            	if len(buffer) < BUFFER_SIZE:
                	break
        	time.sleep(0.05)

    	path = os.path.join(CHUNKS_DIR, chunk_file)
    	cap = cv2.VideoCapture(path)
    	frames = []

    	print(f"[Buffering] Loading {chunk_file}")

    	while cap.isOpened():
        	ret, frame = cap.read()
        	if not ret:
            	break
        	frames.append(frame)
    	cap.release()

    	with buffer_lock:
        	buffer.append(frames)

    	time.sleep(0.1)  # Allow player to catch up

	loading_complete = True
	print("✅ All chunks loaded into buffer.")


def wait_for_prebuffer():
	print(f"[Player] Waiting for {PREBUFFER_COUNT} chunks to prebuffer...")
	while True:
    	with buffer_lock:
        	if len(buffer) >= PREBUFFER_COUNT:
            	break
    	time.sleep(0.1)
	print("[Player] Prebuffer complete! Starting playback...")


def player():
	global playback_active

	wait_for_prebuffer()

	while playback_active:
    	with buffer_lock:
        	if buffer:
            	chunk = buffer.popleft()
        	else:
            	chunk = None

    	if chunk:
        	for frame in chunk:
            	if frame is None:
                	continue
            	cv2.imshow("Video Stream", frame)
            	key = cv2.waitKey(FRAME_DELAY) & 0xFF
            	if key == ord('q'):
                	playback_active = False
                	break
    	else:
        	if loading_complete:
            	break
        	print("[Player] Buffer empty, waiting...")
        	time.sleep(0.1)

	cv2.destroyAllWindows()


if __name__ == "__main__":
	chunks = get_chunk_list()

	loader_thread = threading.Thread(target=buffer_loader, args=(chunks,))
	loader_thread.start()

	player()

	loader_thread.join()
	print("🎉 Playback finished.")
