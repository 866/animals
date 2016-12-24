import numpy as np
import cv2
import time
import os

# Constants
ALPHA = 0.05
DIFF_THRESHOLD = 2
MINTIME_STOP = 30  # in seconds
FRAMES_AVERAGE = 10 # initial number of frames to average in order to find the background
FOURCC = cv2.cv.CV_FOURCC(*'XVID') # Video codec
OUTPUT_FOLDER = "./output" # Folder where the files will be stored
FPS = 8


# Processes image
def filter_image(img):
    blur = cv2.GaussianBlur(img, (25, 25), 0)
    return blur


def diff_sum(diff, points):
    return np.sum(np.sum(diff)) / points


def motion_detector(image, finished, write_video_flag, frame_shape, delay=0.5):

    print("Motion detector started")

    # Find frames for averaging
    frames = np.ndarray((FRAMES_AVERAGE, frame_shape[0], frame_shape[1]), dtype=np.float32)
    for i in range(FRAMES_AVERAGE):
        gray_frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        frames[i] = gray_frame
        time.sleep(delay)

    # Find the background
    background = np.mean(frames, axis=0)
    background = filter_image(background).astype(dtype=np.float16)
    del frames

    # Number of pixels
    ptx = frame_shape[0] * frame_shape[1]

    # Iterate until not finished
    while not finished.value:

        # Process image
        gray_frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processed_frame = filter_image(gray_frame)

        # Find the difference
        diff_frame = np.abs(processed_frame - background).astype(dtype=np.uint8)
        diff_scalar = diff_sum(diff_frame, ptx)

        # Mix background and a bit of a new object
        background = ALPHA * processed_frame + (1 - ALPHA) * background

        # Check if we exceeded moving threshold
        if diff_scalar > DIFF_THRESHOLD:
            if not write_video_flag.value:
                write_video_flag.value = True
                time.sleep(MINTIME_STOP)
        elif diff_scalar < DIFF_THRESHOLD:
            if write_video_flag.value:
                write_video_flag.value = False

        time.sleep(delay)


def writer(image, finished, write_video_flag, frame_shape, delay=1 / 8.):

    print("Writer started")

    # Check if correct path is specified and create dir if it
    # does not exist
    if not os.path.isdir(OUTPUT_FOLDER):
        try:
            os.mkdir(OUTPUT_FOLDER)
        except OSError:
            print("Incorrect output path is specified")
            exit(-1)

    # Iterate until not finished
    while True:

        # Wait for external order to write video
        while not write_video_flag.value:
            if finished.value:
                return
            time.sleep(delay)

        # Initialize a video writer
        datetime = time.strftime("%m|%d_%H:%M:%S.avi")
        output_path = os.path.join(OUTPUT_FOLDER, datetime)
        print "Start REC " + output_path
        video = cv2.VideoWriter(output_path,
                                fourcc=FOURCC, fps=FPS,
                                frameSize=(frame_shape[1], frame_shape[0])) # interchanged sizes because of
                                                                            # width x height(instead of ncols x nrows)

        # Wait for external order to stop video writing
        while write_video_flag.value:
            if finished.value:
                video.release()
                return
            video.write(image)
            time.sleep(delay)

        print "Stop REC"
        video.release()
