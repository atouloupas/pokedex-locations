# Generation 4 Pokédex Locations & Obtain Guide

A web application to search, filter, and discover exactly where and how to obtain all 493 Pokémon across the Generation IV games: **Pokémon Diamond, Pearl, Platinum, HeartGold, and SoulSilver**.

Live Webpage: https://atouloupas.github.io/pokedex-locations/

## Features

- **Dynamic Search**: Instant search by Pokémon name, National ID, or game-specific Pokédex numbers.
- **Game-Specific Data**: Dynamically swaps the encounter methods and location lists when you change the active game.
- **Advanced Filtering**:
  - **Encounter Methods**: Filter by Wild Encounter, Evolution, Gift, Gift Egg, Breeding, Only One / Static, Trade / Transfer, and Event.
  - **Encounter Conditions**: Filter by Poké Radar, Swarms, Headbutt Trees, Honey Trees, Time Events, and specific **GBA Slot cartridge insertions** (Ruby, Sapphire, Emerald, FireRed, LeafGreen).
- **Redirection Links**: Clicking on an evolution parent redirects you to their entry. Clicking a Pokémon name links directly to its Bulbapedia entry.
- **Interactive Mechanics Guide**: Built-in modal explaining Generation IV encounter mechanics.

## Technology Stack

- **Frontend**: HTML5, Vanilla CSS3 (Slate-Dark Glassmorphic design system), Vanilla JavaScript (ES6+).
- **Backend Compiler**: Python 3 script (`compile_pokedex.py`) that queries PokeAPI, caches responses locally to prevent rate limiting, filters out non-Gen-IV data (like Fairy types or future evolutions), and compiles the final dataset into `data/pokedex_gen4.json`.

## Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/atouloupas/pokedex-locations.git
   cd pokedex-locations
   ```
2. **Run the local server**:
   Start a local server to view the webpage:
   ```bash
   python -m http.server 8000
   ```
   Open your browser and navigate to `http://localhost:8000`.

3. **Recompiling the Database (Optional)**:
   If you wish to modify the compilation filters or update the database, run:
   ```bash
   python compile_pokedex.py
   ```
