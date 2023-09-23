"""
https://www.boristhebrave.com/2019/07/14/dungeon-generation-in-diablo-1/
"""
from dataclasses import dataclass
import random
from enum import Enum


# Top right, top left, bottom left, bottom right.
OBLIQUE_CORNERS = {
    7,
    11,
    14,
    13,
}
OBLIQUE_CHARS = {13: "┌", 14: "┐", 11: "└", 7: "┘"}

# Top right, top left, bottom left, bottom right.
ACCUTE_CORNERS = {1, 2, 4, 8}
WALL_DIRECTIONS = {
    1: ((0, -1), (1, 0)),
    2: ((0, -1), (-1, 0)),
    4: ((0, 1), (-1, 0)),
    8: ((0, 1), (1, 0)),
}
ACCUTE_CHARS = {1: "┐", 2: "┌", 4: "└", 8: "┘"}


class Axis(Enum):
    Y = 0
    X = 1

    def other(self):
        if self == Axis.Y:
            return Axis.X
        else:
            return Axis.Y


@dataclass
class Room:
    x: int
    y: int
    width: int
    height: int
    world_width: int
    world_height: int

    def overlaps(self, other: "Room") -> bool:
        # The logic here is that if one of the rectangles is the the right or
        # below the other, then by definition, they can't be overlapping.
        if self.x >= other.x + other.width or other.x >= self.x + self.width:
            return False
        if self.y >= other.y + other.height or other.y >= self.y + self.height:
            return False
        return True

    def within_bounds(self) -> bool:
        return (
            0 < self.x < self.world_width - 1 - self.width
            and 0 < self.y < self.world_height - 1 - self.height
        )


class DividerType(Enum):
    ROCK = 0
    LEDGE = 1


@dataclass
class Tile:
    x: int
    y: int
    world_width: int
    world_height: int
    # Used for flood fill.
    visited: bool = False
    # 0 is floor, 15 is solid wall. For now, starting out unset.
    value: int = -1
    # Dividing walls are treated different than the solid walls that make up the
    # original space.
    is_dividing_wall: bool = False
    is_walkable: bool = False
    is_vertical_divider: bool = False
    divider_type: DividerType = DividerType.ROCK

    def in_world_bounds(self) -> bool:
        """Includes a 1-tile buffer around the outside."""
        return 0 < self.x < self.world_width - 1 and 0 < self.y < self.world_height - 1

    def possible_wall_directions(self):
        # FIXME: this is a regression over the previous version, since now we're
        #   not handling the ends of 1-tile thick walls
        if self.value in ACCUTE_CORNERS:
            return [(self, direction) for direction in WALL_DIRECTIONS[self.value]]
        return []


