import React, { useEffect, useState } from "react";
import Papa from "papaparse"; // npm install papaparse
import "../styles.css"


export default function PatternAdvisor({ player, team, onBack }) {
  const [patterns, setPatterns] = useState([]);
  const [report, setReport] = useState("");

  // === Token Interpreter ===
  function interpretToken(token) {
    const parts = token.split("_vs_");
    if (parts.length !== 2)
      return { raid_type: "unknown", outcome: "unknown", team: "unknown", opponent: "unknown" };

    const left = parts[0].split("_");
    const raid_type = left[0] || "unknown";
    const outcome = left[1] || "unknown";
    const teamName = left.slice(2).join("_") || "unknown";
    const opponent = parts[1].split("_")[0];
    return { raid_type, outcome, team: teamName, opponent };
  }

  // === Infer Pattern Meaning ===
  function inferMeaning(patternRow) {
    const pattern = patternRow.pattern;
    const support = Number(patternRow.support) || 0;
    const gain = Number(patternRow.gain) || 0;

    const tokens = pattern.split("||");
    const parts = tokens.map((t) => interpretToken(t));

    const desc = parts.map((p) => {
      const rt = p.raid_type;
      const oc = p.outcome;
      if (rt === "doordie") return `Do-or-Die raid (${oc})`;
      if (rt === "bonus") return `Bonus attempt (${oc})`;
      if (rt === "regular") return `Regular raid (${oc})`;
      if (rt === "empty") return `Empty raid (${oc})`;
      if (rt === "allout") return `All-Out phase (${oc})`;
      return `Other raid (${oc})`;
    });

    const description = desc.join(" → ");

    let sentiment = "uncommon or neutral";
    if (gain > 0) sentiment = "frequent and advantageous";
    else if (gain === -1) sentiment = "common but low-impact";

    let implication = "neutral or non-scoring trend";
    if (pattern.includes("success")) implication = "positive scoring tendency";
    else if (pattern.includes("empty") || pattern.includes("unknown"))
      implication = "neutral or non-scoring trend";
    else implication = "negative scoring trend";

    return {
      Pattern: description,
      Support: support,
      Gain: gain,
      Summary: `This pattern (${description}) occurs ${support} times and represents a ${sentiment} behavior (${implication}).`,
    };
  }

  // === Tactical Advice Generator ===
  function generateAdvice(df) {
    const successPatterns = df.filter((d) => d.pattern.includes("success"));
    const unknownPatterns = df.filter((d) => d.pattern.match(/unknown|empty/));
    const bonusPatterns = df.filter((d) => d.pattern.includes("bonus"));
    const doordiePatterns = df.filter((d) => d.pattern.includes("doordie"));

    const reportLines = [];
    reportLines.push(`### Tactical Report for ${player} vs ${team}`);
    reportLines.push(`**Total Patterns Analyzed:** ${df.length}`);

    if (doordiePatterns.length > 0)
      reportLines.push(
        `- ${player} frequently engages in Do-or-Die raids — useful for high-pressure moments.`
      );
    if (bonusPatterns.length > 0)
      reportLines.push(
        `- Bonus attempts are part of ${player}'s strategy — can exploit weak corners or single defenders.`
      );
    if (unknownPatterns.length > 10)
      reportLines.push(
        `- Several non-scoring or unclear raids detected — potential inefficiency or defensive strength from ${team}.`
      );
    if (successPatterns.length > unknownPatterns.length)
      reportLines.push(`- Higher success ratio suggests ${player} performs effectively against ${team}.`);
    else
      reportLines.push(`- Lower success ratio suggests ${player} struggles to convert raids against ${team}’s defense.`);

    reportLines.push("\n### 🏹 Recommendations:");
    if (doordiePatterns.length > unknownPatterns.length)
      reportLines.push("Use in Do-or-Die situations for momentum shifts.");
    else reportLines.push("Avoid excessive Do-or-Die raids; defense adapts quickly.");
    if (bonusPatterns.length > 0) reportLines.push("Encourage bonus attempts early in the raid clock.");
    if (unknownPatterns.length > successPatterns.length)
      reportLines.push("Review defensive setups; too many non-scoring attempts.");

    return reportLines.join("\n");
  }

  // === Auto Load CSV when player/team changes ===
  useEffect(() => {
    if (!player || !team) return;

    const formattedPlayer = player.replace(/ /g, "_");
    const formattedTeam = team.replace(/ /g, "_");
    const filePath = `../../server/PlayerRaids/patterns_${formattedPlayer}__${formattedTeam}.csv`;

    Papa.parse(filePath, {
      header: true,
      download: true, // fetch from /public/data/
      complete: (result) => {
        const data = result.data.filter((row) => row.pattern);
        if (data.length === 0) {
          console.warn("No pattern data found for:", filePath);
          setReport(`No pattern data available for ${player} vs ${team}.`);
          setPatterns([]);
          return;
        }

        const interpreted = data.map(inferMeaning);
        setPatterns(interpreted);
        setReport(generateAdvice(data));
      },
      error: (err) => {
        console.error("Failed to load CSV:", err);
        setReport(`Failed to load data for ${player} vs ${team}.`);
      },
    });
  }, [player, team]);

  return (
    <div className="pattern-container">
      <div className="pattern-header">
        <h1>Kabaddi Pattern Advisor</h1>
      </div>

      {report && (
        <div className="report-section">
          <h2>Tactical Report</h2>
          <pre>{report}</pre>
        </div>
      )}

      {patterns.length > 0 ? (
        <table className="pattern-table">
          <thead>
            <tr>
              <th>Pattern</th>
              <th>Support</th>
              <th>Gain</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {patterns.map((p, i) => (
              <tr key={i}>
                <td>{p.Pattern}</td>
                <td>{p.Support}</td>
                <td className={p.Gain > 0 ? "gain-positive" : p.Gain < 0 ? "gain-negative" : "gain-neutral"}>
                  {p.Gain}
                </td>
                <td>{p.Summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="no-data">No patterns available for this player/team.</p>
      )}
    </div>
  );
}