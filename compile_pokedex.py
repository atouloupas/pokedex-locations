import os
import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = os.path.join("data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

GEN4_GAMES = ["diamond", "pearl", "platinum", "heartgold", "soulsilver"]

# Mythical Pokemon list for Gen 4
MYTHICALS = {
    "mew", "celebi", "jirachi", "deoxys", "phione", "manaphy", "darkrai", "shaymin", "arceus"
}

# Fairy type was introduced in Gen 6. Override to old types for Gen 4 accuracy.
GEN4_TYPE_OVERRIDES = {
    "cleffa": ["normal"],
    "clefairy": ["normal"],
    "clefable": ["normal"],
    "togepi": ["normal"],
    "togetic": ["normal", "flying"],
    "togekiss": ["normal", "flying"],
    "igglybuff": ["normal"],
    "jigglypuff": ["normal"],
    "wigglytuff": ["normal"],
    "ralts": ["psychic"],
    "kirlia": ["psychic"],
    "gardevoir": ["psychic"],
    "azurill": ["normal"],
    "marill": ["water"],
    "azumarill": ["water"],
    "mawile": ["steel"],
    "snubbull": ["normal"],
    "granbull": ["normal"],
    "mr-mime": ["psychic"],
    "mime-jr": ["psychic"]
}


def clean_name(name):
    if not name:
        return ""
    # Capitalize and replace hyphens with spaces
    # Special cases
    special = {
        "mr-mime": "Mr. Mime",
        "mime-jr": "Mime Jr.",
        "porygon-z": "Porygon-Z",
        "ho-oh": "Ho-Oh",
        "nidoran-f": "Nidoran ♀",
        "nidoran-m": "Nidoran ♂",
        "deoxys-normal": "Deoxys",
        "giratina-altered": "Giratina",
        "shaymin-land": "Shaymin",
        "wormadam-plant": "Wormadam",
        "farfetchd": "Farfetch'd",
        "heartgold": "HeartGold",
        "soulsilver": "SoulSilver"
    }
    if name.lower() in special:
        return special[name.lower()]
    return name.replace("-", " ").title()

def clean_location(name):
    if not name:
        return ""
    # Remove trailing -area or -zone
    if name.endswith("-area"):
        name = name[:-5]
    elif name.endswith("-zone"):
        name = name[:-5]
        
    parts = name.split("-")
    cleaned_parts = []
    for p in parts:
        if p.lower() in ["1f", "2f", "3f", "4f", "5f", "6f", "b1f", "b2f", "b3f", "b4f", "b5f", "lg"]:
            cleaned_parts.append(p.upper())
        elif p.lower() == "mt":
            cleaned_parts.append("Mt.")
        elif p.lower() in ["sinnoh", "johto", "kanto"]:
            # Skip region prefix
            continue
        else:
            cleaned_parts.append(p.capitalize())
            
    # Handle route- -> Route format
    res = " ".join(cleaned_parts).strip()
    if res.startswith("Route "):
        pass
    elif "Route " in res:
        pass
    else:
        # If route is in parts, we should make sure it looks like "Route X"
        res = res.replace("Route", "Route ")
        
    # Replace double spaces if any
    res = " ".join(res.split())
    return res

def clean_method(method):
    mapping = {
        "walk": "Walking",
        "surf": "Surfing",
        "old-rod": "Fishing (Old Rod)",
        "good-rod": "Fishing (Good Rod)",
        "super-rod": "Fishing (Super Rod)",
        "gift": "Gift",
        "gift-egg": "Gift Egg",
        "only-one": "Only One / Static",
        "headbutt": "Headbutt Trees",
        "rock-smash": "Rock Smash",
        "pokeflute": "Poké Flute",
        "sea-incense": "Sea Incense",
        "lax-incense": "Lax Incense",
        "dark-cave-crebo": "Dark Cave Crebo",
        "squirtbottle": "Squirtbottle",
        "feebas-tile-fishing": "Fishing (Feebas Tile)",
        "purify-smeargle": "Purify Smeargle",
    }
    return mapping.get(method, method.replace("-", " ").title())

def fetch_json(url):
    # Create a safe filename from the URL
    safe_name = url.replace("https://pokeapi.co/api/v2/", "").replace("/", "_").strip("_") + ".json"
    cache_path = os.path.join(CACHE_DIR, safe_name)
    
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                pass # If it's corrupted, refetch
                
    # Fetch from API
    time.sleep(0.02) # Be nice to PokeAPI
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 404:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"error": 404}, f)
            return None
        res.raise_for_status()
        data = res.json()
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_species_task(sid):
    species_url = f"https://pokeapi.co/api/v2/pokemon-species/{sid}/"
    species_data = fetch_json(species_url)
    if not species_data or "error" in species_data:
        return None
        
    # Find default variety
    default_variety = None
    for v in species_data.get("varieties", []):
        if v.get("is_default"):
            default_variety = v["pokemon"]["name"]
            break
    if not default_variety and species_data.get("varieties"):
        default_variety = species_data["varieties"][0]["pokemon"]["name"]
    if not default_variety:
        default_variety = species_data["name"]
        
    # Fetch pokemon detail
    poke_url = f"https://pokeapi.co/api/v2/pokemon/{default_variety}/"
    poke_data = fetch_json(poke_url)
    
    # Fetch encounters
    enc_url = f"https://pokeapi.co/api/v2/pokemon/{default_variety}/encounters"
    enc_data = fetch_json(enc_url)
    
    return {
        "id": sid,
        "species": species_data,
        "pokemon": poke_data,
        "encounters": enc_data,
        "variety_name": default_variety
    }

