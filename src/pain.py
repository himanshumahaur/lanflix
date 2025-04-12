import socket
import cv2
import numpy as np
import struct
import queue
import threading

# def table_update():
#     for folder in os.listdir(DATA_PATH):
#         tmp = dict() 
#         for files in os.listdir(DATA_PATH + folder):
#             tmp[files] = True
#         table[folder] = tmp


PORT = 5001
NPORT = 5000

DATA_PATH = 'data'
FRAMES = queue.Queue()


table = {
    'input': [
        ['000.mp4', '127.0.0.1'],
        ['001.mp4', '127.0.0.1'],
        ['002.mp4', '127.0.0.1']
    ]
}

#used in REQ handeler, and start-stream
frame_received_event = threading.Event()

def start_stream(folder):
    for file, ip in  table[folder]:
        send_request(ip, f'{folder}:{file}')
        frame_received_event.wait()
        frame_received_event.clear()

    while not FRAMES.empty():
        frame = FRAMES.get()
        cv2.imshow("Received Frame", frame)
        cv2.waitKey(41)

def send_request(ip='127.0.0.1', packet='input:006.mp4'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, NPORT))
        
        #FLAG
        s.sendall(b'\x00')
        s.sendall(packet.encode())

def send_response(ip, packet):
    folder, file = packet.decode().strip().split(":")

    cap = cv2.VideoCapture(f'{DATA_PATH}/{folder}/{file}')    

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, NPORT))
        
        #FLAG
        s.sendall(b'\x01')

        while True:
            flag, frame = cap.read()
            if not flag:
                break

            _, img = cv2.imencode('.jpg', frame)
            encoded = img.tobytes()

            be_frame_length = struct.pack('>I', len(encoded))
            s.sendall(be_frame_length)
            
            s.sendall(encoded)

def start_inbound_handler():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('0.0.0.0', PORT))
    s.listen()

    while True:
        print('Listening...')
        conn, addr = s.accept()
        
        header = conn.recv(1)

        #REQUEST
        if header == b'\x00':
            print('REQ')

            packet = conn.recv(1024)
            threading.Thread(target=send_response, args=(addr[0], packet)).start()

        #RESPONSE
        elif header == b'\x01':
            print('RES')

            while be_frame_length := conn.recv(4):
                frame_length = struct.unpack('>I', be_frame_length)[0]

                frame_encoded = bytearray()

                while chunk := conn.recv(frame_length - len(frame_encoded)):
                    frame_encoded += chunk

                img_array = np.frombuffer(frame_encoded, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                FRAMES.put(frame)

                # cv2.imshow('Received Frame', frame)
                # cv2.waitKey(41)

            frame_received_event.set()

            # while not FRAMES.empty():
            #     frame = FRAMES.get()
            #     cv2.imshow("Received Frame", frame)
            #     cv2.waitKey(41)
            
            # print("FRAMES is EMPTY!")

        #UNKNOWN
        else:
            print("OTH")

        conn.close()

threading.Thread(target=start_inbound_handler).start()
