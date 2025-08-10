import socket
import threading

# Server configuration
HOST = '0.0.0.0'
PORT = 5555

# Dictionary to manage rooms and connected clients
rooms = {}

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    try:
        room_id = conn.recv(1024).decode()
        print(f"[ROOM JOIN] {addr} wants to join room '{room_id}'")

        if room_id not in rooms:
            rooms[room_id] = [conn]
            conn.send("WAIT".encode())  # First player waits
        else:
            rooms[room_id].append(conn)
            if len(rooms[room_id]) == 2:
                # Notify both clients that the game is starting
                rooms[room_id][0].send("START_WHITE".encode())
                rooms[room_id][1].send("START_BLACK".encode())

                # Start forwarding data between clients
                threading.Thread(target=relay_messages, args=(rooms[room_id][0], rooms[room_id][1])).start()
                threading.Thread(target=relay_messages, args=(rooms[room_id][1], rooms[room_id][0])).start()
    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
        conn.close()

def relay_messages(from_conn, to_conn):
    while True:
        try:
            data = from_conn.recv(1024)
            if not data:
                break
            to_conn.send(data)
        except:
            break
    from_conn.close()
    to_conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[STARTED] Server running on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()