import copy
import os
import sys
import time
from collections import deque
from typing import Tuple, List, Dict, Optional, Deque, Union

import pygame

START = "S"
END = "E"
FREE = "."
WALL = "#"

Point = Tuple[int, int]
Maze = List[List[str]]

# https://www.pygame.org/docs/ref/color.html#pygame.Color
GuiColor = Union[Tuple[int, int, int], Tuple[int, int, int, int]]
GuiPoint = Tuple[Union[int, float], Union[int, float]]


def gui_init_window(size: int = 1024) -> pygame.Surface:
    """
    Initialize PyGame library

    :param size: Desired window size (width and height).

    :return: Main drawing canvas.
    """
    # https://realpython.com/pygame-a-primer/

    # Initialize the pygame library
    pygame.init()

    # https://www.pygame.org/docs/ref/display.html
    # Create a window/canvas for the maze to be drawn on
    canvas: pygame.Surface = pygame.display.set_mode((size, size),
                                                     flags=(pygame.HWSURFACE + pygame.HWACCEL + pygame.SRCALPHA))
    # Add SRCALPHA flag to support pixels with RGBA colors (Alpha = transparency).

    pygame.display.set_caption("Python Pathfinding")

    return canvas


def gui_handle_events(wait_left_click: bool = False) -> bool:
    """
    Handle GUI events

    :return: True if all events were processed and the program shall continue parsing GUI events,
             False if window was closed and program should exit.
    """
    run = True
    # Events are usually processed only once per call of this function, except if some specific events are awaited
    loop = 0 + wait_left_click  # bool True is 1

    while True:
        # https://www.pygame.org/docs/ref/event.html#pygame.event.get
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Window close button was pressed
                run = False
                loop = False
                pygame.quit()
                break

            if event.type == pygame.constants.MOUSEBUTTONDOWN:
                # If the Left mouse button was pressed
                if wait_left_click and pygame.mouse.get_pressed()[0]:
                    loop -= 1  # One of the awaited event was just handled
                    wait_left_click = False  # Not waiting for this event anymore

        if loop <= 0:
            # No specific event is being awaited (anymore)
            break

    return run


maze_already_drawn = False


def gui_update(canvas: pygame.Surface, maze: Maze,
               path: Tuple[int, int, str] = None,
               final_path: Optional[Tuple[List[Point], List[str]]] = None) -> bool:
    """
    Draw the maze

    :param canvas:      Canvas to use for drawing.
    :param maze:        Maze data to draw.
    :param path:        Path with moves to draw (e.g. while path searching), containing a tuple (x, y, move).
    :param final_path:  Final path with moves to draw (different color than `path`).
    :param path:        Maze data to draw.

    :return: Return value of :func:`gui_handle_events`.
    """
    global maze_already_drawn

    # https://www.pygame.org/docs/ref/surface.html
    # https://www.pygame.org/docs/ref/draw.html
    background_color = (255, 255, 255, 255)  # Last value is alpha (0 is fully transparent, 255 is fully opaque)
    path_color = (50, 50, 200, 200)
    final_path_color = (200, 0, 0, 240)

    # Get the current size of canvas and maze, used to calculate the size of the maze cells
    gui_w, gui_h = canvas.get_size()
    maze_rows = len(maze)
    maze_cols = len(maze[0])
    cell_h = gui_h // maze_rows  # Height of the row is total canvas height divided by number of rows in the maze
    cell_w = gui_w // maze_cols  # Width of the cell is total canvas width divided by number of cells in a row

    border_tb = (gui_h - maze_rows * cell_h) / 2  # Divided by 2 to add the same border on top and bottom
    border_lr = (gui_w - maze_cols * cell_w) / 2  # Divided by 2 to add the same border on left and right

    if not maze_already_drawn:
        canvas.fill(background_color)

        color_map: Dict[str, GuiColor] = {
            START: (128, 0, 0),
            END: (0, 255, 0),
            WALL: (20, 20, 20),
            FREE: (200, 200, 200),
        }

        # Draw maze cells
        for y, row in enumerate(maze):
            for x, cell in enumerate(row):
                pygame.draw.rect(canvas, color_map[cell], (border_lr + x * cell_w,
                                                           border_tb + y * cell_w, cell_w, cell_h))

        maze_already_drawn = True

    def get_shape(x_: int, y_: int, move_: str, size: float) -> Tuple[GuiPoint, ...]:
        # Calculate 3 points of the triangle inside the square cell
        pts = {
            "Right": (
                ((x_ + size) * cell_w, (y_ + 0.5) * cell_h),
                ((x_ + 1 - size) * cell_w, (y_ + 1 - size) * cell_h),
                ((x_ + 1 - size) * cell_w, (y_ + size) * cell_h)
            ),
            "Down": (
                ((x_ + 0.5) * cell_w, (y_ + size) * cell_h),
                ((x_ + size) * cell_w, (y_ + 1 - size) * cell_h),
                ((x_ + 1 - size) * cell_w, (y_ + 1 - size) * cell_h)
            ),
            "Left": (
                ((x_ + 1 - size) * cell_w, (y_ + 0.5) * cell_h),
                ((x_ + size) * cell_w, (y_ + size) * cell_h),
                ((x_ + size) * cell_w, (y_ + 1 - size) * cell_h)
            ),
            "Up": (
                ((x_ + 0.5) * cell_w, (y_ + 1 - size) * cell_h),
                ((x_ + 1 - size) * cell_w, (y_ + size) * cell_h),
                ((x_ + size) * cell_w, (y_ + size) * cell_h)
            ),
        }.get(move_, (
            # Otherwise, get a square
            ((x_ + 1 - size) * cell_w, (y_ + 1 - size) * cell_h),
            ((x_ + 1 - size) * cell_w, (y_ + size) * cell_h),
            ((x_ + size) * cell_w, (y_ + size) * cell_h),
            ((x_ + size) * cell_w, (y_ + 1 - size) * cell_h)
        ))
        # Add border offsets
        # noinspection PyTypeChecker
        return tuple((pt[0] + border_lr, pt[1] + border_tb) for pt in pts)

    # Draw path, which is optional (list of points, list of moves)
    if path:
        x, y, move = path
        pygame.draw.polygon(canvas, path_color, get_shape(x, y, move, 0.9))

    # Draw final path, which is optional (list of points, list of moves)
    if final_path:
        for point, move in zip(*final_path):  # type: Point, str
            pygame.draw.polygon(canvas, final_path_color, get_shape(point[0], point[1], move, 0.8))

    # Update the display/canvas
    pygame.display.update()

    # Also handle GUI events after drawing to keep the window responsive
    return gui_handle_events()


