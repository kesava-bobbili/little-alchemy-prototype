// app.js - Little Alchemy-like Game Logic

// 1. Initial State & Setup
let gameMode = "daily"; // "daily", "practice", "sandbox"
let unlockedElements = new Set(["air", "earth", "fire", "water"]);
let activePuzzle = null;
let currentTargetId = null;
let workspaceElements = [];
let nextElementId = 1;

const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://127.0.0.1:8000" : "https://little-alchemy-prototype-api.onrender.com";
let sessionToken = "";

function getFormattedDate(d) {
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}${month}${year}`;
}

async function initPuzzleAPI(method, value = null, title = "Puzzle") {
  try {
    const response = await fetch(`${API_BASE_URL}/api/alchemist/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ method, value })
    });
    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }
    const data = await response.json();
    sessionToken = data.session_token;
    currentTargetId = data.target_id;
    activePuzzle = {
      title: title,
      targetId: data.target_id,
      startingElements: data.starting_elements,
      targetName: data.target_name,
      targetEmoji: data.target_emoji,
      targetLevel: data.target_level,
      targetCost: data.target_cost
    };
    unlockedElements = new Set(data.starting_elements);
    saveGameState();
    document.getElementById("target-display-name").textContent = activePuzzle.targetName;
    document.getElementById("target-display-emoji").textContent = activePuzzle.targetEmoji;
    document.getElementById("target-display-level").textContent = `Level: ${activePuzzle.targetLevel}`;
    document.getElementById("target-display-steps").textContent = `Shortest steps: ${activePuzzle.targetCost}`;
    renderInventory();
    spawnStartingElements();
  } catch (error) {
    console.warn("Backend API unreachable. Falling back to local client-side logic.", error);
    initPuzzleLocal(method, value, title);
  }
}

function generatePuzzleLocal(targetId, title) {
  const puzzle = GRAPH_DATA.puzzles[targetId];
  if (!puzzle) return;
  
  sessionToken = ""; // Clear token for local mode
  currentTargetId = targetId;
  activePuzzle = {
    title: title,
    targetId: targetId,
    startingElements: puzzle.startingElements,
    targetName: puzzle.targetName,
    targetEmoji: puzzle.targetEmoji,
    targetLevel: puzzle.targetLevel,
    targetCost: puzzle.targetCost
  };
  
  unlockedElements = new Set(puzzle.startingElements);
  saveGameState();
  
  document.getElementById("target-display-name").textContent = activePuzzle.targetName;
  document.getElementById("target-display-emoji").textContent = activePuzzle.targetEmoji;
  document.getElementById("target-display-level").textContent = `Level: ${activePuzzle.targetLevel}`;
  document.getElementById("target-display-steps").textContent = `Shortest steps: ${activePuzzle.targetCost}`;
  
  renderInventory();
  spawnStartingElements();
}

function initPuzzleLocal(method, value = null, title = "Puzzle") {
  const eligible = Object.keys(GRAPH_DATA.puzzles);
  if (eligible.length === 0) return;
  
  let targetId = "steam";
  if (method === "date") {
    let day = 1, month = 0, year = 2026;
    if (value && value.length === 8) {
      day = parseInt(value.slice(0, 2));
      month = parseInt(value.slice(2, 4)) - 1;
      year = parseInt(value.slice(4, 8));
    }
    const idx = (year * 367 + month * 31 + day) % eligible.length;
    targetId = eligible[idx];
  } else if (method === "target") {
    targetId = value || "steam";
  } else {
    const randomIdx = Math.floor(Math.random() * eligible.length);
    targetId = eligible[randomIdx];
  }
  
  generatePuzzleLocal(targetId, title);
}

// Elements lookup maps
let elementsMap = {};
let recipeMap = {};

