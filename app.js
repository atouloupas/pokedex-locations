/**
 * Gen 4 Pokedex Locations - Frontend Controller
 */

// State Management
let pokedexData = [];
let filteredData = [];
let activeGame = "diamond";
let activePokedex = "national";
let searchQuery = "";
let selectedType = "all";
let selectedMethod = "all";
let selectedCondition = "all";
let currentPage = 1;
let pageSize = 50;
let sortBy = "dex-id";
let sortOrder = "asc";

// DOM Elements
const tableBody = document.getElementById("pokedex-table-body");
const searchInput = document.getElementById("search-input");
const searchClearBtn = document.getElementById("search-clear-btn");
const pokedexSelect = document.getElementById("pokedex-select");
const typeSelect = document.getElementById("type-select");
const methodSelect = document.getElementById("method-select");
const conditionSelect = document.getElementById("condition-select");
const gameSelectors = document.getElementById("game-selectors");
const statsCount = document.getElementById("stats-count");
const activeFiltersDesc = document.getElementById("active-filters-desc");
const prevPageBtn = document.getElementById("prev-page-btn");
const nextPageBtn = document.getElementById("next-page-btn");
const pageInfo = document.getElementById("page-info");
const pageSizeSelect = document.getElementById("page-size-select");
const tableHeaders = document.querySelectorAll("th.sortable");

// Modal Elements
const infoModal = document.getElementById("info-modal");
const infoModalTrigger = document.getElementById("info-modal-trigger");
const modalClose = document.getElementById("modal-close");

// Game names mapping for UI titles
const gameNames = {
  diamond: "Pokémon Diamond",
  pearl: "Pokémon Pearl",
  platinum: "Pokémon Platinum",
  heartgold: "Pokémon HeartGold",
  soulsilver: "Pokémon SoulSilver"
};

// Pokedex names mapping for titles
const pokedexNames = {
  national: "National Pokédex",
  "original-sinnoh": "Sinnoh Pokédex (D/P)",
  "extended-sinnoh": "Sinnoh Pokédex (Platinum)",
  "updated-johto": "Johto Pokédex (HG/SS)"
};

// Get Bulbapedia URL
function getBulbapediaUrl(name) {
  let cleanName = name
    .replace(" ♀", "♀")
    .replace(" ♂", "♂")
    .replace(" ", "_");
  return `https://bulbapedia.bulbagarden.net/wiki/${encodeURIComponent(cleanName)}_(Pok%C3%A9mon)`;
}

// Redirect to Pokemon inside the app
window.selectPokemon = function(slug) {
  const poke = pokedexData.find(p => p.slug === slug);
  if (poke) {
    searchInput.value = poke.name;
    searchQuery = poke.name.toLowerCase();
    searchClearBtn.style.display = "block";
    
    if (activePokedex !== "national" && poke.pokedex_numbers[activePokedex] === undefined) {
      pokedexSelect.value = "national";
      activePokedex = "national";
    }
    
    typeSelect.value = "all";
    selectedType = "all";
    methodSelect.value = "all";
    selectedMethod = "all";
    conditionSelect.value = "all";
    selectedCondition = "all";
    
    currentPage = 1;
    filterAndRender();
    
    document.getElementById("table-container").scrollIntoView({ behavior: 'smooth' });
  }
};

// Initialize Application
async function init() {
  setupEventListeners();
  try {
    const response = await fetch("data/pokedex_gen4.json");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    pokedexData = await response.json();
    filterAndRender();
  } catch (error) {
    console.error("Failed to load Pokedex data:", error);
    tableBody.innerHTML = `
      <tr class="error-row">
        <td colspan="5" style="text-align: center; padding: 3rem; color: #f87171;">
          <i class="fa-solid fa-triangle-exclamation" style="font-size: 2.5rem; margin-bottom: 1rem; display: block;"></i>
          <strong>Error loading Pokédex database!</strong><br>
          <span style="font-size: 0.9rem; color: #94a3b8;">Please run compile_pokedex.py to generate data/pokedex_gen4.json first.</span>
        </td>
      </tr>
    `;
  }
}

