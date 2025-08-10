import pygame
import sys
import socket
import threading

pygame.init()
# Constants
WIDTH, HEIGHT = 800, 800
SQUARE_SIZE = WIDTH // 8

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)

# Network
client_socket = None
player_color = None
your_turn = False

# Pygame setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiplayer Chess")

class ChessPiece:
    def __init__(self, color, type, image):
        self.color = color
        self.type = type
        self.image = pygame.image.load(image)
        self.image = pygame.transform.scale(self.image, (SQUARE_SIZE, SQUARE_SIZE))
        self.has_moved = False

board = [[None for _ in range(8)] for _ in range(8)]
current_player = 'white'

selected_piece = None
selected_pos = None

checked_king_pos = None
promotion_pending = False
promotion_position = None
promotion_color = None

def connect_to_server():
    global client_socket, player_color, your_turn
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('localhost', 5555))  # Change to server IP if needed
    room_id = input("Enter room ID to join: ")
    client_socket.send(room_id.encode())

    status = client_socket.recv(1024).decode()
    if status == "WAIT":
        print("Waiting for opponent...")
        status = client_socket.recv(1024).decode()

    if status == "START_WHITE":
        print("Game started! You are White.")
        player_color = 'white'
        your_turn = True
    elif status == "START_BLACK":
        print("Game started! You are Black.")
        player_color = 'black'
        your_turn = False

def listen_for_opponent():
    global your_turn, current_player
    while True:
        try:
            data = client_socket.recv(1024).decode()
            if data:
                parts = list(map(int, data.split(',')))
                from_r, from_c, to_r, to_c = parts
                piece = board[from_r][from_c]
                board[to_r][to_c] = piece
                board[from_r][from_c] = None
                piece.has_moved = True
                current_player = player_color
                your_turn = True
        except:
            break

def init_board():
    for col in range(8):
        board[1][col] = ChessPiece('black', 'pawn', 'images/black_pawn.png')
        board[6][col] = ChessPiece('white', 'pawn', 'images/white_pawn.png')
    board[0][0] = board[0][7] = ChessPiece('black', 'rook', 'images/black_rook.png')
    board[7][0] = board[7][7] = ChessPiece('white', 'rook', 'images/white_rook.png')
    board[0][1] = board[0][6] = ChessPiece('black', 'knight', 'images/black_knight.png')
    board[7][1] = board[7][6] = ChessPiece('white', 'knight', 'images/white_knight.png')
    board[0][2] = board[0][5] = ChessPiece('black', 'bishop', 'images/black_bishop.png')
    board[7][2] = board[7][5] = ChessPiece('white', 'bishop', 'images/white_bishop.png')
    board[0][3] = ChessPiece('black', 'queen', 'images/black_queen.png')
    board[7][3] = ChessPiece('white', 'queen', 'images/white_queen.png')
    board[0][4] = ChessPiece('black', 'king', 'images/black_king.png')
    board[7][4] = ChessPiece('white', 'king', 'images/white_king.png')