// 2. Initialize Game Data
function initGame() {
  // Build fast maps
  elementsMap = {};
  GRAPH_DATA.elements.forEach(elem => {
    elementsMap[elem.id] = elem;
  });
  
  recipeMap = {};
  GRAPH_DATA.recipes.forEach(r => {
    const key = [r.input_a, r.input_b].sort().join("+");
    if (!recipeMap[key]) {
      recipeMap[key] = [];
    }
    recipeMap[key].push(r.output);
  });
  
  // Load saved state
  loadGameState();
  
  // Setup UI event listeners
  setupEventListeners();
  
  // Select active mode
  switchMode(gameMode);
}

// 3. Game Mode Control
function switchMode(mode) {
  gameMode = mode;
  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  
  // Reset Canvas Workspace
  clearWorkspace();
  
  const puzzlePanel = document.getElementById("puzzle-panel");
  const practiceSelector = document.getElementById("practice-selector-container");
  
  if (mode === "daily") {
    puzzlePanel.style.display = "block";
    practiceSelector.style.display = "none";
    setupDailyChallenge();
  } else if (mode === "practice") {
    puzzlePanel.style.display = "block";
    practiceSelector.style.display = "block";
    populatePracticeSelector();
    setupPracticeChallenge();
  } else if (mode === "sandbox") {
    puzzlePanel.style.display = "none";
    practiceSelector.style.display = "none";
    // Sandbox starts with base 4 primitives
    unlockedElements = new Set(["air", "earth", "fire", "water"]);
    saveGameState();
    renderInventory();
    spawnSandboxStartingElements();
  }
}

// 4. Daily Puzzle Generator
function setupDailyChallenge() {
  const today = new Date();
  const dateStr = getFormattedDate(today);
  initPuzzleAPI("date", dateStr, "Daily Challenge");
}

function populatePracticeSelector() {
  const select = document.getElementById("practice-target-select");
  if (select.children.length > 1) return; // Already populated
  
  const eligible = Object.keys(GRAPH_DATA.puzzles)
    .map(id => elementsMap[id])
    .filter(Boolean)
    .sort((a, b) => a.name.localeCompare(b.name));
    
  eligible.forEach(elem => {
    const opt = document.createElement("option");
    opt.value = elem.id;
    opt.textContent = `${elem.name} (Lvl ${elem.level})`;
    select.appendChild(opt);
  });
}

function populateCatalog() {
  const container = document.getElementById("catalog-list");
  if (container.children.length > 0) return; // Only populate once
  
  const sorted = GRAPH_DATA.elements
    .filter(elem => elem.id !== "deity" && elem.id !== "monster")
    .sort((a, b) => a.name.localeCompare(b.name));
    
  sorted.forEach(elem => {
    const item = document.createElement("div");
    item.className = "catalog-item";
    item.style.display = "flex";
    item.style.alignItems = "center";
    item.style.gap = "8px";
    item.style.padding = "8px";
    item.style.borderRadius = "8px";
    item.style.background = "rgba(255,255,255,0.05)";
    item.style.border = "1px solid var(--panel-border)";
    
    item.innerHTML = `
      <span style="font-size: 1.4rem;">${elem.emoji}</span>
      <div>
        <div class="catalog-name" style="font-weight: 600; color: #fff; font-size: 0.9rem;">${elem.name}</div>
        <div style="font-size: 0.72rem; color: var(--text-muted);">Level ${elem.level !== null ? elem.level : 0}</div>
      </div>
    `;
    
    container.appendChild(item);
  });
}

function setupPracticeChallenge() {
  const select = document.getElementById("practice-target-select");
  const targetId = select.value || "steam";
  initPuzzleAPI("target", targetId, "Practice Mode");
}

function spawnStartingElements() {
  const canvas = document.getElementById("canvas-workspace");
  const rect = canvas.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  
  // Spawn in a cross layout
  const offsets = [
    { x: -100, y: -50 },
    { x: 100, y: -50 },
    { x: -100, y: 80 },
    { x: 100, y: 80 }
  ];
  
  activePuzzle.startingElements.forEach((id, idx) => {
    const elem = elementsMap[id];
    const offset = offsets[idx];
    createElementCard(id, centerX + offset.x, centerY + offset.y);
  });
}

