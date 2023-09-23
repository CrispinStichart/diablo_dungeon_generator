import diablo1_dungeon_generation as d1
import pickle


def world_to_string(world, spaces=2):
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"

    divider_characters = {True: "║", False: "═"}
    accute_chars = {1: "┐", 2: "┌", 4: "└", 8: "┘"}
    oblique_chars = {13: "┌", 14: "┐", 11: "└", 7: "┘"}

    lines = []
    for row in world:
        row_str = []
        for tile in row:
            if tile.is_walkable:
                if tile.visited:
                    tile_char = "."
                else:
                    tile_char = RED + "."
            elif tile.value == 0 and not tile.is_walkable and not tile.is_dividing_wall:
                tile_char = "o"
            elif tile.is_dividing_wall:
                tile_char = BLUE + divider_characters[tile.is_vertical_divider]
            elif tile.value in d1.ACCUTE_CORNERS:
                tile_char = YELLOW + accute_chars[tile.value]
            elif tile.value in d1.OBLIQUE_CORNERS:
                tile_char = YELLOW + oblique_chars[tile.value]
            elif tile.value == 15:
                tile_char = "#"
            elif tile.value in {3, 12}:
                tile_char = YELLOW + "—"
            elif tile.value in {6, 9}:
                tile_char = YELLOW + "|"
            elif tile.is_dividing_wall:
                tile_char = GREEN + "$"
            else:
                tile_char = RED + chr(97 + tile.value)
            row_str.append(tile_char + ENDC)
        lines.append((" " * 2).join(row_str))

    return "\n".join(lines)


def benchmark():
    generator = d1.Generator()
    rounds = 1000
    total_tries = 0
    for _i in range(rounds):
        this_round_tries, _ = generator.try_generation()
        total_tries += this_round_tries
        print(f"Try {_i}, took average so far: {total_tries/(_i+1)}")


def main():
    try:
        with open("output/world_without_walls.pickle", "rb") as f:
            world = pickle.load(f)
            generator = d1.Generator(world=world, seed=666)
            generator.add_walls()
            generator.marching_squares()
            can_path, size = generator.pathable()

            print(world_to_string(world))
            print(f"{'' if can_path else 'Not '}Pathable, {size} tiles.")

    except FileNotFoundError:
        print("Creating new world")
        generator = d1.Generator()
        tries, world = generator.try_generation()
        print(f"Took {tries} tries.")

        with open("output/world_without_walls.pickle", "wb") as f:
            pickle.dump(world, f)


if __name__ == "__main__":
    main()
    # benchmark()