def draw_board():
    for row in range(8):
        for col in range(8):
            color = WHITE if (row + col) % 2 == 0 else BROWN
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    if checked_king_pos:
        pygame.draw.rect(screen, (255, 0, 0), (
            checked_king_pos[1] * SQUARE_SIZE,
            checked_king_pos[0] * SQUARE_SIZE,
            SQUARE_SIZE, SQUARE_SIZE
        ))
    if selected_pos:
        pygame.draw.rect(screen, YELLOW, (
            selected_pos[1] * SQUARE_SIZE,
            selected_pos[0] * SQUARE_SIZE,
            SQUARE_SIZE, SQUARE_SIZE
        ))
    if selected_piece:
        moves = get_legal_moves(selected_piece, selected_pos[0], selected_pos[1])
        for move in moves:
            center = (move[1] * SQUARE_SIZE + SQUARE_SIZE // 2, move[0] * SQUARE_SIZE + SQUARE_SIZE // 2)
            pygame.draw.circle(screen, (0, 255, 0), center, 10)

def draw_piece():
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece:
                screen.blit(piece.image, (col * SQUARE_SIZE, row * SQUARE_SIZE))

def get_valid_moves(piece, row, col):
    moves = []
    direction = -1 if piece.color == 'white' else 1
    if piece.type == 'pawn':
        if 0 <= row + direction < 8 and board[row + direction][col] is None:
            moves.append((row + direction, col))
            if (piece.color == 'white' and row == 6) or (piece.color == 'black' and row == 1):
                if board[row + 2 * direction][col] is None:
                    moves.append((row + 2 * direction, col))
        for dc in [-1, 1]:
            if 0 <= row + direction < 8 and 0 <= col + dc < 8:
                if board[row + direction][col + dc] and board[row + direction][col + dc].color != piece.color:
                    moves.append((row + direction, col + dc))
    elif piece.type in ['rook', 'bishop', 'queen']:
        directions = []
        if piece.type in ['rook', 'queen']:
            directions += [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if piece.type in ['bishop', 'queen']:
            directions += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dr, dc in directions:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                if board[r][c] is None:
                    moves.append((r, c))
                elif board[r][c].color != piece.color:
                    moves.append((r, c))
                    break
                else:
                    break
                r += dr
                c += dc
    elif piece.type == 'knight':
        for dr, dc in [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8 and (board[r][c] is None or board[r][c].color != piece.color):
                moves.append((r, c))
    elif piece.type == 'king':
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < 8 and 0 <= c < 8 and (board[r][c] is None or board[r][c].color != piece.color):
                    moves.append((r, c))
    return moves

def get_legal_moves(piece, row, col):
    legal_moves = []
    possible_moves = get_valid_moves(piece, row, col)
    for move in possible_moves:
        r2, c2 = move
        captured = board[r2][c2]
        board[r2][c2] = piece
        board[row][col] = None
        if not is_check(piece.color):
            legal_moves.append(move)
        board[row][col] = piece
        board[r2][c2] = captured
    return legal_moves

def is_check(color):
    global checked_king_pos
    king_pos = None
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece.color == color and piece.type == 'king':
                king_pos = (r, c)
                break
        if king_pos:
            break
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece.color != color:
                if king_pos in get_valid_moves(piece, r, c):
                    checked_king_pos = king_pos
                    return True
    checked_king_pos = None
    return False

def is_game_over():
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece.color == current_player:
                if get_legal_moves(piece, r, c):
                    return False
    return True

def draw_promotion_options(color):
    options = ['queen', 'rook', 'bishop', 'knight']
    for i, piece_type in enumerate(options):
        img = pygame.image.load(f'images/{color}_{piece_type}.png')
        img = pygame.transform.scale(img, (SQUARE_SIZE, SQUARE_SIZE))
        screen.blit(img, (i * SQUARE_SIZE + 2 * SQUARE_SIZE, 3.5 * SQUARE_SIZE))

def handle_click(pos):
    global selected_piece, selected_pos, current_player
    global promotion_pending, promotion_position, promotion_color, your_turn

    if not your_turn or promotion_pending:
        return

    col = pos[0] // SQUARE_SIZE
    row = pos[1] // SQUARE_SIZE

    # Promotion selection
    if promotion_pending:
        option_index = (pos[0] - 2 * SQUARE_SIZE) // SQUARE_SIZE
        if 0 <= option_index < 4 and 3.5 * SQUARE_SIZE <= pos[1] <= 4.5 * SQUARE_SIZE:
            piece_types = ['queen', 'rook', 'bishop', 'knight']
            selected_type = piece_types[option_index]
            r, c = promotion_position
            board[r][c] = ChessPiece(promotion_color, selected_type, f'images/{promotion_color}_{selected_type}.png')
            promotion_pending = False
            promotion_position = None
            promotion_color = None
            current_player = 'black' if current_player == 'white' else 'white'
            your_turn = False
        return

    if selected_piece is None:
        piece = board[row][col]
        if piece and piece.color == current_player:
            selected_piece = piece
            selected_pos = (row, col)
    else:
        if (row, col) in get_legal_moves(selected_piece, selected_pos[0], selected_pos[1]):
            board[row][col] = selected_piece
            board[selected_pos[0]][selected_pos[1]] = None
            selected_piece.has_moved = True

            move_data = f"{selected_pos[0]},{selected_pos[1]},{row},{col}"
            client_socket.send(move_data.encode())

            if selected_piece.type == 'pawn' and (row == 0 or row == 7):
                promotion_pending = True
                promotion_position = (row, col)
                promotion_color = selected_piece.color
                selected_piece = None
                selected_pos = None
                return

            current_player = 'black' if current_player == 'white' else 'white'
            your_turn = False
        selected_piece = None
        selected_pos = None

def main():
    init_board()
    connect_to_server()
    threading.Thread(target=listen_for_opponent, daemon=True).start()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                handle_click(pygame.mouse.get_pos())

        is_check(current_player)
        draw_board()
        draw_piece()
        if promotion_pending:
            draw_promotion_options(promotion_color)
        pygame.display.flip()

if __name__ == "__main__":
    main()