function spawnSandboxStartingElements() {
  const canvas = document.getElementById("canvas-workspace");
  const rect = canvas.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  
  const offsets = [
    { x: -100, y: -50 },
    { x: 100, y: -50 },
    { x: -100, y: 80 },
    { x: 100, y: 80 }
  ];
  
  const basePrimitives = ["air", "earth", "fire", "water"];
  basePrimitives.forEach((id, idx) => {
    const offset = offsets[idx];
    createElementCard(id, centerX + offset.x, centerY + offset.y);
  });
}

// 6. Canvas Drag & Drop Implementation (Phase 4 UI)
function createElementCard(id, x, y) {
  const elem = elementsMap[id];
  if (!elem) return;
  
  const canvas = document.getElementById("canvas-workspace");
  const card = document.createElement("div");
  card.className = "element-card pop-in";
  card.dataset.id = id;
  card.dataset.uid = nextElementId++;
  
  // Add category styling classes
  const group = getElementColorGroup(id);
  card.classList.add(group);
  
  card.innerHTML = `<span class="card-emoji">${elem.emoji}</span> <span class="card-name">${elem.name}</span>`;
  
  // Position absolutely inside canvas
  card.style.left = `${x}px`;
  card.style.top = `${y}px`;
  
  canvas.appendChild(card);
  
  // Store reference
  const item = {
    uid: card.dataset.uid,
    id: id,
    element: card,
    x: x,
    y: y
  };
  workspaceElements.push(item);
  
  makeDraggable(item);
}

function getElementColorGroup(id) {
  // Return matching css glow style group
  const hot = ["fire", "lava", "heat", "sun", "explosion", "plasma", "lightning", "energy"];
  const wet = ["water", "sea", "ocean", "rain", "puddle", "pond", "lake", "steam", "geyser", "cloud", "mist", "fog", "acid rain"];
  const organic = ["plant", "tree", "forest", "wood", "life", "animal", "grass", "soil", "mud", "algae", "reed"];
  
  if (hot.some(h => id.includes(h))) return "glow-hot";
  if (wet.some(w => id.includes(w))) return "glow-wet";
  if (organic.some(o => id.includes(o))) return "glow-organic";
  return "glow-default";
}

function makeDraggable(item) {
  const card = item.element;
  let startX, startY;
  
  card.addEventListener("mousedown", dragStart);
  card.addEventListener("touchstart", dragStart, { passive: false });
  
  function dragStart(e) {
    e.preventDefault();
    
    // Bring card to front
    card.parentElement.appendChild(card);
    
    const clientX = e.type === "touchstart" ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === "touchstart" ? e.touches[0].clientY : e.clientY;
    
    startX = clientX - item.x;
    startY = clientY - item.y;
    
    document.addEventListener("mousemove", dragMove);
    document.addEventListener("mouseup", dragEnd);
    document.addEventListener("touchmove", dragMove, { passive: false });
    document.addEventListener("touchend", dragEnd);
  }
  
  function dragMove(e) {
    const clientX = e.type === "touchmove" ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === "touchmove" ? e.touches[0].clientY : e.clientY;
    
    const canvas = document.getElementById("canvas-workspace");
    const rect = canvas.getBoundingClientRect();
    
    let x = clientX - startX;
    let y = clientY - startY;
    
    // Boundary check inside canvas
    const cardWidth = card.offsetWidth;
    const cardHeight = card.offsetHeight;
    
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x > rect.width - cardWidth) x = rect.width - cardWidth;
    if (y > rect.height - cardHeight) y = rect.height - cardHeight;
    
    item.x = x;
    item.y = y;
    
    card.style.left = `${x}px`;
    card.style.top = `${y}px`;
  }
  
  function dragEnd() {
    document.removeEventListener("mousemove", dragMove);
    document.removeEventListener("mouseup", dragEnd);
    document.removeEventListener("touchmove", dragMove);
    document.removeEventListener("touchend", dragEnd);
    
    // Check collision with other workspace elements
    checkCollisions(item);
  }
}