def main():
    print("Step 1: Fetching all species (1-493) and their data...")
    raw_data = []
    
    # Use ThreadPoolExecutor for concurrent fetching
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_species_task, i): i for i in range(1, 494)}
        for future in as_completed(futures):
            sid = futures[future]
            try:
                res = future.result()
                if res:
                    raw_data.append(res)
                    if len(raw_data) % 50 == 0:
                        print(f"  Fetched {len(raw_data)}/493 Pokémon...")
            except Exception as e:
                print(f"Error fetching species {sid}: {e}")
                
    # Sort raw_data by ID
    raw_data.sort(key=lambda x: x["id"])
    print(f"Successfully loaded details for {len(raw_data)} species.")

    # Step 2: Fetch unique evolution chains
    print("Step 2: Fetching evolution chains...")
    chain_urls = set()
    for item in raw_data:
        chain_url = item["species"]["evolution_chain"]["url"]
        chain_urls.add(chain_url)
        
    print(f"Found {len(chain_urls)} unique evolution chains. Fetching...")
    chains_data = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_json, url): url for url in chain_urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                res = future.result()
                if res:
                    # Extract chain ID from URL
                    chain_id = url.split("/")[-2]
                    chains_data[chain_id] = res
            except Exception as e:
                print(f"Error fetching chain {url}: {e}")
                
    print(f"Loaded {len(chains_data)} evolution chains.")

    # Step 3: Parse evolution chains to build species map
    print("Step 3: Parsing evolution chains...")
    evolutions_map = {}
    
    def parse_node(node, parent_name=None):
        species_name = node["species"]["name"]
        details_list = node.get("evolution_details", [])
        
        trigger_text = ""
        if details_list:
            details_strings = []
            for details in details_list:
                # Filter by version group (Gen 4 or earlier: ID <= 10)
                if details.get("version_group") is not None:
                    vg = details["version_group"]
                    vg_id = vg if isinstance(vg, int) else int(vg.get("url", "/0/").split("/")[-2])
                    if vg_id > 10:
                        continue
                # Skip if base_form is specified (regional variant evolution from other generations)
                if details.get("base_form"):
                    continue
                    
                trigger_name = details["trigger"]["name"]
                parts = []
                if trigger_name == "level-up":
                    if details.get("min_level"):
                        parts.append(f"Level {details['min_level']}")
                    if details.get("min_happiness"):
                        parts.append("High Friendship")
                    if details.get("min_beauty"):
                        parts.append("High Beauty")
                    if details.get("known_move"):
                        parts.append(f"knowing {clean_name(details['known_move']['name'])}")
                    if details.get("known_move_type"):
                        parts.append(f"knowing a {clean_name(details['known_move_type']['name'])} type move")
                    if details.get("location"):
                        parts.append(f"at {clean_name(details['location']['name'])}")
                    if details.get("time_of_day"):
                        parts.append(f"during {details['time_of_day'].title()}")
                    if details.get("held_item"):
                        parts.append(f"holding {clean_name(details['held_item']['name'])}")
                    if details.get("gender"):
                        gender_str = "Male" if details["gender"] == 2 else "Female"
                        parts.append(f"({gender_str})")
                    if details.get("relative_physical_stats") is not None:
                        stat = details["relative_physical_stats"]
                        if stat > 0:
                            parts.append("Attack > Defense")
                        elif stat < 0:
                            parts.append("Defense > Attack")
                        else:
                            parts.append("Attack = Defense")
                    
                    desc = "Level up"
                    if parts:
                        desc += " " + " + ".join(parts)
                    details_strings.append(desc)
                    
                elif trigger_name == "use-item":
                    item_name = clean_name(details["item"]["name"])
                    details_strings.append(f"Use {item_name}")
                    
                elif trigger_name == "trade":
                    held = details.get("held_item")
                    trade_species = details.get("trade_species")
                    desc = "Trade"
                    if held:
                        desc += f" holding {clean_name(held['name'])}"
                    if trade_species:
                        desc += f" for {clean_name(trade_species['name'])}"
                    details_strings.append(desc)
                    
                elif trigger_name == "shed":
                    details_strings.append("Level 20 with empty party slot and Pokéball in bag")
                else:
                    details_strings.append(f"Evolve via {trigger_name}")
            
            trigger_text = " or ".join(list(dict.fromkeys(details_strings)))
            
        evolutions_map[species_name] = {
            "evolves_from": parent_name,
            "trigger_text": trigger_text,
            "children": [child["species"]["name"] for child in node.get("evolves_to", [])]
        }
        
        for child in node.get("evolves_to", []):
            parse_node(child, species_name)

    for cid, chain_data in chains_data.items():
        if chain_data and "chain" in chain_data:
            parse_node(chain_data["chain"])

    # Step 4: Compile final database
    print("Step 4: Compiling final database...")
    compiled_pokedex = []
    
    # We will build it step by step
    # Keep track of species info for recursive parents
    pokemon_dict = {} # name -> compiled_record
    
    for item in raw_data:
        spec_data = item["species"]
        poke_data = item["pokemon"]
        enc_data = item["encounters"] or []
        variety_name = item["variety_name"]
        
        sid = item["id"]
        slug_name = spec_data["name"]
        display_name = clean_name(slug_name)
        
        # Types
        types = [t["type"]["name"] for t in poke_data.get("types", [])] if poke_data else []
        if slug_name in GEN4_TYPE_OVERRIDES:
            types = GEN4_TYPE_OVERRIDES[slug_name]
        
        # Sprite URL
        sprite_url = None
        if poke_data and "sprites" in poke_data:
            sprites = poke_data["sprites"]
            if sprites.get("other") and sprites["other"].get("official-artwork"):
                sprite_url = sprites["other"]["official-artwork"].get("front_default")
            if not sprite_url:
                sprite_url = sprites.get("front_default")
                
        # Pokedex numbers
        pokedex_numbers = {
            "national": sid
        }
        for pd in spec_data.get("pokedex_numbers", []):
            dex_name = pd["pokedex"]["name"]
            if dex_name in ["original-sinnoh", "extended-sinnoh", "updated-johto"]:
                pokedex_numbers[dex_name] = pd["entry_number"]
                
        # Evolution data
        evo = evolutions_map.get(slug_name, {"evolves_from": None, "trigger_text": ""})
        
        # Parse encounters
        game_encounters = {g: [] for g in GEN4_GAMES}
        
        for enc in enc_data:
            if "error" in enc:
                continue
            loc_slug = enc["location_area"]["name"]
            loc_display = clean_location(loc_slug)
            
            for vd in enc.get("version_details", []):
                vname = vd["version"]["name"]
                if vname in GEN4_GAMES:
                    # Skip Rocket HQ Platinum database bug for specific species
                    if vname == "platinum" and "team-rocket-hq" in loc_slug and slug_name in ["geodude", "voltorb", "electrode", "koffing"]:
                        continue
                        
                    for ed in vd.get("encounter_details", []):
                        m_slug = ed["method"]["name"]
                        m_display = clean_method(m_slug)
                        chance = ed["chance"]
                        min_lvl = ed["min_level"]
                        max_lvl = ed["max_level"]
                        
                        # Conditions (GBA slot, swarm, radar, time etc)
                        conditions = []
                        for cond in ed.get("condition_values", []):
                            cname = cond["name"]
                            
                            # Skip off conditions
                            if cname.endswith("-off") or cname.endswith("-no") or cname == "slot2-none":
                                continue
                                
                            # Custom overrides
                            if cname == "swarm-yes":
                                conditions.append("Swarm")
                                continue
                            if cname == "radar-on" or cname == "radar":
                                conditions.append("Poké Radar")
                                continue
                                
                            if cname.endswith("-on"):
                                cname = cname[:-3]
                            if cname.endswith("-yes"):
                                cname = cname[:-4]
                                
                            # Clean GBA slot conditions
                            if cname.startswith("slot2-"):
                                game_part = cname.replace("slot2-", "").lower()
                                if game_part == "firered":
                                    conditions.append("GBA FireRed")
                                elif game_part == "leafgreen":
                                    conditions.append("GBA LeafGreen")
                                else:
                                    conditions.append(f"GBA {game_part.title()}")
                            else:
                                conditions.append(cname.replace("-", " ").title())
                                
                        game_encounters[vname].append({
                            "location": loc_display,
                            "method": m_display,
                            "chance": chance,
                            "levels": f"{min_lvl}-{max_lvl}" if min_lvl != max_lvl else str(min_lvl),
                            "conditions": conditions
                        })
                        
        # Group and deduplicate encounters per game for clean presentation
        formatted_locations = {g: [] for g in GEN4_GAMES}
        for g in GEN4_GAMES:
            raw_locs = game_encounters[g]
            # Group by location + method
            grouped = {}
            for rl in raw_locs:
                key = (rl["location"], rl["method"])
                if key not in grouped:
                    grouped[key] = {
                        "location": rl["location"],
                        "method": rl["method"],
                        "chances": [],
                        "min_level": 999,
                        "max_level": 0,
                        "conditions": set()
                    }
                grouped[key]["chances"].append(rl["chance"])
                # Extract level range
                levels = [int(x) for x in rl["levels"].split("-")]
                grouped[key]["min_level"] = min(grouped[key]["min_level"], min(levels))
                grouped[key]["max_level"] = max(grouped[key]["max_level"], max(levels))
                for c in rl["conditions"]:
                    grouped[key]["conditions"].add(c)
                    
            for key, val in grouped.items():
                total_chance = sum(val["chances"])
                total_chance = min(total_chance, 100)
                
                lvl_str = f"{val['min_level']}-{val['max_level']}" if val["min_level"] != val["max_level"] else str(val["min_level"])
                cond_list = list(val["conditions"])
                
                formatted_locations[g].append({
                    "location": val["location"],
                    "method": val["method"],
                    "chance": total_chance,
                    "levels": lvl_str,
                    "conditions": cond_list
                })
                
            # Sort locations alphabetically, then by chance descending
            formatted_locations[g].sort(key=lambda x: (x["location"], -x["chance"]))
            
        # Override Giratina locations
        if slug_name == "giratina":
            formatted_locations["diamond"] = [{
                "location": "Turnback Cave",
                "method": "Only One / Static",
                "chance": 100,
                "levels": "70",
                "conditions": []
            }]
            formatted_locations["pearl"] = [{
                "location": "Turnback Cave",
                "method": "Only One / Static",
                "chance": 100,
                "levels": "70",
                "conditions": []
            }]
            formatted_locations["platinum"] = [{
                "location": "Distortion World",
                "method": "Only One / Static",
                "chance": 100,
                "levels": "47",
                "conditions": []
            }]
            formatted_locations["heartgold"] = [{
                "location": "Sinjoh Ruins",
                "method": "Only One / Static",
                "chance": 100,
                "levels": "1",
                "conditions": ["Other Event Arceus In Party"]
            }]
            formatted_locations["soulsilver"] = [{
                "location": "Sinjoh Ruins",
                "method": "Only One / Static",
                "chance": 100,
                "levels": "1",
                "conditions": ["Other Event Arceus In Party"]
            }]
            
        # Pal Park Encounters
        pal_park = []
        for ppe in spec_data.get("pal_park_encounters", []):
            pal_park.append({
                "area": clean_name(ppe["area"]["name"]),
                "base_score": ppe["base_score"],
                "rate": ppe["rate"]
            })
            
        record = {
            "id": sid,
            "slug": slug_name,
            "name": display_name,
            "types": types,
            "sprite": sprite_url,
            "pokedex_numbers": pokedex_numbers,
            "is_baby": spec_data.get("is_baby", False),
            "is_legendary": spec_data.get("is_legendary", False),
            "is_mythical": spec_data.get("is_mythical", False),
            "generation": spec_data["generation"]["name"],
            "evolves_from": clean_name(evo["evolves_from"]) if evo["evolves_from"] else None,
            "evolves_from_slug": evo["evolves_from"],
            "trigger_text": evo["trigger_text"],
            "locations": formatted_locations,
            "pal_park": pal_park,
            "obtain_methods": {}
        }
        
        pokemon_dict[slug_name] = record
        compiled_pokedex.append(record)

    # Step 5: Compute initial obtain methods recursively
    print("Step 5: Computing obtain methods...")
    
    def is_catchable(slug, game):
        rec = pokemon_dict.get(slug)
        if not rec:
            return False
        return len(rec["locations"][game]) > 0

    def has_catchable_descendant(slug, game, visited=None):
        if visited is None:
            visited = set()
        if slug in visited:
            return None
        visited.add(slug)
        
        evo = evolutions_map.get(slug)
        if not evo:
            return None
            
        for child in evo["children"]:
            if is_catchable(child, game):
                return child
            res = has_catchable_descendant(child, game, visited)
            if res:
                return res
        return None

    # Compute methods for all pokemon and all games
    for record in compiled_pokedex:
        slug = record["slug"]
        record["obtain_methods"] = {}
        
        for g in GEN4_GAMES:
            methods = []
            
            # 1. Check native catchable locations
            if is_catchable(slug, g):
                has_gift_egg = False
                has_gift = False
                has_only_one = False
                has_wild = False
                
                for l in record["locations"][g]:
                    m = l["method"].lower()
                    if "gift egg" in m or "gift-egg" in m:
                        has_gift_egg = True
                    elif "gift" in m:
                        has_gift = True
                    elif "only one" in m or "only-one" in m:
                        has_only_one = True
                    else:
                        has_wild = True
                        
                if has_gift_egg:
                    methods.append({"type": "gift-egg", "description": "Gift Egg"})
                if has_gift:
                    methods.append({"type": "gift", "description": "Gift"})
                if has_only_one:
                    methods.append({"type": "only-one", "description": "Only One / Static"})
                if has_wild:
                    methods.append({"type": "wild", "description": "Wild Encounter"})
            
            # 2. Check if it's an evolution
            if record["evolves_from_slug"]:
                methods.append({"type": "evolution", "description": "Evolution"})
            
            # 3. Check if it's breeding only
            if not is_catchable(slug, g) and not record["evolves_from_slug"]:
                child_slug = has_catchable_descendant(slug, g)
                if child_slug:
                    methods.append({"type": "breeding", "description": "Breeding"})
            
            # Explicit override for Lucario, Togetic, and Togekiss to always be Evolution
            if slug in ["lucario", "togetic", "togekiss"]:
                methods = [{"type": "evolution", "description": "Evolution"}]
                
            # 4. Check if it's a mythical (event)
            if not methods and (slug in MYTHICALS or record["is_mythical"]):
                methods.append({"type": "event", "description": "Event"})
                
            # 5. Otherwise it's trade / transfer
            if not methods:
                methods.append({"type": "transfer-only", "description": "Trade / Transfer"})
                
            # Deduplicate methods
            seen_types = set()
            deduped_methods = []
            for m in methods:
                if m["type"] not in seen_types:
                    seen_types.add(m["type"])
                    deduped_methods.append(m)
                    
            record["obtain_methods"][g] = deduped_methods

    # Step 6: Refine location and details with Breeding, Pal Park, and Trade/Transfer details
    print("Step 6: Populating Breeding, Pal Park, and Trade/Transfer details...")
    
    for record in compiled_pokedex:
        slug = record["slug"]
        gen_name = record["generation"]
        
        for g in GEN4_GAMES:
            methods = record["obtain_methods"][g]
            
            # A. If method is Breeding, add a breeding location entry
            if any(m["type"] == "breeding" for m in methods):
                child_slug = has_catchable_descendant(slug, g)
                child_name = pokemon_dict[child_slug]["name"]
                record["locations"][g] = [{
                    "location": f"Breed {child_name} to obtain {record['name']}.",
                    "method": "Breeding",
                    "chance": 100,
                    "levels": "—",
                    "conditions": []
                }]
                continue
                
            # B. If method is Trade / Transfer
            if any(m["type"] == "transfer-only" for m in methods):
                record["locations"][g] = []
                
                # Check trade games first
                trade_games = []
                for og in GEN4_GAMES:
                    if og == g:
                        continue
                    og_record = pokemon_dict.get(slug)
                    if og_record:
                        og_methods = og_record["obtain_methods"][og]
                        # If it is obtainable natively in the other game (wild, gift, static, gift-egg, or breeding)
                        og_obtainable = any(om["type"] not in ["transfer-only", "event"] for om in og_methods)
                        if og_obtainable:
                            trade_games.append(og)
                            
                if trade_games:
                    games_display = [clean_name(tg) for tg in trade_games]
                    if len(games_display) == 1:
                        desc = f"Trade from {games_display[0]}"
                    else:
                        desc = f"Trade from " + " or ".join(games_display)
                    record["locations"][g].append({
                        "location": desc,
                        "method": "Trade / Transfer",
                        "chance": 100,
                        "levels": "—",
                        "conditions": []
                    })
                    
                # Also check Pal Park (skip for Gen 4 exclusives)
                if record["pal_park"] and gen_name != "generation-iv":
                    if gen_name in ["generation-i", "generation-ii"]:
                        gba_games = "FireRed or LeafGreen"
                    elif gen_name == "generation-iii":
                        gba_games = "Ruby, Sapphire, or Emerald"
                    else:
                        gba_games = "Gen III GBA game"
                        
                    for ppe in record["pal_park"]:
                        record["locations"][g].append({
                            "location": f"Pal Park: {ppe['area']} (Score: {ppe['base_score']}, Rate: {ppe['rate']}%) - Transfer from {gba_games}",
                            "method": "Trade / Transfer",
                            "chance": 100,
                            "levels": "—",
                            "conditions": []
                        })
                        
                # If neither trade games nor Pal Park exists:
                if not record["locations"][g]:
                    if gen_name in ["generation-i", "generation-ii"]:
                        desc = "Transfer from FireRed or LeafGreen"
                    elif gen_name == "generation-iii":
                        desc = "Transfer from Ruby, Sapphire, or Emerald"
                    else:
                        desc = "Trade / Transfer"
                    record["locations"][g].append({
                        "location": desc,
                        "method": "Trade / Transfer",
                        "chance": 100,
                        "levels": "—",
                        "conditions": []
                    })
                    
            # C. Overrides for Lucario, Togetic, Togekiss Pal Park details
            if slug in ["lucario", "togetic", "togekiss"] and record["pal_park"]:
                if gen_name in ["generation-i", "generation-ii"]:
                    gba_games = "FireRed or LeafGreen"
                elif gen_name == "generation-iii":
                    gba_games = "Ruby, Sapphire, or Emerald"
                else:
                    gba_games = "Gen III GBA game"
                    
                if not record["locations"][g]:
                    record["locations"][g] = []
                for ppe in record["pal_park"]:
                    exists = any(f"Pal Park: {ppe['area']}" in loc["location"] for loc in record["locations"][g])
                    if not exists:
                        record["locations"][g].append({
                            "location": f"Pal Park: {ppe['area']} (Score: {ppe['base_score']}, Rate: {ppe['rate']}%) - Transfer from {gba_games}",
                            "method": "Trade / Transfer",
                            "chance": 100,
                            "levels": "—",
                            "conditions": []
                        })

    # Write out compiled pokedex JSON
    out_path = os.path.join("data", "pokedex_gen4.json")
    os.makedirs("data", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compiled_pokedex, f, indent=2)
        
    print(f"Done! Saved compiled pokedex to {out_path} ({len(compiled_pokedex)} entries).")

if __name__ == "__main__":
    main()