# Print the path using colors
def print_path(maze: Maze, path=None, color: bool = True) -> None:
    """
    :param maze:  Maze data.
    :param path:  List of points which algorithm reached when executing moves (including the destination cell).
    :param color: Should the path be printed in color text?
    """

    # Copies the maze so that you don't change it
    maze = copy.deepcopy(maze)

    # If the path is provided, print the path inside the provided maze
    if path:
        # If color is True, print the path using colors, else use '@'
        if color:
            for x, y in path:  # If printing without colors add `[:-1]` after `path`
                maze[y][x] = "\033[0;102m" + maze[y][x] + "\033[0m"  # instead of colors, you could use "@"

        else:
            # Print the shortest path inside the maze without using colors
            for x, y in path[:-1]:  # The last character is the end, so don't replace it
                maze[y][x] = "@"

    for line in maze:
        print("".join(line))


# Find the shortest possible route in a matrix `mat` from source `src` to
# destination `dest`
def find_shortest_path(mat: Maze, start_point: Point, end_point: Point,
                       print_progress: bool = False, canvas: Optional[pygame.Surface] = None) \
        -> Tuple[Optional[List[Point]], Optional[List[str]]]:
    """
    https://www.techiedelight.com/lee-algorithm-shortest-path-in-a-maze

    :param mat:            Maze data.
    :param start_point:    Source/start point.
    :param end_point:      Destination/end point.
    :param print_progress: Should the printing process be printed?
    :param canvas:         Graphic canvas to which to draw the maze to it instead to a stdout.

    :return: List of points which the algorithm reached when executing moves (including the destination cell);
             List of moves needed to reach each cell.
    """
    sx, sy = start_point
    ex, ey = end_point

    # base case: invalid input
    if not mat or len(mat) == 0 or mat[sy][sx] == 0 or mat[ey][ex] == 0:
        return None, None

    # construct a matrix to keep track of visited cells
    visited = [[False for _ in row] for row in mat]

    # Function to check if it is possible to go to position (r, c)
    # from the current position. The function returns false if r, c
    # is not a valid position or has a value 0 or already visited.
    def is_valid(px: int, py: int) -> bool:
        """
        :param px: Point X.
        :param py: Point Y.
        :return: Is the cell ok to move to?
        """
        return ((py >= 0) and (py < len(mat)) and (px >= 0) and (px < len(mat[py]))
                and mat[py][px] != WALL and not visited[py][px])

    # Below lists detail all four possible x,y movements from a cell, so we can just iterate
    # over these combinations instead of repeating "the same" check 4 times for every direction.
    # Diagonal movements could also be added here, in that case there would be 8 possible possible_moves.
    possible_moves: Dict[str, Point] = {
        "Right": (1, 0),  # x + 1
        "Down": (0, 1),  # y + 1
        "Left": (-1, 0),  # x - 1
        "Up": (0, -1),  # y - 1
    }

    # create an empty queue
    q: Deque[Tuple[int, int, int, Optional[str], Optional[tuple]]] = deque()

    # mark the source cell as visited and enqueue the source node
    visited[sy][sx] = True

    # (sx, sy, dist, move, prev_cell) represents matrix cell coordinates, their minimum distance from the source,
    # the move used to reach this cell, and the previous cell from which you came
    cell = (sx, sy, 0, None, None)
    q.append(cell)

    # stores length of the longest path from source to destination
    min_dist = sys.maxsize

    # Used only when `print_progress` is true
    last_printed_distance = None
    all_paths = set()

    # loop till queue is empty
    while q:

        # dequeue front node and process it
        cell = q.popleft()
        (x, y, dist, move, _) = cell
        # (x, y) represents a current cell, and `dist` stores its
        # minimum distance from the source

        if print_progress:
            if canvas:
                gui_update(canvas, mat, path=(x, y, move))
            else:
                all_paths.add((x, y))
                if last_printed_distance != dist:
                    # Clear the output
                    os.system("cls" if os.name == 'nt' else "clear")
                    print_path(mat, all_paths, color=True)
                    last_printed_distance = dist

        # if the destination is found, update `min_dist` and stop
        if x == ex and y == ey:
            min_dist = dist
            break

        # check for all four possible movements from the current cell
        # and enqueue each valid movement
        for move, (dx, dy) in possible_moves.items():
            # check if it is possible to go to position
            if is_valid(x + dx, y + dy):
                # mark next cell as visited and enqueue it
                visited[y + dy][x + dx] = True
                q.append((x + dx, y + dy, dist + 1, move, cell))

    # If the path was not found, report an error
    if min_dist == sys.maxsize:
        return None, None

    path: List[Point] = []
    moves: List[str] = []
    while True:
        (x, y, _, move, prev_cell) = cell
        # If the previous cell in None, then the current cell is the start cell
        if not prev_cell:
            return path, moves

        # Add the move to that cell at the beginning of the list
        moves.insert(0, move)
        # Add the cell at the beginning of the list
        path.insert(0, (x, y))
        cell = prev_cell