// 7. Combination & Collision Check Logic
function checkCollisions(draggedItem) {
  const cardA = draggedItem.element;
  const rectA = cardA.getBoundingClientRect();
  
  for (let otherItem of workspaceElements) {
    if (otherItem.uid === draggedItem.uid) continue;
    
    const cardB = otherItem.element;
    const rectB = cardB.getBoundingClientRect();
    
    // Intersection check
    const isIntersecting = !(rectA.right < rectB.left || 
                             rectA.left > rectB.right || 
                             rectA.bottom < rectB.top || 
                             rectA.top > rectB.bottom);
                             
    if (isIntersecting) {
      // Attract/combine
      combineElements(draggedItem, otherItem);
      return;
    }
  }
}

function combineElements(itemA, itemB) {
  const idA = itemA.id;
  const idB = itemB.id;
  
  // Recipe lookup (inputs must be sorted alphabetically)
  const key = [idA, idB].sort().join("+");
  const outputs = recipeMap[key];
  
  const canvas = document.getElementById("canvas-workspace");
  
  if (outputs && outputs.length > 0) {
    // Collision center coordinates
    const centerX = (itemA.x + itemB.x) / 2;
    const centerY = (itemA.y + itemB.y) / 2;
    
    // Create combine smoke/spark puff
    createCombineEffect(centerX, centerY);
    
    // Delete parent cards from DOM & memory
    itemA.element.remove();
    itemB.element.remove();
    
    workspaceElements = workspaceElements.filter(item => item.uid !== itemA.uid && item.uid !== itemB.uid);
    
    // Spawn output elements (slightly offset if multiple to make them readable)
    outputs.forEach((outputId, idx) => {
      const offsetX = (idx - (outputs.length - 1) / 2) * 40;
      createElementCard(outputId, centerX + offsetX, centerY);
      
      // Register discovery
      if (!unlockedElements.has(outputId)) {
        unlockedElements.add(outputId);
        saveGameState();
        renderInventory();
        triggerDiscoveryNotification(outputId);
      }
      
      // Check if target is achieved
      checkVictory(outputId);
    });
  } else {
    // Invalid combo, bounce cards slightly apart
    bounceApart(itemA, itemB);
  }
}

function bounceApart(itemA, itemB) {
  // Shift itemA slightly opposite to itemB
  const dx = itemA.x - itemB.x;
  const dy = itemA.y - itemB.y;
  const dist = Math.sqrt(dx*dx + dy*dy) || 1;
  
  const shiftX = (dx / dist) * 20;
  const shiftY = (dy / dist) * 20;
  
  itemA.x += shiftX;
  itemA.y += shiftY;
  
  itemA.element.style.left = `${itemA.x}px`;
  itemA.element.style.top = `${itemA.y}px`;
  
  itemA.element.classList.add("shake");
  setTimeout(() => {
    itemA.element.classList.remove("shake");
  }, 300);
}

// 8. Visual Animations & Effects
function createCombineEffect(x, y) {
  const canvas = document.getElementById("canvas-workspace");
  const puff = document.createElement("div");
  puff.className = "puff-effect";
  puff.style.left = `${x + 30}px`;
  puff.style.top = `${y + 15}px`;
  canvas.appendChild(puff);
  
  setTimeout(() => {
    puff.remove();
  }, 400);
}

function triggerDiscoveryNotification(id) {
  const name = elementsMap[id].name;
  const emoji = elementsMap[id].emoji;
  
  const notifier = document.getElementById("discovery-notifier");
  notifier.innerHTML = `🌟 New Element Discovered: <strong>${emoji} ${name}</strong>!`;
  notifier.classList.add("show");
  
  setTimeout(() => {
    notifier.classList.remove("show");
  }, 3000);
}