// Set up event handlers
function setupEventListeners() {
  // Search
  searchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value.toLowerCase().trim();
    searchClearBtn.style.display = searchQuery ? "block" : "none";
    currentPage = 1;
    filterAndRender();
  });

  // Clear Search
  searchClearBtn.addEventListener("click", () => {
    searchInput.value = "";
    searchQuery = "";
    searchClearBtn.style.display = "none";
    currentPage = 1;
    filterAndRender();
  });

  // Game buttons
  gameSelectors.addEventListener("click", (e) => {
    const btn = e.target.closest(".game-btn");
    if (!btn) return;
    
    // Update active states
    document.querySelectorAll(".game-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    
    activeGame = btn.dataset.game;
    currentPage = 1;
    filterAndRender();
  });

  // Select Filters
  pokedexSelect.addEventListener("change", (e) => {
    activePokedex = e.target.value;
    currentPage = 1;
    filterAndRender();
  });

  typeSelect.addEventListener("change", (e) => {
    selectedType = e.target.value;
    currentPage = 1;
    filterAndRender();
  });

  methodSelect.addEventListener("change", (e) => {
    selectedMethod = e.target.value;
    currentPage = 1;
    filterAndRender();
  });

  conditionSelect.addEventListener("change", (e) => {
    selectedCondition = e.target.value;
    currentPage = 1;
    filterAndRender();
  });

  // Pagination controls
  prevPageBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderTable();
    }
  });

  nextPageBtn.addEventListener("click", () => {
    const totalPages = getTotalPages();
    if (currentPage < totalPages) {
      currentPage++;
      renderTable();
    }
  });

  pageSizeSelect.addEventListener("change", (e) => {
    const val = e.target.value;
    pageSize = val === "all" ? "all" : parseInt(val, 10);
    currentPage = 1;
    renderTable();
  });

  // Table Sorting
  tableHeaders.forEach(th => {
    th.addEventListener("click", () => {
      const field = th.dataset.sort;
      if (sortBy === field) {
        // Toggle order
        sortOrder = sortOrder === "asc" ? "desc" : "asc";
      } else {
        sortBy = field;
        sortOrder = "asc";
      }
      
      // Update header icons
      tableHeaders.forEach(header => {
        const icon = header.querySelector("i");
        if (header === th) {
          icon.className = sortOrder === "asc" ? "fa-solid fa-sort-up" : "fa-solid fa-sort-down";
        } else {
          icon.className = "fa-solid fa-sort";
        }
      });
      
      filterAndRender();
    });
  });

  // Modal actions
  infoModalTrigger.addEventListener("click", () => {
    infoModal.classList.add("show");
  });

  modalClose.addEventListener("click", () => {
    infoModal.classList.remove("show");
  });

  // Close modal when clicking outside content
  window.addEventListener("click", (e) => {
    if (e.target === infoModal) {
      infoModal.classList.remove("show");
    }
  });
}

// Filter and sort the pokedexData, then render
function filterAndRender() {
  // Apply Filters
  filteredData = pokedexData.filter(pokemon => {
    // 1. Pokedex Filter
    if (activePokedex !== "national") {
      const dexKey = activePokedex;
      if (pokemon.pokedex_numbers[dexKey] === undefined) {
        return false;
      }
    }
    
    // 2. Type Filter
    if (selectedType !== "all") {
      if (!pokemon.types.includes(selectedType)) {
        return false;
      }
    }
    
    // 3. Obtain Method Filter
    if (selectedMethod !== "all") {
      const methods = pokemon.obtain_methods[activeGame];
      if (!methods.some(m => m.type === selectedMethod)) {
        return false;
      }
    }

    // 3b. Encounter Condition Filter
    if (selectedCondition !== "all") {
      const gameLocs = pokemon.locations[activeGame] || [];
      
      let match = false;
      if (selectedCondition === "swarm") {
        match = gameLocs.some(loc => loc.conditions && loc.conditions.includes("Swarm"));
      } else if (selectedCondition === "radar") {
        match = gameLocs.some(loc => loc.conditions && loc.conditions.includes("Poké Radar"));
      } else if (selectedCondition === "gba") {
        match = gameLocs.some(loc => loc.conditions && loc.conditions.some(c => c.startsWith("GBA")));
      } else if (selectedCondition.startsWith("gba-")) {
        const mapping = {
          "gba-ruby": "GBA Ruby",
          "gba-sapphire": "GBA Sapphire",
          "gba-emerald": "GBA Emerald",
          "gba-firered": "GBA FireRed",
          "gba-leafgreen": "GBA LeafGreen"
        };
        const targetCond = mapping[selectedCondition];
        match = gameLocs.some(loc => loc.conditions && loc.conditions.includes(targetCond));
      } else if (selectedCondition === "headbutt") {
        match = gameLocs.some(loc => loc.method === "Headbutt Trees");
      } else if (selectedCondition === "honey") {
        match = gameLocs.some(loc => loc.method === "Honey Tree");
      } else if (selectedCondition === "time") {
        match = gameLocs.some(loc => loc.conditions && loc.conditions.some(c => 
          c.includes("Morning") || c.includes("Day") || c.includes("Night") || c.startsWith("Weekday")
        ));
      }
      
      if (!match) {
        return false;
      }
    }
    
    // 4. Search Query Filter
    if (searchQuery !== "") {
      const nameMatch = pokemon.name.toLowerCase().includes(searchQuery);
      const natIdMatch = String(pokemon.id).includes(searchQuery);
      
      // Also match by specific Pokedex number if searching for numbers
      let dexNumMatch = false;
      if (activePokedex !== "national") {
        const dexNum = pokemon.pokedex_numbers[activePokedex];
        if (dexNum !== undefined && String(dexNum).includes(searchQuery)) {
          dexNumMatch = true;
        }
      }
      
      if (!nameMatch && !natIdMatch && !dexNumMatch) {
        return false;
      }
    }
    
    return true;
  });

  // Apply Sorting
  filteredData.sort((a, b) => {
    let comparison = 0;
    
    if (sortBy === "dex-id") {
      // Sort by the active pokedex index first, fall back to national ID
      const numA = activePokedex === "national" ? a.id : (a.pokedex_numbers[activePokedex] || 9999);
      const numB = activePokedex === "national" ? b.id : (b.pokedex_numbers[activePokedex] || 9999);
      comparison = numA - numB;
    } else if (sortBy === "name") {
      comparison = a.name.localeCompare(b.name);
    }
    
    return sortOrder === "asc" ? comparison : -comparison;
  });

  renderTable();
}

