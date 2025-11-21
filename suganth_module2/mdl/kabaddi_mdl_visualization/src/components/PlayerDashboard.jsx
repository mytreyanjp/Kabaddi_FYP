import React, { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import PatternAdvisor from "./PatternAdvisor";

export default function PlayerDashboard({ player, team, onBack }) {
  const [data, setData] = useState(null);
  const [insightData, setInsightData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const resp = await fetch("http://127.0.0.1:5000/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ teamA: team, teamB: "All Opponents", player }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const js = await resp.json();
        setData(js);

        if (js.insight_data) {
          setInsightData(js.insight_data);
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load player data");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [player, team]);

  if (loading) return <div className="muted">Loading Player Dashboard...</div>;
  if (error) return <div style={{ color: "salmon" }}>{error}</div>;
  if (!data) return <div>No player data available.</div>;

  const summary = data.summary || {};
  const insights = insightData || [];

  // Averages for header
  const avgSuccess =
    insights.length > 0
      ? (
          insights.reduce((sum, i) => sum + (i.success_rate || 0), 0) /
          insights.length
        ).toFixed(2)
      : 0;
  const avgPoints =
    insights.length > 0
      ? (
          insights.reduce((sum, i) => sum + (i.avg_points || 0), 0) /
          insights.length
        ).toFixed(2)
      : 0;

  return (
    <div className="card" style={{ padding: "20px" }}>
      <button className="button" onClick={onBack} style={{ marginBottom: "20px" }}>
        ← Back
      </button>

      <h2 style={{ textAlign: "center" }}>Player Performance Dashboard</h2>
      <h3 style={{ textAlign: "center", color: "#aaa" }}>{player}</h3>
      <p style={{ textAlign: "center" }}>
        Team: <b>{team}</b> | Opponents: <b>{insights.length}</b>
      </p>

      {/* Stats Summary */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          textAlign: "center",
          marginBottom: "30px",
        }}
      >
        <div>
          <h4>Average Success Rate</h4>
          <p>{avgSuccess}%</p>
        </div>
        <div>
          <h4>Average Points</h4>
          <p>{avgPoints}</p>
        </div>
        <div>
          <h4>Total Opponents</h4>
          <p>{insights.length}</p>
        </div>
      </div>

      {/* Charts */}
        <div
        style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "20px",
            marginBottom: "40px",
        }}
        >
        {/* Success Rate Bar */}
        <Plot
            data={[
            {
                x: insightData.map((d) => d.opponent),
                y: insightData.map((d) => (d.success_rate * 100).toFixed(2)),
                type: "bar",
                text: insightData.map((d) => (d.success_rate * 100).toFixed(2) + "%"),
                textposition: "outside",
                marker: { color: "rgba(0,150,255,0.7)" },
                name: "Success Rate",
            },
            ]}
            layout={{
            title: "Success Rate vs Teams",
            xaxis: { title: "Opponent Team", tickangle: -45 },
            yaxis: { title: "Success Rate (%)", range: [0, 100] },
            plot_bgcolor: "transparent",
            paper_bgcolor: "transparent",
            font: { color: "#ddd" },
            height: 400,
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: "100%", height: "100%" }}
        />

        {/* Average Points Line */}
        <Plot
            data={[
            {
                x: insightData.map((d) => d.opponent),
                y: insightData.map((d) => Number(d.avg_points) || 0),
                type: "scatter",
                mode: "lines+markers",
                line: { color: "#ffb300", shape: "spline", width: 3 },
                marker: { size: 6 },
                name: "Avg Points per Raid",
                connectgaps: true,
            },
            ]}
            layout={{
            title: "Average Points per Raid vs Teams",
            xaxis: { title: "Opponent Team", tickangle: -45 },
            yaxis: { title: "Avg Points per Raid", rangemode: "tozero" },
            plot_bgcolor: "transparent",
            paper_bgcolor: "transparent",
            font: { color: "#ddd" },
            height: 400,
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: "100%", height: "100%" }}
        />
        </div>

        {/* Table */}
        <h3 style={{ marginBottom: "10px" }}>Opponent-Wise Statistics</h3>
        <table className="table" style={{ width: "100%" }}>
        <thead>
            <tr>
            <th>Opponent</th>
            <th>Success Rate (%)</th>
            <th>Avg Points</th>
            <th>Total Raids</th>
            <th>Do-or-Die Count</th>
            <th>Bonus Count</th>
            </tr>
        </thead>
        <tbody>
            {insightData.map((i, idx) => (
            <tr key={idx}>
                <td>{i.opponent}</td>
                <td>{(i.success_rate * 100).toFixed(2)}</td>
                <td>{i.avg_points?.toFixed(2) || "0.00"}</td>
                <td>{i.total_raids || 0}</td>
                <td>{i.doordie_count || 0}</td>
                <td>{i.bonus_count || 0}</td>
            </tr>
            ))}
        </tbody>
        </table>
        <PatternAdvisor player={player} team={team} onBack={() => setView("dashboard")} />
        
    </div>
  );
}
