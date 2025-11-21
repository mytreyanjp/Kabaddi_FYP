import React, { useEffect, useState } from "react";

export default function Hierarchy({ playerName = null, opponentTeam = null, onPlayerClick }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    function handler(e) {
      const { teamA, teamB, player } = e.detail;
      run(teamA, teamB, player);
    }
    window.addEventListener("mdl-run", handler);
    return () => window.removeEventListener("mdl-run", handler);
  }, []);

  async function run(teamA, teamB, player = null) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch("http://127.0.0.1:5000/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ teamA, teamB, player }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Server error: ${resp.status} ${txt}`);
      }

      const js = await resp.json();
      console.log("[DEBUG] /api/run response:", js);
      setResult(js);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const hasTeamRanking = result && result.pattern_type === "team" && Array.isArray(result.ranking);
  const hasModels = result && result.models && Array.isArray(result.models);

  return (
    <div className="card">
      <h2>Results</h2>

      {/* Loading */}
      {loading && <div className="muted">Computing MDL on server...</div>}

      {/* Error */}
      {error && <div style={{ color: "#ff8080" }}>{error}</div>}

      {/* Initial Idle State */}
      {!loading && !result && !error && (
        <div className="muted" style={{ textAlign: "center" }}>
          {playerName ? (
            <>
              Analyzing <b>{playerName}</b> vs <b>{opponentTeam || "Opponent"}</b>...
            </>
          ) : (
            <>
              Select teams and click <b>Compute MDL</b>.
            </>
          )}
        </div>
      )}

      {/* ===== TEAM MODE ===== */}
      {!loading && hasTeamRanking && (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div className="muted">
                Team A: <b>{result.teamA}</b>
              </div>
              <div className="muted">
                Team B: <b>{result.teamB}</b>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="muted">
                Best Model: <b>{result.best_model}</b>
              </div>
            </div>
          </div>

          <h3 style={{ marginTop: 12 }}>Player Rankings</h3>
          {result.ranking.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  <th>Matches</th>
                  <th>Avg Points</th>
                  <th>Total Points</th>
                  <th>Model Mean</th>
                  <th>Visual</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {result.ranking.map((r, i) => (
                  <tr
                    key={r.player}
                    onClick={() => onPlayerClick && onPlayerClick(r.player, result.teamA)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>{i + 1}</td>
                    <td>{r.player}</td>
                    <td>{r.matches}</td>
                    <td>{r.avg_points?.toFixed(2) || 0}</td>
                    <td>{r.total_points?.toFixed(2) || 0}</td>
                    <td>{r.model_mean?.toFixed(2) || 0}</td>
                    <td style={{ width: 240 }}>
                      <div
                        className="bar"
                        style={{
                          width: Math.min(100, (r.model_mean || 0) * 3) + "%",
                          backgroundColor: "#42a5f5",
                          height: "10px",
                          borderRadius: "4px",
                        }}
                      ></div>
                    </td>
                    <td>
                      <button
                        className="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onPlayerClick && onPlayerClick(r.player, result.teamA);
                        }}
                      >
                        View Player
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{ textAlign: "center", color: "#aaa" }}>
              No players found for this matchup.
            </p>
          )}

          {/* Models */}
          {hasModels && (
            <>
              <h3 style={{ marginTop: 20 }}>Model Comparison</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>DL (bits)</th>
                  </tr>
                </thead>
                <tbody>
                  {result.models.map((m) => (
                    <tr key={m.name}>
                      <td>{m.name}</td>
                      <td>{Number(m.dl).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}

      {/* ===== PLAYER MODE SAFEGUARD ===== */}
      {!loading && result && result.pattern_type === "insight" && (
        <div style={{ textAlign: "center", color: "#aaa" }}>
          <p>
            Player data loaded successfully.  
            Please switch to the <b>Player Dashboard</b> view.
          </p>
        </div>
      )}

      {/* ===== FALLBACK ===== */}
      {!loading && result && !hasTeamRanking && !error && (
        <div style={{ textAlign: "center", color: "#aaa" }}>
          <p>No ranking data found for the selected input.</p>
        </div>
      )}
    </div>
  );
}
