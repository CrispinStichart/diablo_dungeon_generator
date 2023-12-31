import pickle

from PIL import Image
from os import listdir
import diablo1_dungeon_generation as d1

TILE_DIR = "pokemon_tileset/"
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
    # Create the generator.
    generator = d1.Generator()
    # Create a blank canvas.
    size = (generator.width * TILE_SIZE, generator.height * TILE_SIZE)
    canvas = Image.new("RGBA", size)
    # Arange the sprites on the canvas.
    generator.try_generation()
    for row in generator.world:
        for tile in row:
            if tile.is_dividing_wall:
                sprite = tiles["rock"]
            elif not tile.is_walkable and tile.value == 0:
                sprite = tiles["cracked_rock"]
            else:
                sprite = tiles.get(str(tile.value))
            if sprite:
                canvas.paste(sprite, (tile.x * TILE_SIZE, tile.y * TILE_SIZE))

    canvas.save("output/pokemon_dungeon.png")


if __name__ == "__main__":
    main()