def main() -> int:
    # List all files that don't have any extension
    files = [f for f in os.listdir() if os.path.isfile(f) and not os.path.splitext(f)[1]]
    print("Enter file number to read maze data")
    for i, f in enumerate(files):
        print(f"{i} - {f}")
    file_index = input("Enter file number: ").strip()
    file_name = files[int(file_index)]
    print(f"Reading maze data from file '{os.path.realpath(file_name)}'")

    # Open the file and copy contents into `content`
    with open(file_name, encoding="utf-8") as file:
        content = file.read().strip()  # Remove spaces and newlines from both ends of file

    # Maze content is separated by spaces
    maze: Maze = [[c for c in row] for row in content.split(" ")]

    canvas = gui_init_window()

    print(f"Dimensions of the entered maze are: {len(maze)}*{len(maze[0])}")
    print_path(maze)

    start_point = None
    end_point = None
    # Print entire maze and find the start and end point
    for y, line in enumerate(maze):
        for x, cell in enumerate(line):
            if cell == START:
                start_point = (x, y)
            elif cell == END:
                end_point = (x, y)

    if not start_point:
        print("Start point could not be found")
        return -1
    if not end_point:
        print("End point could not be found")
        return -1
    print(f"Start point: {start_point}, End point {end_point}")

    # Ask user if they want the entire searching process printed (it takes a while)
    print_progress = True  # (input("Print searching process? [Y/n]: ").lower().strip() == "y")

    print('Open the "Python Pathfinding" window and left-click')
    gui_update(canvas, maze)

    # Process GUI events so that the GUI window can be brought to front and clicked
    gui_handle_events(wait_left_click=True)

    t0 = time.perf_counter()
    path, moves = find_shortest_path(maze, start_point, end_point, print_progress, canvas=canvas)
    dt = time.perf_counter() - t0

    if not path:
        print(f"Shortest path could not be found in {dt:.1f} s")
        return -1
    print(f"Shortest path length is: {len(path)} in {dt:.1f} s")

    print(f"{'N': <7}{'(x, y)': <11}Move executed to reach this point")
    for cell_num, (point, move) in enumerate(zip(path, moves), 1):
        print(f"{f'#{cell_num}:': <7}{str(tuple(point)): <11}{move}")

    # Print the final path. 3rd argument is color printing [True/False], default: True
    print_path(maze, path, color=True)
    gui_update(canvas, maze, final_path=(path, moves))

    while gui_handle_events():
        # Sleep a while to prevent busy-looping and consuming high CPU for no reason
        time.sleep(0.01)

    return 0


exit(main())
