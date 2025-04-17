import socket
import cv2
import numpy as np
import struct
import queue
import threading

import ffmpeg
import os
import time

import json
import random

IP = ''
IPS = []

PORT = 5000

# for mask in range(0, 255):
#     IPS.append(f'0.0.0.{mask}')

DATA_PATH = 'data'

FRAMES = queue.Queue()
PEERS = set()
TABLE = {}

#used in REQ handeler, and start-stream
frames_event = threading.Event()
stream_event = threading.Event()

def fetch_frames(folder):
    for file, ip in  TABLE[folder]:
        send_request(ip, f'{folder}:{file}')

        #mutex
        frames_event.wait()
        frames_event.clear()

        #buffer size, no. of frames cached
        while FRAMES.qsize() > 150:
            time.sleep(1)
    stream_event.clear()

def start_stream(folder):
    stream_event.set()
    threading.Thread(target=fetch_frames, args=(folder,)).start()

    while True:
        if not FRAMES.empty():
            frame = FRAMES.get()
            cv2.imshow("Received Frame", frame)
            cv2.waitKey(41)
        else:
            if stream_event.is_set():
                time.sleep(1)
            else:
                return

def send_request(ip, packet):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, PORT))
        
        #FLAG
        s.sendall(b'\x00')
        s.sendall(packet.encode())

def send_response(ip, packet):
    folder, file = packet.decode().strip().split(":")

    cap = cv2.VideoCapture(f'{DATA_PATH}/{folder}/{file}')    

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, PORT))
        
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
                print(FRAMES.qsize())

            frames_event.set()

        #UPLOAD
        elif header == b'\x02':
            print('UPL')

            be_header_length = conn.recv(4)
            header_length = struct.unpack('>I', be_header_length)[0]            
            header = conn.recv(header_length)

            folder, file = header.decode().strip().split(':')

            buffer = bytearray()
            while chunk := conn.recv(4096):
                buffer += chunk

            if not os.path.exists(f'{DATA_PATH}/{folder}'):  
                os.mkdir(f'{DATA_PATH}/{folder}')
    
            with open(f'{DATA_PATH}/{folder}/{file}', 'wb') as _:
                _.write(buffer)
                _.close()

            print(f'Saved {folder}/{file}!')

        #TABLE
        elif header == b'\x03':
            print('TBL')

            buffer = bytearray()
            while chunk := conn.recv(4096):
                buffer += chunk

            entry = json.loads(buffer.decode())
            TABLE.update(entry)
        
        elif header == b'\x04':
            print('DSC')
            
            PEERS.add((addr[0], 5000))

        #UNKNOWN
        else:
            print("OTH")

        conn.close()

def share_entry(entry):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        for peer in PEERS:
            s.connect((peer[0], PORT))

            #flag
            s.sendall(b'\x03')
            
            buffer = json.dumps(entry).encode()
            s.sendall(buffer)

def split_share(file):
    new_entry = {file: list()}

    os.mkdir(f'{DATA_PATH}/.tmp/{file}')
    ffmpeg.input(file).output(f'{DATA_PATH}/.tmp/{file}/%03d.mp4', c='copy', f='segment', segment_time=5).run()

    chunks = [_ for _ in os.listdir(f'{DATA_PATH}/.tmp/{file}')]
    chunks.sort()

    for c in chunks:
        #randomly selection
        ip = random.choice(list(PEERS))[0]
        new_entry[file].append([c, ip])

        chunk = f'{DATA_PATH}/.tmp/{file}/{c}'
        buffer = open(chunk, 'rb').read()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, PORT))

            #FLAG
            s.sendall(b'\x02')

            header = f"{file}:{c}"
            s.sendall(struct.pack('>I', len(header)))
            s.sendall(header.encode())

            s.sendall(buffer)

        os.remove(chunk)
    os.rmdir(f'{DATA_PATH}/.tmp/{file}')

    TABLE.update(new_entry)
    share_entry(new_entry)

def join_network():
    self_addr = f'{IP}:{PORT}'

    for ip in IPS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((ip, PORT))
                s.sendall(b'\x04')

                PEERS.add((ip, PORT))
                print(f"Discovered peer: {ip}:{PORT}")

        except Exception as e:
            print(ip, "Not Available")
            continue


# threading.Thread(target=start_inbound_handler).start()


# add your ip in peer table
    # use socket to get you'r ip first;
    # add it to table simply

# neighbour discovery
    # iterate over all available ips: (+ if netmask can be found)
        # send ip:port, recv ip:port
        # ready for sharing

# split_share('wingit.mp4')
# start_stream('wingit.mp4')
