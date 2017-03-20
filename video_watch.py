import numpy as np
import cv2
import time
import os

# Constants
ALPHA = 0.005
DELAY = 0.
FPS = 8
FRAMES_TO_SKIP = 0  # 30
DIFF_THRESHOLD = 3
MINTIME_STOP = 40  # in seconds
FRAMES_AVERAGE = 10 * (FRAMES_TO_SKIP + 1)
FOURCC = cv2.cv.CV_FOURCC(*'XVID')
OUTPUT_FOLDER = "./output"

cap = cv2.VideoCapture(0) #"/home/victor/Videos/2016-12-04-101522.webm")


def skip(nframes=FRAMES_TO_SKIP, delay=DELAY):
    """
    Skips n frames
    :param nframes: number of frames to skip
    :return:
    """
    for i in range(nframes):  # skip first FRAMES_TO_SKIP
        cap.read()
        time.sleep(delay)


def proper_frame(delay=DELAY):
    """
    :return: frame
    """
    snapshot = None
    correct_img = False
    while not correct_img:
        correct_img, snapshot = cap.read()
        time.sleep(delay)
    return snapshot


def diff_sum(diff, points):
    return np.sum(np.sum(diff)) / points


# Processes image
def filter_image(img):
    blur = cv2.GaussianBlur(img, (25, 25), 0)
    return blur


# Check if correct path is specified
if not os.path.isdir(OUTPUT_FOLDER):
    try:
        os.mkdir(OUTPUT_FOLDER)
    except OSError:
        print("Incorrect output path is specified")
        exit(-1)

# Skip first frames
skip(20, 1/7.)
#skip(6000, 0)
# Shape of the image
frame_shape = (int(cap.get(int(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))),
               int(cap.get(int(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))))

imgs = np.ndarray((FRAMES_AVERAGE, frame_shape[0], frame_shape[1]), dtype=np.float32)

# Number of pixels in the image
ptx = float(frame_shape[0] * frame_shape[1])

# Find frames for averaging
for i in range(FRAMES_AVERAGE):
    gray_frame = cv2.cvtColor(proper_frame(), cv2.COLOR_BGR2GRAY)
    imgs[i] = gray_frame

# Average
background = np.mean(imgs, axis=0)
background = filter_image(background).astype(dtype=np.float16)
del imgs

# Predefine some variables
video_out = None
last_movement = None
last_nframes = None
frames_counter = 0

# Capture the video until 'q' is pressed
while True:
    # Capture every nth frame
    skip()
    color_frame = proper_frame()
    frames_counter += 1

    # Measure FPS
    if last_nframes is None:
        last_nframes = time.time()

    if frames_counter % 100 == 0:
        elapse = time.time() - last_nframes
        print("FPS: {:.2f}".format(frames_counter / float(elapse)))
        last_nframes = time.time()
        frames_counter = 0

    # Process image
    gray_frame = cv2.cvtColor(color_frame, cv2.COLOR_BGR2GRAY)
    processed_frame = filter_image(gray_frame)

    # Calculate fps
    # Find the difference
    diff_frame = np.abs(processed_frame - background).astype(dtype=np.uint8)
    diff_scalar = diff_sum(diff_frame, ptx)
    # print diff_scalar, diff_scalar > DIFF_THRESHOLD, diff_frame
    # print np.abs(processed_frame - background)
    # cv2.imshow("fff", diff_frame)
    # cv2.waitKey(0)
    # break

    # Mix background and a bit of a new object
    background = ALPHA * processed_frame + (1 - ALPHA) * background

    # Display output
    # recording = video_out is not None
    # diff_color = cv2.cvtColor(diff_frame.astype(dtype=np.uint8), cv2.COLOR_GRAY2BGR)
    # cv2.putText(diff_color, "Diff: {0:.2f}".format(float(diff_scalar)), (20, 20),
    #             cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.5, (255, 255, 255))
    # if recording:
    #     cv2.putText(diff_color, " * REC", (20, 40),
    #                 cv2.FONT_HERSHEY_TRIPLEX, 0.5, (0, 0, 255))
    # show_image = np.hstack((color_frame, diff_color))
    # cv2.imshow("ShowTime", show_image)

    # Write the video if we have movement
    if video_out is not None:
        video_out.write(color_frame)

    # Check if we exceeded moving threshold
    if diff_scalar > DIFF_THRESHOLD:
        if video_out is None:
            # Fix last timestamp
            last_movement = time.time()

            # Start writing the video
            datetime = time.strftime("%m|%d_%H:%M:%S.avi")
            output_path = os.path.join(OUTPUT_FOLDER, datetime)
            print "Start REC " + output_path
            video_out = cv2.VideoWriter(output_path,
                                        fourcc=FOURCC, fps=FPS,
                                        frameSize=frame_shape[::-1])  # interchanged sizes because of
                                                                      # width x height(instead of ncols x nrows)
        video_out.write(color_frame)
    else:
        if video_out is not None and time.time() - last_movement > MINTIME_STOP:
            # Stop writing the video if we already opened video writing
            video_out.release()
            print "Stop REC\n"
            video_out = None

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
