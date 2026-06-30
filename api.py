#!/usr/bin/env python3
import base64
import hmac
import os
import random
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Optional, Union, Literal
from fastapi import FastAPI, APIRouter, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Initialize FastAPI App
app = FastAPI(title="AlcheMix Game API", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class StartRequest(BaseModel):
    method: Literal["random", "seed", "date", "target"]
    value: Optional[str] = None

class StartResponse(BaseModel):
    seed: int
    session_token: str
    target_id: str
    target_name: str
    target_emoji: str
    target_level: int
    target_cost: int
    starting_elements: List[str]

class CheckRequest(BaseModel):
    session_token: str
    crafted_element_id: str

class CheckResponse(BaseModel):
    solved: bool
    target_id: str

class RecipeStep(BaseModel):
    input_a: dict
    input_b: dict
    output: dict

class AnswerResponse(BaseModel):
    target_id: str
    steps: List[RecipeStep]

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("ALCHEMIX_SECRET_KEY", "alchemix-dev-secret-key-12345").encode()
BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Data Loaders
# ---------------------------------------------------------------------------
elements_data = []
elements_map = {}
recipes_data = []
paths_cache = {}
eligible_keys = []

def load_game_data():
    global elements_data, elements_map, recipes_data, paths_cache, eligible_keys
    
    # Load Elements
    elem_path = BASE_DIR / "elements.json"
    if not elem_path.exists():
        raise RuntimeError("elements.json not found")
    with open(elem_path, "r", encoding="utf-8") as f:
        elements_data = json.load(f)["elements"]
    
    # Load Emojis (use pre-generated mapping if exists)
    emojis_path = BASE_DIR / "elements_emojis.json"
    emojis_map = {}
    if emojis_path.exists():
        with open(emojis_path, "r", encoding="utf-8") as f:
            emojis_map = json.load(f)
            
    for elem in elements_data:
        elem["emoji"] = emojis_map.get(elem["id"], elem.get("emoji", "🔮"))
        elements_map[elem["id"]] = elem
        
    # Load Recipes
    recipes_path = BASE_DIR / "recipes.json"
    if not recipes_path.exists():
        raise RuntimeError("recipes.json not found")
    with open(recipes_path, "r", encoding="utf-8") as f:
        recipes_data = json.load(f)["recipes"]
        
    # Load Paths
    paths_path = BASE_DIR / "paths_cache.json"
    if not paths_path.exists():
        raise RuntimeError("paths_cache.json not found")
    with open(paths_path, "r", encoding="utf-8") as f:
        paths_cache = json.load(f)
        
    # Build list of eligible puzzle elements (craftable items with levels > 0)
    eligible_keys = sorted([
        elem["id"] for elem in elements_data 
        if elem["level"] is not None and elem["level"] > 0 and elem["id"] in paths_cache
    ])

# Execute initial data load
load_game_data()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_date(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%d%m%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use DDMMYYYY.")

def _make_token(seed: int, target_id: str) -> str:
    """Create a signed token embedding the seed and targetId."""
    nonce = os.urandom(16).hex()
    msg = f"{seed}:{target_id}:{nonce}".encode()
    mac = hmac.new(SECRET_KEY, msg, "sha256").digest()
    return base64.urlsafe_b64encode(msg + mac).rstrip(b'=').decode()

def _validate_token(token: str) -> tuple[int, str]:
    """Verify signature and extract (seed, target_id)."""
    padding = '=' * (4 - len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(token + padding)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid session token.")
    if len(raw) <= 32:
        raise HTTPException(status_code=403, detail="Invalid session token.")
    
    msg, received_mac = raw[:-32], raw[-32:]
    expected_mac = hmac.new(SECRET_KEY, msg, "sha256").digest()
    
    if not hmac.compare_digest(expected_mac, received_mac):
        raise HTTPException(status_code=403, detail="Invalid or tampered session token.")
        
    try:
        parts = msg.decode().split(':')
        seed = int(parts[0])
        target_id = parts[1]
        return seed, target_id
    except (ValueError, IndexError, UnicodeDecodeError):
        raise HTTPException(status_code=403, detail="Invalid session token.")

def generate_starting_deck(target_id: str) -> list[str]:
    """Backward replacement puzzle solver algorithm."""
    path_info = paths_cache.get(target_id)
    if not path_info or not path_info.get("paths"):
        return ["air", "earth", "fire", "water"]
        
    path = path_info["paths"][0]
    queue = [{"id": target_id, "path": path}]
    
    while len(queue) < 4:
        expand_idx = -1
        max_cost = -1
        for i, node in enumerate(queue):
            if node["path"].get("recipe") is not None and node["path"].get("cost", 0) > max_cost:
                max_cost = node["path"]["cost"]
                expand_idx = i
                
        if expand_idx == -1:
            break
            
        node = queue.pop(expand_idx)
        recipe = node["path"]["recipe"]
        children = node["path"].get("children") or {}
        
        in_a, in_b = recipe[0], recipe[1]
        path_a = children.get(in_a) or {"cost": 0, "recipe": None, "children": None}
        path_b = children.get(in_b) or {"cost": 0, "recipe": None, "children": None}
        
        queue.append({"id": in_a, "path": path_a})
        queue.append({"id": in_b, "path": path_b})
        
    starting_ids = list(set([node["id"] for node in queue]))
    
    # Pad to 4 starting elements if needed
    primitives = ["air", "earth", "fire", "water"]
    for prim in primitives:
        if len(starting_ids) >= 4:
            break
        if prim not in starting_ids:
            starting_ids.append(prim)
            
    return starting_ids[:4]

def find_solution_path_py(target_id: str, starting_set: list) -> list:
    """Calculates the BFS recipe combination steps to reach the target."""
    recipe_map = {}
    for r in recipes_data:
        key = "+".join(sorted([r["input_a"], r["input_b"]]))
        recipe_map.setdefault(key, []).append(r["output"])
        
    current_set = set(starting_set)
    parent_recipe = {}
    discovered_in_round = True
    
    while discovered_in_round and target_id not in current_set:
        discovered_in_round = False
        current_list = list(current_set)
        new_discoveries = {}
        
        for i in range(len(current_list)):
            for j in range(i, len(current_list)):
                key = "+".join(sorted([current_list[i], current_list[j]]))
                outputs = recipe_map.get(key)
                if outputs:
                    for output in outputs:
                        if output not in current_set and output not in new_discoveries:
                            new_discoveries[output] = {
                                "input_a": current_list[i],
                                "input_b": current_list[j]
                            }
                            discovered_in_round = True
                            
        for output, parent in new_discoveries.items():
            current_set.add(output)
            parent_recipe[output] = parent
            
    if target_id not in current_set:
        return []
        
    steps = []
    seen_steps = set()
    
    def trace(node_id):
        if node_id in starting_set:
            return
        parent = parent_recipe.get(node_id)
        if not parent:
            return
            
        trace(parent["input_a"])
        trace(parent["input_b"])
        
        step_key = (parent["input_a"], parent["input_b"], node_id)
        if step_key not in seen_steps:
            seen_steps.add(step_key)
            a_elem = elements_map.get(parent["input_a"], {"name": parent["input_a"], "emoji": "🔮"})
            b_elem = elements_map.get(parent["input_b"], {"name": parent["input_b"], "emoji": "🔮"})
            out_elem = elements_map.get(node_id, {"name": node_id, "emoji": "🔮"})
            steps.append({
                "input_a": {"id": parent["input_a"], "name": a_elem["name"], "emoji": a_elem.get("emoji", "🔮")},
                "input_b": {"id": parent["input_b"], "name": b_elem["name"], "emoji": b_elem.get("emoji", "🔮")},
                "output": {"id": node_id, "name": out_elem["name"], "emoji": out_elem.get("emoji", "🔮")}
            })
            
    trace(target_id)
    return steps

# ---------------------------------------------------------------------------
# Router and endpoints
# ---------------------------------------------------------------------------
@app.post("/api/alchemist/start", response_model=StartResponse)
def start_game(data: StartRequest) -> StartResponse:
    method = data.method
    value = (data.value or "").strip()
    
    today = date.today()
    min_allowed_date = date(2026, 6, 14)
    max_allowed_date = today + timedelta(days=1)
    
    if not eligible_keys:
        raise HTTPException(status_code=500, detail="No puzzle elements loaded.")
        
    if method == "date":
        seed_date = _parse_date(value)
        if not (min_allowed_date <= seed_date <= max_allowed_date):
            raise HTTPException(status_code=400, detail="Date out of range.")
        seed = int(seed_date.strftime("%Y%m%d"))
        
        # Hash date to select element (Note: month - 1 matches Javascript's 0-indexed month)
        idx = (seed_date.year * 367 + (seed_date.month - 1) * 31 + seed_date.day) % len(eligible_keys)
        target_id = eligible_keys[idx]
        
    elif method == "random":
        seed = random.randint(100000, 999999)
        target_id = random.choice(eligible_keys)
        
    elif method == "seed":
        if not value.isdigit() or len(value) != 6:
            raise HTTPException(status_code=400, detail="Invalid seed. Must be 6 digits.")
        seed = int(value)
        rng = random.Random(seed)
        target_id = rng.choice(eligible_keys)
        
    elif method == "target":
        if value not in elements_map:
            raise HTTPException(status_code=400, detail="Target element not found.")
        target_id = value
        seed = random.randint(100000, 999999)
        
    else:
        raise HTTPException(status_code=400, detail="Invalid method type.")
        
    # Generate starting deck
    starting_deck = generate_starting_deck(target_id)
    
    elem = elements_map[target_id]
    path_info = paths_cache.get(target_id, {})
    cost = path_info.get("paths", [{}])[0].get("cost", 0) if path_info.get("paths") else 0
    
    session_token = _make_token(seed, target_id)
    
    return StartResponse(
        seed=seed,
        session_token=session_token,
        target_id=target_id,
        target_name=elem["name"],
        target_emoji=elem["emoji"],
        target_level=elem["level"],
        target_cost=cost,
        starting_elements=starting_deck
    )

@app.post("/api/alchemist/check", response_model=CheckResponse)
def check_game(data: CheckRequest) -> CheckResponse:
    # Validate token and match crafted item
    _, target_id = _validate_token(data.session_token)
    solved = (data.crafted_element_id.lower().strip() == target_id)
    return CheckResponse(solved=solved, target_id=target_id)

@app.get("/api/alchemist/answer", response_model=AnswerResponse)
def reveal_solution(
    token: str = Query(..., description="Session token returned from start endpoint")
) -> AnswerResponse:
    seed, target_id = _validate_token(token)
    starting_deck = generate_starting_deck(target_id)
    steps = find_solution_path_py(target_id, starting_deck)
    return AnswerResponse(target_id=target_id, steps=steps)
