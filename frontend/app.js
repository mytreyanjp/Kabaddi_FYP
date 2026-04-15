const TEAM_META = {
  heuristic_team: {
    label: "Heuristic",
    accent: "#c88d2f",
    description: "Rule-based shortlist from player effectiveness features.",
  },
  ilp_team: {
    label: "ILP",
    accent: "#3d6b52",
    description: "Constraint-optimized lineup from integer programming.",
  },
  genetic_algorithm_team: {
    label: "Genetic Algorithm",
    accent: "#7f5fce",
    description: "Evolutionary search over valid 7-player squads.",
  },
  simulated_annealing_team: {
    label: "Simulated Annealing",
    accent: "#bc5f3c",
    description: "Temperature-guided search for a high-scoring roster.",
  },
  tabu_search_team: {
    label: "Tabu Search",
    accent: "#2f7f8d",
    description: "Neighborhood search with tabu memory to avoid repeats.",
  },
};

const TEAM_ORDER = [
  "heuristic_team",
  "ilp_team",
  "simulated_annealing_team",
  "tabu_search_team",
  "genetic_algorithm_team",
];

const state = {
  lineup: null,
};

const statusEl = document.getElementById("status");
const teamGridEl = document.getElementById("team-grid");
const summaryCardsEl = document.getElementById("summary-cards");

function initialsFor(name) {
  return String(name)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function prettyNumber(value) {
  return Number(value || 0).toFixed(1);
}

function sortPlayersByName(players) {
  return [...players].sort((a, b) =>
    String(a.player_name || "").localeCompare(String(b.player_name || ""), undefined, {
      sensitivity: "base",
    })
  );
}

function computeSummary(players) {
  const totals = players.reduce(
    (acc, player) => {
      acc.overall += Number(player.overall_points || 0);
      acc.offense += Number(player.offense_points || 0);
      acc.defense += Number(player.defense_points || 0);
      acc.seasons += Number(player.total_seasons || 0);
      acc.roles[player.tag] = (acc.roles[player.tag] || 0) + 1;
      return acc;
    },
    { overall: 0, offense: 0, defense: 0, seasons: 0, roles: {} }
  );

  return {
    overall: totals.overall,
    offense: totals.offense,
    defense: totals.defense,
    avgSeasons: totals.seasons / Math.max(players.length, 1),
    roles: totals.roles,
  };
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "status-card error" : "status-card";
}

function renderSummaryCards() {
  const entries = Object.entries(state.lineup || {}).map(([key, team]) => {
    const meta = TEAM_META[key];
    const summary = computeSummary(team.players);
    return { key, meta, summary };
  });

  const sorted = entries.sort((a, b) => b.summary.overall - a.summary.overall);
  summaryCardsEl.innerHTML = sorted
    .map(
      ({ meta, summary }, index) => `
        <article class="summary-card">
          <p class="eyebrow">${index === 0 ? "Top total" : "Squad score"}</p>
          <strong>${meta.label}</strong>
          <div class="summary-score">${prettyNumber(summary.overall)}</div>
          <div class="meta-label">Combined overall points</div>
        </article>
      `
    )
    .join("");
}

function createPlayerCard(player) {
  const role = player.tag || "player";
  const avatar = player.photo_url
    ? `
      <div class="player-avatar">
        <img src="${player.photo_url}" alt="${player.player_name}" onerror="this.parentElement.innerHTML='${initialsFor(
          player.player_name
        )}'" />
      </div>
    `
    : `<div class="player-avatar">${initialsFor(player.player_name)}</div>`;

  return `
    <article class="player-card">
      ${avatar}
      <div>
        <div class="tag-row">
          <p class="player-name">${player.player_name}</p>
          <span class="role-pill ${role}">${role}</span>
        </div>
        <p class="player-meta">${player.primary_position || "Unknown position"}</p>
        <div class="role-row">
          <span class="metric-chip"><strong>${prettyNumber(player.overall_points)}</strong> overall</span>
          <span class="metric-chip"><strong>${prettyNumber(player.offense_points)}</strong> offense</span>
          <span class="metric-chip"><strong>${prettyNumber(player.defense_points)}</strong> defense</span>
        </div>
      </div>
    </article>
  `;
}

function renderTeams() {
  const teamEntries = TEAM_ORDER
    .filter((teamKey) => state.lineup?.[teamKey])
    .map((teamKey) => [teamKey, state.lineup[teamKey]]);
  teamGridEl.innerHTML = teamEntries
    .map(([teamKey, team]) => {
      const meta = TEAM_META[teamKey];
      const players = sortPlayersByName(team.players || []);
      const summary = computeSummary(players);
      return `
        <article class="team-card" data-team-key="${teamKey}" style="border-top: 6px solid ${meta.accent}">
          <div class="team-card-main">
            <div class="team-card-header">
              <p class="eyebrow">${meta.label}</p>
              <div>
                <h3>${meta.description}</h3>
                <p class="team-subtitle">${team.players.length} selected players</p>
              </div>
            </div>
            <div class="metric-row">
              <div class="metric-chip">
                <strong>${prettyNumber(summary.overall)}</strong>
                Combined overall
              </div>
              <div class="metric-chip">
                <strong>${summary.avgSeasons.toFixed(1)}</strong>
                Avg. seasons
              </div>
            </div>
            <div class="role-row">
              <span class="role-pill raider">${summary.roles.raider || 0} raiders</span>
              <span class="role-pill defender">${summary.roles.defender || 0} defenders</span>
              <span class="role-pill allrounder">${summary.roles.allrounder || 0} allrounders</span>
            </div>
          </div>
          <div class="team-card-roster">
            <div class="roster-grid">
            ${players.map(createPlayerCard).join("")}
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadLineup() {
  try {
    const response = await fetch("/api/lineup");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    state.lineup = await response.json();
    renderSummaryCards();
    renderTeams();
    setStatus("Lineups loaded from the backend.");
  } catch (error) {
    setStatus(`Unable to load lineups from the backend. ${error.message}`, true);
  }
}

loadLineup();
