"""
For further reading about the Diablo 1 generation algorithm, see:
https://www.boristhebrave.com/2019/07/14/dungeon-generation-in-diablo-1/
"""
from dataclasses import dataclass
import random
from enum import Enum
from typing import List, Tuple, Any

# Top right, top left, bottom left, bottom right.
OBLIQUE_CORNERS = {
    7,
    11,
    14,
    13,
}

# Top right, top left, bottom left, bottom right.
ACCUTE_CORNERS = {1, 2, 4, 8}
WALL_DIRECTIONS = {
    1: ((0, -1), (1, 0)),
    2: ((0, -1), (-1, 0)),
    4: ((0, 1), (-1, 0)),
    8: ((0, 1), (1, 0)),
}


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
        """Return true if this room overlaps with the other room."""
        # The logic here is that if one of the rectangles is to the right or
        # below the other, then by definition, they can't be overlapping.
        if self.x >= other.x + other.width or other.x >= self.x + self.width:
            return False
        if self.y >= other.y + other.height or other.y >= self.y + self.height:
            return False
        return True

    def within_bounds(self) -> bool:
        """
        Returns true if the room is contained within not just the world bounds,
        but also within a one-tile buffer around the edge of the world.
        """
        return (
            0 < self.x < self.world_width - 1 - self.width
            and 0 < self.y < self.world_height - 1 - self.height
        )


