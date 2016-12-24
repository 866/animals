import cv2
import time

MAX_TRIES = 10
MAX_FPS_ITER = 30

class VideoCapture:
    """
    Class that handles video capture from device or video file
    """
    def __init__(self, size=(800, 600), device=0, delay=0.):
        """
        :param device: device index or video filename
        :param delay: delay between frames capture(in seconds)
        """
        self._cap = cv2.VideoCapture(device)
        # self._cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, size[1])
        # self._cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, size[0])
        # print self.get_size()
        self._delay = delay

    def proper_frame(self, delay=None):
        """
        :param delay: delay between frames capture(in seconds)
        :return: frame
        """
        snapshot = None
        correct_img = False
        fail_counter = -1
        while not correct_img:
            # Capture the frame
            correct_img, snapshot = self._cap.read()
            fail_counter += 1
            # Raise exception if there's no output from the device
            if fail_counter > MAX_TRIES:
                raise Exception("Exceeded number of tries to capture the frame.")
            # Delay before we get a new frame
            time.sleep(delay)
        return snapshot

    def get_size(self):
        """
        :return: Size of captured image
        """
        return (int(self._cap.get(int(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))),
                int(self._cap.get(int(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))), 3)

    def get_stream_function(self):
        """
        Returns stream_function object function
        """
        def stream_function(image, finished, fps):
            """
            Function that runs in parallel
            :param image: shared numpy array for multiprocessing(see multiprocessing.Array)
            :param finished: Synchronized wrapper for int(see multiprocessing.Value)
            :return: last frame
            """
            # Incorrect input array
            if image.shape != self.get_size():
                raise Exception("Improper size of the input image")
            iterations = 0
            last_timestamp = time.time()
            # Capture frame until we get finished flag set to True
            while not finished.value:
                image[:, :, :] = self.proper_frame(self._delay)
                iterations += 1
                if iterations == MAX_FPS_ITER:
                    fps.value = MAX_FPS_ITER / (time.time() - last_timestamp)
                    iterations = 0
                    last_timestamp = time.time()
            return image
        return stream_function

    def release(self):
        self._cap.release()
