from PIL import Image
from os import listdir
import diablo1_dungeon_generation as d1

TILE_DIR = r"C:\Users\Crispin Stichart\Pictures\pokemon_cave_tileset\deep\\"
TILE_SIZE = 32
def load_tiles():
    tiles = {}
    for tile_filename in listdir(TILE_DIR):
        tile_path = TILE_DIR + tile_filename
        tile_img = Image.open(tile_path)
        tiles[tile_filename.rstrip(".png")] = tile_img

    return tiles


def main():
    # Load the tiles.
    tiles = load_tiles()
    # Set up the empty canvas.
    size = (d1.MAP_SIZE * TILE_SIZE, d1.MAP_SIZE * TILE_SIZE)
    canvas = Image.new("RGBA", size)
    # Arange the sprites on the canvas.
    _, world = d1.try_generation()
    for row in world:
        for tile in row:
            sprite = None
            if tile.is_dividing_wall:
                sprite = tiles["rock"]
            elif not tile.is_walkable and tile.value == 0:
                sprite = tiles["cracked_rock"]
            else:
                sprite = tiles.get(str(tile.value))
            if sprite:
                canvas.paste(sprite, (tile.x * TILE_SIZE, tile.y * TILE_SIZE))

    canvas.save("pokemon_dungeon.png")


if __name__ == "__main__":
    main()
