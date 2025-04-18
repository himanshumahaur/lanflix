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

IP = '127.0.0.1'
IPS = []

PORT = 5000

# for mask in range(0, 255):
#     IPS.append(f'0.0.0.{mask}')

DATA_PATH = 'data'

FRAMES = queue.Queue()
PEERS = set()
PEERS.add(IP)
TABLE = {}

#used in REQ handeler, and start-stream
frames_event = threading.Event()
stream_event = threading.Event()

def fetch_frames(folder):
    for file, ip in  TABLE[folder]:
        if not stream_event.is_set():
            return

        send_request(ip, f'{folder}:{file}')

        #mutex if free for next request
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

            if cv2.waitKey(41) & 0xFF == ord('q'):
                

                while not FRAMES.empty():
                    FRAMES.get()

                stream_event.clear()
                return
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

            data = conn.recv(1024)

            PEERS.add(data.decode())

            print(PEERS)

        #UNKNOWN
        else:
            print("OTH")

        conn.close()

def share_entry(entry):
    for ip in PEERS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, PORT))

            #flag
            s.sendall(b'\x03')
            
            buffer = json.dumps(entry).encode()
            s.sendall(buffer)

            s.close()

def split_share(file):
    new_entry = {file: list()}

    os.mkdir(f'{DATA_PATH}/.tmp/{file}')
    ffmpeg.input(file).output(f'{DATA_PATH}/.tmp/{file}/%03d.mp4', c='copy', f='segment', segment_time=5).run()

    chunks = [_ for _ in os.listdir(f'{DATA_PATH}/.tmp/{file}')]
    chunks.sort()

    for c in chunks:
        #randomly selection
        ip = random.choice(list(PEERS))
        new_entry[file].append([c, ip])

        chunk = f'{DATA_PATH}/.tmp/{file}/{c}'
        buffer = open(chunk, 'rb').read()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(ip, PORT)
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
                s.settimeout(0.5)
                s.connect((ip, PORT))

                s.sendall(b'\x04')
                s.sendall(IP.encode())

                PEERS.add(ip)

        except Exception as e:
            continue

    print(PEERS)

os.system('rm -r ./data && mkdir -p ./data/.tmp && touch ./data/.tmp/.gitkeep')

join_network()
threading.Thread(target=start_inbound_handler).start()

'''
- IP can be retrived using `socket ... fun()`
- While to play stream
'''

def render_logo():
    print(r"    ____   ____ ____   ______ __  ____ ______ _____  __  __")
    print(r"   / __ \ /  _// __ \ / ____//  |/   // ____// ___/ / / / /")
    print(r"  / /_/ / / / / /_/ // __/  / /|_// // __/   \__ \ / /_/ /")
    print(r" / ____/ / / / ____// /___ / /   / // /___ ____/ // __  /")
    print(r"/_/    /___//_/   //_____//_/   /_//_____//_____//_/ /_/")

    print("\n\tAbhishek Raj\t\t2024PIS5012")
    print("\tHimanshu Mahaur\t\t2024PIS5020")

# split_share("wingit.mp4")

while(True):
    os.system("clear")

    render_logo()

    print("\nCHOOSE AN OPTION")

    print("\t1. Connected Peers")
    print("\t2. Show Table")
    print("\t3. Upload File")
    print("\t4. Stream File")

    opt = int(input("-> "))

    if opt == 1:
        print(list(PEERS))
        input("Press Enter to continue...")

    elif opt == 2:
        print(TABLE.keys())
        input("Press Enter to continue...")

    elif opt == 3:
        file = input("File: ")
        split_share(file)
        input("Press Enter to continue...")

    elif opt == 4:
        file = input("File: ")
        start_stream(file)

    else:
        input("Invalid Input...")