// Calculate total pages
function getTotalPages() {
  if (pageSize === "all") return 1;
  return Math.ceil(filteredData.length / pageSize) || 1;
}

// Render the filtered table rows
function renderTable() {
  const totalItems = filteredData.length;
  
  // Update stats summary text
  statsCount.innerHTML = `Showing <span>${totalItems}</span> of <span>${pokedexData.length}</span> Pokémon`;
  
  const typeText = selectedType !== "all" ? `${typeSelect.options[typeSelect.selectedIndex].text}-type ` : "";
  const methodText = selectedMethod !== "all" ? ` obtainable via ${methodSelect.options[methodSelect.selectedIndex].text.toLowerCase()} ` : "";
  activeFiltersDesc.innerHTML = `${gameNames[activeGame]} &bull; ${pokedexNames[activePokedex]} &bull; ${typeText}${methodText}Results`;

  // Render Loading / Empty state
  if (totalItems === 0) {
    tableBody.innerHTML = `
      <tr class="empty-row">
        <td colspan="5" style="text-align: center; padding: 3rem; color: var(--text-secondary);">
          <i class="fa-solid fa-magnifying-glass" style="font-size: 2rem; margin-bottom: 1rem; display: block; color: var(--text-muted);"></i>
          No Pokémon found matching the selected filters.
        </td>
      </tr>
    `;
    updatePaginationControls(0);
    return;
  }

  // Paginate
  const totalPages = getTotalPages();
  if (currentPage > totalPages) currentPage = totalPages;
  
  const startIdx = pageSize === "all" ? 0 : (currentPage - 1) * pageSize;
  const endIdx = pageSize === "all" ? totalItems : Math.min(startIdx + pageSize, totalItems);
  const paginatedData = filteredData.slice(startIdx, endIdx);

  // Build rows HTML
  let rowsHtml = "";
  
  paginatedData.forEach(pokemon => {
    // 1. Pokedex number formatting
    const dexNum = activePokedex === "national" ? pokemon.id : pokemon.pokedex_numbers[activePokedex];
    const formattedDexNum = String(dexNum).padStart(3, '0');
    
    // 2. Types list
    const typeBadges = pokemon.types.map(t => `<span class="type-badge type-${t}">${t}</span>`).join(" ");
    
    // 3. Evolution Details column
    let evolutionHtml = "";
    if (pokemon.evolves_from) {
      const triggerSpan = pokemon.trigger_text 
        ? `<span class="evo-trigger">${pokemon.trigger_text}</span>` 
        : "";
      evolutionHtml = `
        <span class="evo-parent">
          <i class="fa-solid fa-arrow-turn-up fa-rotate-90" style="margin-right: 0.35rem; color: var(--primary);"></i>
          <a class="evo-parent-link" href="#" onclick="selectPokemon('${pokemon.evolves_from_slug}'); return false;">${pokemon.evolves_from}</a>
        </span>
        ${triggerSpan}
      `;
    } else {
      evolutionHtml = `<span class="evo-none">Basic Form</span>`;
    }
    
    // 4. Obtain Method Column
    const methodsArray = pokemon.obtain_methods[activeGame];
    const methodBadgeHtml = methodsArray.map(m => `<span class="method-badge ${m.type}" style="margin-bottom: 0.25rem; display: inline-flex;">${m.description}</span>`).join(" ");
    
    // 5. Locations Details Column
    const gameLocs = pokemon.locations[activeGame];
    let locationsHtml = "";
    
    if (gameLocs && gameLocs.length > 0) {
      locationsHtml = gameLocs.map(loc => {
        const condBadges = loc.conditions && loc.conditions.length > 0
          ? loc.conditions.map(c => `<span class="location-cond">${c}</span>`).join("")
          : "";
          
        const isTradeOrBreeding = loc.method === "Breeding" || loc.method === "Trade / Transfer";
        const metaParts = [];
        metaParts.push(`<span class="location-method">${loc.method}</span>`);
        if (!isTradeOrBreeding) {
          metaParts.push(`<span class="location-chance">${loc.chance}%</span>`);
          metaParts.push(`<span class="location-level">Lv. ${loc.levels}</span>`);
        }
        const metaHtml = metaParts.join(" &bull; ") + (condBadges ? " " + condBadges : "");
        
        return `
          <div class="location-item">
            <span class="location-name">${loc.location}</span>
            <div class="location-meta">
              ${metaHtml}
            </div>
          </div>
        `;
      }).join("");
    } else {
      // Explanatory locations based on obtain method
      const texts = [];
      methodsArray.forEach(m => {
        if (m.type === "evolution") texts.push("Obtained by evolving pre-evolution.");
        else if (m.type === "egg" && m.description === "Breeding") texts.push("Obtained by breeding evolved form.");
        else if (m.type === "egg" && m.description === "Gift Egg") texts.push("Hatched from a gift Egg.");
        else if (m.type === "gift") texts.push("Received as a gift.");
        else if (m.type === "event") texts.push("Available via special distribution events.");
        else if (m.type === "transfer-only") texts.push("Must be traded from another version or transferred from Generation III.");
      });
      const uniqueTexts = [...new Set(texts)];
      locationsHtml = `<span class="locations-empty">${uniqueTexts.join("<br>")}</span>`;
    }
    
    // 6. Build the table row
    rowsHtml += `
      <tr>
        <td data-label="Index" class="col-index">#${formattedDexNum}</td>
        <td data-label="Pokémon" class="col-pokemon">
          <div class="pokemon-cell">
            <div class="pokemon-sprite-wrapper">
              ${pokemon.sprite 
                ? `<img class="pokemon-sprite" src="${pokemon.sprite}" alt="${pokemon.name}" loading="lazy">` 
                : `<i class="fa-solid fa-circle" style="color: rgba(255,255,255,0.05); font-size: 2rem;"></i>`
              }
            </div>
            <div class="pokemon-info">
              <span class="pokemon-name">
                <a class="pokemon-name-link" href="${getBulbapediaUrl(pokemon.name)}" target="_blank" rel="noopener noreferrer">${pokemon.name}</a>
              </span>
              <div class="pokemon-types">${typeBadges}</div>
            </div>
          </div>
        </td>
        <td data-label="Encounter Method" class="col-method">
          <div class="method-cell">
            ${methodBadgeHtml}
          </div>
        </td>
        <td data-label="Evolution Condition" class="col-evo">
          <div class="evo-cell">${evolutionHtml}</div>
        </td>
        <td data-label="Location Details" class="col-locations">
          <div class="locations-cell">${locationsHtml}</div>
        </td>
      </tr>
    `;
  });

  tableBody.innerHTML = rowsHtml;
  updatePaginationControls(totalItems);
}

// Update pagination buttons and text
function updatePaginationControls(totalItems) {
  const totalPages = getTotalPages();
  
  if (pageSize === "all" || totalItems === 0) {
    prevPageBtn.disabled = true;
    nextPageBtn.disabled = true;
    pageInfo.textContent = `Showing all items`;
  } else {
    prevPageBtn.disabled = currentPage === 1;
    nextPageBtn.disabled = currentPage === totalPages;
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  }
}

// Boot the app
document.addEventListener("DOMContentLoaded", init);
