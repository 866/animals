import socket

import cv2
import Image
import StringIO
import time
import ctypes
import struct
import fcntl
import sys
import numpy as np
from video_capture import VideoCapture
from multiprocessing import Array, Value, Process
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn


def get_ip_address(ifname):
    """
    Finds ip address for an interface
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

server = None


def getCamHandler(shared_frame, shared_boolean, shared_float):
    """
    Makes a closure for CamHandler class
    :param shared_frame: frame that is shared between processes
    :param shared_boolean: shared "finished" flag
    :param shared_float: shared fps falue
    :return: CamHandler class
    """

    global server

    class CamHandler(BaseHTTPRequestHandler):
        """
        Request Handler class for ThreadedHTTP server
        """
        def do_GET(self):
            """
            Handles all get requests
            :return: nothing
            """
            if self.path.endswith('/cam.mjpg'):
                # Image stream
                self.send_response(200)
                self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
                self.end_headers()

                # Continue while stream is not finished
                while not shared_boolean.value:
                    try:
                        # Get the image
                        imgRGB = cv2.cvtColor(shared_frame, cv2.COLOR_BGR2RGB)
                        jpg = Image.fromarray(imgRGB)
                        # Temporary file for JPEG
                        tmpFile = StringIO.StringIO()
                        jpg.save(tmpFile, 'JPEG')
                        # Write the output
                        self.wfile.write("--jpgboundary")
                        self.send_header('Content-type', 'image/jpeg')
                        self.send_header('Content-length', str(tmpFile.len))
                        self.end_headers()
                        # Write jpeg image into the stream
                        jpg.save(self.wfile, 'JPEG')
                        # Delay before getting new frame
                        time.sleep(0.1)
                    except Exception as e:
                        print("Exception", e)
                        break
                return
            if self.path.endswith('/main.html'):
                # Return main page
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><head></head><body>')
                self.wfile.write('<img src="http://127.0.0.1:8080/cam.mjpg"/>')
                self.wfile.write('</body></html>')
                return
            if self.path.endswith('/exit'):
                # Let's exit
                self.send_response(200)
                shared_boolean.value = 1
                server.shutdown()
                return
            if self.path.endswith('/fps'):
                # Return fps value
                self.send_response(200)
                self.wfile.write("{:.2f}".format(shared_float.value))
                return

    return CamHandler


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def main():

    # Get ip address of the given interface
    ip_address = None    
    try:
        ip_address = get_ip_address(sys.argv[1])
    except Exception as e:
        print(e)
        exit(-1)
    print ip_address

    # Define Video Capture object and auxilary objects
    cap = VideoCapture()
    shape = cap.get_size()
    stream = cap.get_stream_function()

    # Define shared values
    shared_array_base = Array(ctypes.c_uint8, shape[0] * shape[1] * shape[2])
    frame = np.ctypeslib.as_array(shared_array_base.get_obj())
    frame = frame.reshape(shape[0], shape[1], shape[2])
    finished = Value('i', 0)
    shared_float = Value('f', 0)
    video_process = Process(target=stream, args=(frame, finished, shared_float))
    video_process.start()

    global server
    try:
        # Start the server on the ip address
        CamHandler = getCamHandler(frame, finished, shared_float)
        print("Starting the server on {}".format(ip_address))
        server = ThreadedHTTPServer((ip_address, 8080), CamHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        # Release everything
        cap.release()
        finished.value = 1
        video_process.terminate()
        server.socket.close()
    except Exception as e:
        # Something wrong happened
        print("Exception", e)        
        finished.value = 1
        cap.release()
        video_process.terminate()
        exit(-1)

if __name__ == '__main__':
    main()