function triggerSuccess() {
  setTimeout(() => {
    const modal = document.getElementById("success-modal");
    document.getElementById("modal-target-name").textContent = activePuzzle.targetName;
    document.getElementById("modal-target-emoji").textContent = activePuzzle.targetEmoji;
    modal.style.display = "flex";
  }, 600);
}

async function checkVictory(outputId) {
  if (gameMode === "sandbox" || outputId !== currentTargetId) return;
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/alchemist/check`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        session_token: sessionToken,
        crafted_element_id: outputId
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.solved) {
        triggerSuccess();
      }
    } else {
      // Local fallback
      triggerSuccess();
    }
  } catch (error) {
    console.error("Verification error:", error);
    triggerSuccess(); // Local fallback
  }
}

// 9. Side Panel Inventory Rendering
function renderInventory() {
  const container = document.getElementById("inventory-list");
  container.innerHTML = "";
  
  const showAll = document.getElementById("show-all-toggle")?.checked || false;
  let itemsToRender = [];
  
  if (showAll) {
    // Render all elements, mark locked ones
    itemsToRender = GRAPH_DATA.elements
      .filter(elem => elem.id !== "deity" && elem.id !== "monster")
      .sort((a, b) => a.name.localeCompare(b.name));
  } else {
    // Render only unlocked elements
    itemsToRender = Array.from(unlockedElements)
      .map(id => elementsMap[id])
      .filter(Boolean)
      .sort((a, b) => a.name.localeCompare(b.name));
  }
    
  itemsToRender.forEach(elem => {
    const isLocked = showAll && !unlockedElements.has(elem.id);
    const item = document.createElement("div");
    item.className = "inventory-item";
    item.draggable = !isLocked;
    item.dataset.id = elem.id;
    
    if (isLocked) {
      item.classList.add("locked");
    } else {
      // Color glow class
      const group = getElementColorGroup(elem.id);
      item.classList.add(group);
    }
    
    item.innerHTML = `<span class="item-emoji">${elem.emoji}</span> <span class="item-name">${elem.name}</span>`;
    
    if (!isLocked) {
      // Spawn element onto canvas when clicked inside inventory sidebar
      item.addEventListener("click", () => {
        const canvas = document.getElementById("canvas-workspace");
        const rect = canvas.getBoundingClientRect();
        
        // Spawn at random offset near center to avoid perfect stack overlaps
        const rx = (Math.random() - 0.5) * 80;
        const ry = (Math.random() - 0.5) * 80;
        
        createElementCard(elem.id, rect.width / 2 + rx - 50, rect.height / 2 + ry - 20);
      });
      
      // HTML5 Drag Start listener
      item.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", elem.id);
      });
    }
    
    container.appendChild(item);
  });
}

// 9.5 Recipe Solution Path Solver
function findSolutionPath(targetId, startingSet) {
  let currentSet = new Set(startingSet);
  let parentRecipe = {}; // maps elementId -> { input_a, input_b }
  let discoveredInRound = true;
  
  while (discoveredInRound && !currentSet.has(targetId)) {
    discoveredInRound = false;
    let currentList = Array.from(currentSet);
    let newDiscoveries = {};
    
    for (let i = 0; i < currentList.length; i++) {
      for (let j = i; j < currentList.length; j++) {
        const key = [currentList[i], currentList[j]].sort().join("+");
        const output = recipeMap[key];
        if (output && !currentSet.has(output) && !newDiscoveries[output]) {
          newDiscoveries[output] = { input_a: currentList[i], input_b: currentList[j] };
          discoveredInRound = true;
        }
      }
    }
    
    for (let output in newDiscoveries) {
      currentSet.add(output);
      parentRecipe[output] = newDiscoveries[output];
    }
  }
  
  if (!currentSet.has(targetId)) return null;
  
  let steps = [];
  function trace(id) {
    if (startingSet.includes(id)) return;
    const parent = parentRecipe[id];
    if (!parent) return;
    
    trace(parent.input_a);
    trace(parent.input_b);
    
    const stepStr = `<div class="recipe-step-line"><span>${elementsMap[parent.input_a].emoji} ${elementsMap[parent.input_a].name}</span> + <span>${elementsMap[parent.input_b].emoji} ${elementsMap[parent.input_b].name}</span> ➔ <strong>${elementsMap[id].emoji} ${elementsMap[id].name}</strong></div>`;
    
    if (!steps.includes(stepStr)) {
      steps.push(stepStr);
    }
  }
  
  trace(targetId);
  return steps;
}

// 10. Local Storage Persistence
function saveGameState() {
  const state = {
    gameMode: gameMode,
    unlockedElements: Array.from(unlockedElements),
    currentTargetId: currentTargetId,
    activePuzzle: activePuzzle,
    sessionToken: sessionToken
  };
  localStorage.setItem("alchemix_game_state", JSON.stringify(state));
}

function loadGameState() {
  const saved = localStorage.getItem("alchemix_game_state");
  if (!saved) return;
  
  try {
    const state = JSON.parse(saved);
    gameMode = state.gameMode || "daily";
    currentTargetId = state.currentTargetId;
    activePuzzle = state.activePuzzle;
    sessionToken = state.sessionToken || "";
    
    if (state.unlockedElements) {
      unlockedElements = new Set(state.unlockedElements);
    }
  } catch (e) {
    console.error("Error loading saved game state", e);
  }
}

// 11. Helper Event Listeners
function setupEventListeners() {
  // HTML5 Drag & Drop listeners on Canvas Playground
  const canvas = document.getElementById("canvas-workspace");
  canvas.addEventListener("dragover", (e) => {
    e.preventDefault();
  });
  canvas.addEventListener("drop", (e) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain");
    if (!id || !elementsMap[id]) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left - 50;
    const y = e.clientY - rect.top - 20;
    
    createElementCard(id, x, y);
  });

  // Mode selection buttons
  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      switchMode(e.currentTarget.dataset.mode);
    });
  });
  
  // Practice target selector change
  document.getElementById("practice-target-select").addEventListener("change", () => {
    setupPracticeChallenge();
  });
  
  // Show all toggle change
  document.getElementById("show-all-toggle").addEventListener("change", () => {
    renderInventory();
  });
  
  // Reset and Clear Workspace buttons
  document.getElementById("clear-workspace-btn").addEventListener("click", clearWorkspace);
  document.getElementById("reset-puzzle-btn").addEventListener("click", () => {
    clearWorkspace();
    if (activePuzzle) {
      spawnStartingElements();
      unlockedElements = new Set(activePuzzle.startingElements);
      saveGameState();
      renderInventory();
    }
  });
  
  // Search sidebar inventory filter
  document.getElementById("inventory-search").addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase().trim();
    document.querySelectorAll(".inventory-item").forEach(item => {
      const name = item.querySelector(".item-name").textContent.toLowerCase();
      item.style.display = name.includes(query) ? "flex" : "none";
    });
  });
  
  // Close success modal
  document.getElementById("close-modal-btn").addEventListener("click", () => {
    document.getElementById("success-modal").style.display = "none";
  });
  
  // Show Solution / Recipe Modal
  document.getElementById("show-recipe-btn").addEventListener("click", async () => {
    if (!currentTargetId || !activePuzzle) return;
    const container = document.getElementById("recipe-steps-list");
    document.getElementById("recipe-modal").style.display = "flex";
    
    if (!sessionToken) {
      const steps = findSolutionPathLocal(currentTargetId, activePuzzle.startingElements);
      if (steps && steps.length > 0) {
        container.innerHTML = steps.join("");
      } else {
        container.innerHTML = "<div style='color: var(--text-muted);'>No solution path required (target already in starting set!).</div>";
      }
      return;
    }
    
    container.innerHTML = "<div style='color: var(--text-muted);'>Loading solution path from backend API...</div>";
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/alchemist/answer?token=${sessionToken}`);
      if (!response.ok) throw new Error("Failed to load answer");
      const data = await response.json();
      
      if (data.steps && data.steps.length > 0) {
        const stepHTMLs = data.steps.map(step => {
          return `<div class="recipe-step-line"><span>${step.input_a.emoji} ${step.input_a.name}</span> + <span>${step.input_b.emoji} ${step.input_b.name}</span> ➔ <strong>${step.output.emoji} ${step.output.name}</strong></div>`;
        });
        container.innerHTML = stepHTMLs.join("");
      } else {
        container.innerHTML = "<div style='color: var(--text-muted);'>No solution path required (target already in starting set!).</div>";
      }
    } catch (err) {
      console.warn("API answer load failed, using local solver:", err);
      const steps = findSolutionPathLocal(currentTargetId, activePuzzle.startingElements);
      if (steps && steps.length > 0) {
        container.innerHTML = steps.join("");
      } else {
        container.innerHTML = "<div style='color: var(--text-muted);'>No solution path required (target already in starting set!).</div>";
      }
    }
  });
  
  // Close Recipe Modal
  document.getElementById("close-recipe-btn").addEventListener("click", () => {
    document.getElementById("recipe-modal").style.display = "none";
  });
  
  // Open Catalog Modal
  document.getElementById("open-catalog-btn").addEventListener("click", () => {
    populateCatalog();
    document.getElementById("catalog-modal").style.display = "flex";
  });
  
  // Close Catalog Modal (X button)
  document.getElementById("close-catalog-x").addEventListener("click", () => {
    document.getElementById("catalog-modal").style.display = "none";
  });
  
  // Close Catalog Modal (Close button)
  document.getElementById("close-catalog-btn").addEventListener("click", () => {
    document.getElementById("catalog-modal").style.display = "none";
  });
  
  // Search Catalog Filter
  document.getElementById("catalog-search").addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase().trim();
    document.querySelectorAll(".catalog-item").forEach(item => {
      const name = item.querySelector(".catalog-name").textContent.toLowerCase();
      item.style.display = name.includes(query) ? "flex" : "none";
    });
  });
}