class Generator:
    def __init__(
        self,
        width=40,
        height=40,
        *,
        world=None,
        from_string="",
        from_file="",
        seed: int | None = None,
    ):
        if seed is not None:
            random.seed(seed)

        self.width = width
        self.height = height

        if world:
            self.world = world
        else:
            self.world: list[list[Tile]] = [
                [Tile(x, y, self.width, self.height) for x in range(self.width)]
                for y in range(self.height)
            ]

        self.floor_space = 0
        self.rooms: list[Room] = []

        self.from_string = from_string
        self.from_file = from_file

        if world:
            # We only want to load from a string or file if we didn't pass in a
            # world.
            pass
        elif from_string:
            self.load_world_from_string(from_string)
        elif from_file:
            self.load_world_from_file(from_file)
        else:
            pass
            # self.try_generation()

    def reset(self):
        self.world = [
            [Tile(x, y, self.width, self.height) for x in range(self.width)]
            for y in range(self.height)
        ]
        self.floor_space = 0
        self.rooms = []

    def load_world_from_string(self, world_string: str):
        pass

    def load_world_from_file(self, filename: str):
        pass

    def place_starting_rooms(self):
        # In the future, we'll randomly choose three spots.
        # For now, we'll go for the center.
        starting_room = 15, 20, 10, 10
        return Room(*starting_room, self.width, self.height)

    def fill_room(self, room: Room):
        self.floor_space += room.width * room.height
        for i in range(room.y, room.y + room.height):
            for j in range(room.x, room.x + room.width):
                self.world[i][j].is_walkable = True

    def bud(self, starting_room: Room, axis: Axis, bugged=False):
        # 25% chance to switch the axis.
        axis = random.choices((axis, axis.other()), cum_weights=(75, 100))[0]

        if axis == Axis.Y or bugged:
            room1, room2 = self.get_new_room_coords(starting_room, Axis.Y)
            self.try_budding(room1, axis)
            self.try_budding(room2, axis)

        if axis == Axis.X or bugged:
            room1, room2 = self.get_new_room_coords(starting_room, Axis.X)
            self.try_budding(room1, axis)
            self.try_budding(room2, axis)

    def try_budding(self, room, axis):
        if not room.within_bounds():
            return
        for existing_room in self.rooms:
            if room.overlaps(existing_room):
                return
        self.rooms.append(room)
        self.bud(room, axis.other())

    def get_new_room_coords(self, starting_room: Room, axis: Axis):
        room_width = random.choice((2, 4, 6))
        room_height = random.choice((2, 4, 6))

        vertical_center = starting_room.y + (starting_room.height // 2)
        horzontal_center = starting_room.x + (starting_room.width // 2)

        # Calculate the shifting x and y cooridinates for the 4 possible rooms.
        room_x_top_and_bottom = horzontal_center - (room_width // 2)
        room_y_top = starting_room.y - room_height
        room_y_bottom = starting_room.y + starting_room.height
        room_y_left_and_right = vertical_center - (room_height // 2)
        room_x_left = starting_room.x - room_width
        room_x_right = starting_room.x + starting_room.width

        if axis == Axis.Y:
            return (
                Room(
                    room_x_top_and_bottom,
                    room_y_top,
                    room_width,
                    room_height,
                    self.width,
                    self.height,
                ),
                Room(
                    room_x_top_and_bottom,
                    room_y_bottom,
                    room_width,
                    room_height,
                    self.width,
                    self.height,
                ),
            )
        else:
            return (
                Room(
                    room_x_left,
                    room_y_left_and_right,
                    room_width,
                    room_height,
                    self.width,
                    self.height,
                ),
                Room(
                    room_x_right,
                    room_y_left_and_right,
                    room_width,
                    room_height,
                    self.width,
                    self.height,
                ),
            )

    def marching_squares(self):
        """
        Firther reading:
            https://en.wikipedia.org/wiki/Marching_squares
            https://www.boristhebrave.com/2018/04/15/marching-cubes-tutorial/
        """
        # False for any corner of a walkable tile, true otherwise
        corner_grid = [
            [True for _x in range(self.width + 1)] for _y in range(self.height + 1)
        ]

        # First, we calculate the corners.
        offsets = ((-1, -1), (-1, 0), (0, -1), (0, 0))
        for y in range(1, self.height):
            for x in range(1, self.width):
                # Each corner is a corner of four cells. We can think of the corner
                # grid as being offset from the world grid by half a tile in each
                # direction. So an offset of (-1, -1) is the tile to the top-left of
                # of the corner (or from the other way, the corner is the
                # bottom-right of that tile), while an offset of (0, 0) is to the
                # bottom right.
                for dx, dy in offsets:
                    t = self.world[y + dy][x + dx]
                    if t.is_walkable or t.is_dividing_wall:
                        corner_grid[y][x] = False
                        break

        # Then, we figure out the value of the tile, based on the corners.
        # Note that these offsets are in the opposite direction, now that we're
        # going from tiles to corners. The order of offsets *does* matter. Top left,
        # top right, bottom right, bottom left.
        offsets = ((0, 0), (1, 0), (1, 1), (0, 1))
        for y in range(self.height):
            for x in range(self.width):
                t = self.world[y][x]
                t.value = 0
                for i, (dx, dy) in enumerate(offsets):
                    t.value |= corner_grid[y + dy][x + dx]
                    t.value <<= 1
                t.value >>= 1

    def add_wall(self, tile: Tile, direction: tuple[int, int]):
        """Adds a wall stretching along a random axis from a corner to the next wall."""
        dx, dy = direction
        # Save the original position, but stepped in once so it's a newly added wall
        # tile.
        og_x, og_y = tile.x + dx, tile.y + dy
        x, y = og_x, og_y
        # This list holds all the actual wall tiles. This doesn't includes walls
        # that were transmuted into solid walls. This way, we don't open a door that
        # leads to a solid wall. Each nested list represents a span of walls that
        # have walkable tiles on each side, all of which need a doorway.
        wall_tiles: list[list[Tile]] = [[]]
        while True:
            current_tile = self.world[y][x]
            side1_tile = self.world[y + dx][x + dy]
            side2_tile = self.world[y - dx][x - dy]

            # Test if we've hit a wall.
            if not current_tile.is_walkable:
                # Back it up a step so the last x,y is a newly added wall tile.
                x, y = x - dx, y - dy
                break

            current_tile.is_walkable = False
            # TODO: Try aborting wall generation instead of transmuting it. Then
            #   continue on and pick a different corner.
            # Check if we're passing by a wall of either type. If we are, we just turn the
            # dividing wall into a solid wall, so the dungeon looks more natural.
            # Also, if the wall we're passing by is a dividing wall, we turn it into
            # a solid wall as well.
            if side1_tile.is_walkable and side2_tile.is_walkable:
                current_tile.is_dividing_wall = True
                current_tile.is_vertical_divider = bool(direction[1])
                wall_tiles[-1].append(current_tile)
            else:
                # if not side1_tile.is_walkable:
                #     side1_tile.is_dividing_wall = False
                # if not side2_tile.is_walkable:
                #     side2_tile.is_dividing_wall = False
                # We create a new span if there's not an empty one at the end.
                if wall_tiles[-1]:
                    wall_tiles.append([])

            self.floor_space -= 1
            # Take a step forward.
            x, y = x + dx, y + dy

        # Test if the wall never went anywhere, which can happen if another wall
        # runs up against this corner.
        if (x, y) == (tile.x, tile.y):
            return

        # Add doorways to all spans.
        for span in wall_tiles:
            if not span:
                continue
            doorway_tile = random.choice(span)
            doorway_tile.is_walkable = True
            doorway_tile.is_dividing_wall = False
            self.floor_space += 1

    def pathable(self) -> tuple[bool, int]:
        # First, we collect all the floor tiles and set the visibility. Tiles
        # are created with visibility set to False, however, we might rerun this
        # algorithm multiple times with the same set of tiles.
        floor_tiles = [tile for row in self.world for tile in row if tile.is_walkable]
        for tile in floor_tiles:
            tile.visited = False
        # Then, we pick any floor tile and flood fill, counting the number of
        # touched tiles. If, at the end, we touched the same number as
        # len(floor_tiles), then everything is pathable. Otherwise, it means there's
        # an inacessible room.
        offsets = [(-1, 0), (0, -1), (1, 0), (0, 1)]  # left, up, right, down
        tile_stack = [floor_tiles[0]]
        visited_count = 0
        while tile_stack:
            tile = tile_stack.pop()
            if tile.visited:
                continue
            tile.visited = True
            visited_count += 1
            for dx, dy in offsets:
                neighbor = self.world[tile.y + dy][tile.x + dx]
                if neighbor.is_walkable and neighbor.visited == False:
                    tile_stack.append(neighbor)
        # print(f"Visited {visited_count}/{len(floor_tiles)}")
        return visited_count == len(floor_tiles), len(floor_tiles)

    def add_walls(self):
        possible_walls = []
        for row in self.world:
            for tile in row:
                possible_walls.extend(tile.possible_wall_directions())

        for tile, direction in random.sample(
            possible_walls, k=len(possible_walls) // 3
        ):
            self.add_wall(tile, direction)

    def generate_world(self):
        starting_room = self.place_starting_rooms()
        self.rooms.append(starting_room)
        self.bud(starting_room, random.choice((Axis.Y, Axis.X)))
        # Now we calculate initial floorspace:
        for room in self.rooms:
            self.floor_space += room.width * room.height
        # TODO: refactor everything
        if self.floor_space < 700:
            return
        # Carve out the rooms.
        for room in self.rooms:
            for y in range(room.y, room.y + room.height):
                for x in range(room.x, room.x + room.width):
                    self.world[y][x].is_walkable = True

        self.marching_squares()
        self.add_walls()
        # Recalculate the wall edges, because the wall-adding step might have
        # changed some dividing walls into solid walls.
        self.marching_squares()

    def try_generation(self, max_tries=-1, required_floor_space=700):
        tries = 0
        pathable_called = 0
        while tries < max_tries or max_tries == -1:
            tries += 1
            self.generate_world()
            if self.floor_space < required_floor_space:
                continue
            pathable_called += 1
            can_path, size = self.pathable()
            if can_path and size >= required_floor_space:
                break
            self.reset()
            # if not can_path:
            #     print_world()
        # print("Called pathable()", pathable_called, "times.")

        return tries, self.world