@dataclass
class Tile:
    x: int
    y: int
    world_width: int
    world_height: int
    # Used when we check if the map is pathable.
    visited: bool = False
    # 0 is floor (usually), 15 is interior wall.
    value: int = 15
    # the value will also be 0 if it's a wall that's bordered by floor tiles. So
    # we also need to track whether it's a walkable floor or a dividing wall.
    is_walkable: bool = False
    # Dividing walls are treated different than the solid walls that make up the
    # original space.
    is_dividing_wall: bool = False
    # Dividing walls can go vertically or horizontally. We keep track of the
    # orientation so we can render them differently later.
    is_vertical_divider: bool = False
    # A span connection is a dividing wall tile that intersects perpendiclarly
    # with onother dividing wall.
    is_span_connection = False

    def in_world_bounds(self) -> bool:
        """Includes a 1-tile buffer around the outside."""
        return 0 < self.x < self.world_width - 1 and 0 < self.y < self.world_height - 1

    def possible_wall_directions(self) -> list[tuple["Tile", tuple[int, int]]]:
        """
        Returns the tile, and direction a wall can go in from this point.
        It only applies to accute corners, others return an empty list.
        """
        # FIXME: this is a regression over the previous version, since now we're
        #   not handling the ends of 1-tile thick walls. Of course, maybe it's
        #   better this way anyway, but I should at least test it out... I don't
        #   know how D1 actually handles this.
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
        seed: int | None = None,
    ):
        if seed is not None:
            random.seed(seed)

        self.width = width
        self.height = height

        # Used for debugging -- we can pickle a world and reload it from disk.
        # Useful when making changes to the wall generation.
        if world:
            self.world = world
        else:
            self.world: list[list[Tile]] = [
                [Tile(x, y, self.width, self.height) for x in range(self.width)]
                for y in range(self.height)
            ]

        # How many tries it took to genrate the world.
        self.tries: int = 0
        # How many walkable tiles there are.
        self.floor_space: int = 0
        # All the rooms that have been created. Only used for the initial room
        # placement, after which we deal with the world matrix directly.
        self.rooms: list[Room] = []
        # Pending room possiblities. These possibilities won't be checked for
        # valididty until we attempt to place them.
        self.rooms_to_bud: list[tuple[Room, Axis]] = []

    def reset(self) -> None:
        """If at first you don't succeeed..."""
        self.world = [
            [Tile(x, y, self.width, self.height) for x in range(self.width)]
            for y in range(self.height)
        ]
        self.floor_space = 0
        self.rooms = []

    def create_starting_rooms(self) -> list[tuple[Room, Axis]]:
        # TODO: In the actual D1 code, they pick 1-3 pre-chosen locations for
        #   the 10x10 rooms, and draw a centeral coridor between them.
        starting_room = 15, 20, 10, 10
        return [
            (
                Room(*starting_room, self.width, self.height),
                random.choice((Axis.Y, Axis.X)),
            )
        ]

    def add_room_candidates(self, room: Room, axis: Axis, both=False):
        """
        When a room is placed, it adds two candidate rooms on either side. These
        rooms aren't necessarily placed right away, and they aren't checked for
        valididty until later.
        """
        # 25% chance to switch the axis. Note that the axis passed in was the
        # opposite of the parent, so the result is that the generator prefers a
        # branching dungeon, but there's a 25% chance of continuing the room and
        # creating a corridor. Doesn't matter if `both` is set to True.
        axis = random.choices((axis, axis.other()), cum_weights=(75, 100))[0]

        if axis == Axis.Y or both:
            room1, room2 = self.get_new_room_coords(room, Axis.Y)
            self.rooms_to_bud.append((room1, axis))
            self.rooms_to_bud.append((room2, axis))
        if axis == Axis.X or both:
            room1, room2 = self.get_new_room_coords(room, Axis.X)
            self.rooms_to_bud.append((room1, axis))
            self.rooms_to_bud.append((room2, axis))

    def get_new_room_coords(self, starting_room: Room, axis: Axis):
        """
        Calculates the coordinates for the two rooms that are branching off from
        `starting_room` along `axis`.
        """
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

    def try_budding(self, room, axis):
        """
        `room` is an unverified candidate room location. In this method, we
        verify that we can actually place it (that it doesn't overlap with
        another room or extend out of bounds), and then we place it and
        calculate two more candidate room locations.
        """
        if not room.within_bounds():
            return
        for existing_room in self.rooms:
            if room.overlaps(existing_room):
                return
        self.rooms.append(room)
        self.add_room_candidates(room, axis)

    def marching_squares(self) -> None:
        """
        This is used to figure out while wall tiles are corners (either oblique
        or accute) or just side walls. This is so that when we draw the map,
        either in ASCII or with tiles, we can use different characters/tiles for
        those spots so it looks pretty.

        Further reading:
            https://en.wikipedia.org/wiki/Marching_squares
            https://www.boristhebrave.com/2018/04/15/marching-cubes-tutorial/
        """
        # Please note: this is not the most efficent way to do things. I am aware.

        # False for any corner of a walkable tile, true otherwise.
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

                # I experimented with deleting walls that are on their own. The
                # result is that the layout before adding the dividing walls is
                # clean, so the dividing walls tend to stretch further. I didn't
                # really like the look, but it be the right thing for certain
                # types of games.
                # if t.value == 0 and not t.is_dividing_wall:
                #     t.is_walkable = True

    def pathable(self) -> bool:
        """
        Uses a flood-fill to make sure that every tile is reachable from any
        others. This might not be true if we get really unlucky with the
        generation.
        """
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
        tile_stack = [floor_tiles[0]] if floor_tiles else []
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

        pathable = visited_count == len(floor_tiles)

        # I've been keeping track of walkable tiles in self.floor_space, but I
        # want to make sure I didn't mess that up.
        if pathable and visited_count != self.floor_space:
            raise Exception(
                f"visited_count ({visited_count}) doesn't match self.floor_space ({self.floor_space})"
            )

        return pathable

    def add_wall(self, tile: Tile, direction: tuple[int, int]) -> list[list[Tile]]:
        """
        Adds a wall stretching along the chosen direction from an accute corner to the
        next wall. If it passes by another wall (solid or dividing) it doesn't
        place the dividing wall, but that doesn't abort the wall placement.
        Whenever that happens, it starts starts a new list. The idea is that
        each list represents a span of wall tiles that will need a doorway
        added. However, we don't do the doorway placement here, because if we do
        there's a chance of creating an unreachable area.
        """
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
                # Mark where a wall t-bones another.
                if current_tile.is_dividing_wall:
                    current_tile.is_span_connection = True
                # Back it up a step so the last x,y is a newly added wall tile.
                x, y = x - dx, y - dy
                break

            # TODO: Try aborting wall generation instead of transmuting it. Then
            #   continue on and pick a different corner.
            # TODO: Try creating solid wall instead of skipping. Would need to
            #   rerun marching squares afterword, unless we fix up the tile and
            #   neighbors as we do it.
            # Only places a dividing wall tiles if there's an empty tile on
            # either side. This is to avoid running a wall against another wall,
            # which just looks weird.
            if side1_tile.is_walkable and side2_tile.is_walkable:
                current_tile.is_walkable = False
                current_tile.is_dividing_wall = True
                current_tile.is_vertical_divider = bool(direction[1])

                wall_tiles[-1].append(current_tile)
                self.floor_space -= 1
            else:
                # We create a new span if there's not an empty one at the end.
                if wall_tiles[-1]:
                    wall_tiles.append([])

            # Take a step forward.
            x, y = x + dx, y + dy

        return wall_tiles

    def add_walls(self) -> list[list[Tile]]:
        """
        Here we're finding all the accute corners/direction pairs. So if we have
        an acute corner that's facing to the lower right, a wall can extend from
        that corner to the right or downward. So two tuples are being added:
        (<tile>, (1, 0)), and (<tile>, (0, 1)).
        """
        possible_walls = []
        for row in self.world:
            for tile in row:
                possible_walls.extend(tile.possible_wall_directions())

        # A 1/3 ratio looks good to me.
        wall_spans: list[list[Tile]] = []
        for tile, direction in random.sample(
            possible_walls, k=len(possible_walls) // 3
        ):
            wall_spans.extend(self.add_wall(tile, direction))

        return wall_spans

    def add_doors(self, spans):
        """
        Adds all the doors, although first it has to check the spans for spots
        where they intersect, and split the span at that spot.
        """
        # First, we need to check the spans for intersecting walls. We marked
        # the location of such in the add_walls() step, now we need to actually
        # split the span.
        checked_spans = []
        for span in spans:
            start = 0
            for i, tile in enumerate(span):
                if tile.is_span_connection:
                    new_span = span[start:i]
                    if new_span:
                        checked_spans.append(new_span)
                    start = i + 1
            new_span = span[start:]
            if new_span:
                checked_spans.append(new_span)

        # Add doorways to all spans.
        for span in checked_spans:
            if not span:
                continue
            doorway_tile = random.choice(span)
            doorway_tile.is_walkable = True
            doorway_tile.is_dividing_wall = False
            self.floor_space += 1

    def add_rooms(self):
        """
        This kicks off the main stage of generation. Note that we're not
        touching the world matrix yet, we're just creating a list of Room
        objects.
        """
        starting_room_and_axis = self.create_starting_rooms()
        self.rooms_to_bud.extend(starting_room_and_axis)
        while self.rooms_to_bud:
            # Treating rooms_to_bud as a queue (first in, first out) seems to
            # generate, on average, a more spacious, branching level.
            room, axis = self.rooms_to_bud.pop(0)
            self.try_budding(room, axis)

    def generate_world(self, required_floor_space: int):
        """
        This function is one full generation attempt.
        """
        # Place all the rooms.
        self.add_rooms()

        # Now we calculate initial floorspace before adding the walls
        for room in self.rooms:
            self.floor_space += room.width * room.height

        # We want to skip the expense of doing the rest of the algorithm if we
        # know we've already failed to meet the floor space requirements.
        if self.floor_space < required_floor_space:
            return
        # Carve out the rooms.
        for room in self.rooms:
            for y in range(room.y, room.y + room.height):
                for x in range(room.x, room.x + room.width):
                    self.world[y][x].is_walkable = True

        # Marks tiles, mostly for display purposes, but also to figure out where
        # accute corners are, which we need to know to place the walls.
        self.marching_squares()
        # Place the walls...
        spans = self.add_walls()
        # ...and guess what this method does?
        self.add_doors(spans)

    def try_generation(self, max_tries=-1, required_floor_space=500):
        """
        Repeatedly tries the generation until it creates a fully pathable map
        with the required floor space. Fun fact: this is what Diablo 1 actually
        did! Who needs fancy algorithms that get things right on the first try
        when you can just... try again?

        Careful with setting the required floor space too high. With a 40x40
        map, 500 seems like a good fit, with the average number of tries being
        25, which is basically instant. But as I was writing this, I tried 700,
        and it took 19760 tries, which took at least a full 5 seconds on my
        machine.
        """
        self.tries = 0
        pathable_called = 0
        while self.tries < max_tries or max_tries == -1:
            self.reset()

            self.tries += 1
            self.generate_world(required_floor_space)
            if self.floor_space < required_floor_space:
                continue
            pathable_called += 1
            can_path = self.pathable()
            if can_path and self.floor_space >= required_floor_space:
                break