function clearWorkspace() {
  document.querySelectorAll("#canvas-workspace .element-card").forEach(c => c.remove());
  workspaceElements = [];
}

function findSolutionPathLocal(targetId, startingSet) {
  let currentSet = new Set(startingSet);
  let parentRecipe = {}; // maps elementId -> { input_a, input_b }
  let discoveredInRound = true;
  
  while (discoveredInRound && !currentSet.has(targetId)) {
    discoveredInRound = false;
    let currentList = Array.from(currentSet);
    let newDiscoveries = {};
    
    for (let i = 0; i < currentList.length; i++) {
      for (let j = i; j < currentList.length; j++) {
        const key = [currentList[i], currentList[j]].sort().join("+");
        const outputs = recipeMap[key];
        if (outputs) {
          outputs.forEach(output => {
            if (!currentSet.has(output) && !newDiscoveries[output]) {
              newDiscoveries[output] = { input_a: currentList[i], input_b: currentList[j] };
              discoveredInRound = true;
            }
          });
        }
      }
    }
    
    for (let output in newDiscoveries) {
      currentSet.add(output);
      parentRecipe[output] = newDiscoveries[output];
    }
  }
  
  if (!currentSet.has(targetId)) return null;
  
  let steps = [];
  function trace(id) {
    if (startingSet.includes(id)) return;
    const parent = parentRecipe[id];
    if (!parent) return;
    
    trace(parent.input_a);
    trace(parent.input_b);
    
    const stepStr = `<div class="recipe-step-line"><span>${elementsMap[parent.input_a].emoji} ${elementsMap[parent.input_a].name}</span> + <span>${elementsMap[parent.input_b].emoji} ${elementsMap[parent.input_b].name}</span> ➔ <strong>${elementsMap[id].emoji} ${elementsMap[id].name}</strong></div>`;
    
    if (!steps.includes(stepStr)) {
      steps.push(stepStr);
    }
  }
  
  trace(targetId);
  return steps;
}

// Start game loop when script is loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initGame);
} else {
  initGame();
}
