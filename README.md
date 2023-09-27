# Diablo 1 Dungeon Generator

This script implements (most of) the Diablo 1 dungeon generation algorithm as described [here](https://www.boristhebrave.com/2019/07/14/dungeon-generation-in-diablo-1/
). Specifically, the Cathedral levels.

Also included is a script, `pokemon_generator.py`, that uses the first-gen pokemon cave tileset to render the result of the generation.

# Limitations

Currently not implementing the starting rooms the way D1 does it, with a chance for multiple preset rooms connected by a corridor. 

Also, not handling "saddle points", where a tile could be rendered as either corner. See the screenshots directory for examples. The pokemon ones just leave the tile blank, and the ascii one displays a scarlet letter.

# Examples

See the examples directory for more examples.

# License

All code is MIT. Pokemon tileset used without permission. I expect to be killed by Nintendo lawyer-assasins any day now.