import React, { useEffect, useState } from 'react'
import Hierarchy from './components/Hierarchy'
import PlayerDashboard from './components/PlayerDashboard'


export default function App() {
  const [teamA, setTeamA] = useState('')
  const [teamB, setTeamB] = useState('')
  const [teams, setTeams] = useState([])
  const [selectedPlayer, setSelectedPlayer] = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadTeams = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5000/api/teams')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.teams && Array.isArray(data.teams)) setTeams(data.teams)
        else throw new Error('Invalid team data format')
      } catch (err) {
        console.error('Failed to load teams:', err)
        setError('Unable to fetch team list from server.')
      } finally {
        setLoading(false)
      }
    }
    loadTeams()
  }, [])

  const handleRun = () => {
    if (!teamA || !teamB) {
      alert('Select both Team A and Team B.')
      return
    }
    // Tell Hierarchy to run MDL for selected teams
    window.dispatchEvent(new CustomEvent('mdl-run', { detail: { teamA, teamB } }))
  }

if (selectedPlayer && selectedTeam) {
  return (
    <PlayerDashboard
      player={selectedPlayer}
      team={selectedTeam}
      onBack={() => {
        setSelectedPlayer(null)
        setSelectedTeam(null)
      }}
    />
  )
}


  return (
    <div className="app">
      <div className="card" style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: '24px', marginBottom: '10px' }}>Kabaddi MDL Raider Hierarchy</h1>
        <p className="muted">Select a team and an opponent to analyze raider performance.</p>

        {loading && <div className="muted">Loading teams...</div>}
        {error && <div style={{ color: 'salmon' }}>{error}</div>}

        {!loading && !error && (
          <div className="controls" style={{ justifyContent: 'center', marginTop: '20px' }}>
            <select
              className="select"
              value={teamA}
              onChange={(e) => setTeamA(e.target.value)}
            >
              <option value="">Select Team A</option>
              {teams.map((team) => (
                <option key={'a-' + team} value={team} disabled={team === teamB}>
                  {team}
                </option>
              ))}
            </select>

            <select
              className="select"
              value={teamB}
              onChange={(e) => setTeamB(e.target.value)}
            >
              <option value="">Select Team B</option>
              {teams.map((team) => (
                <option key={'b-' + team} value={team} disabled={team === teamA}>
                  {team}
                </option>
              ))}
            </select>

            <button className="button" onClick={handleRun}>
              Compute MDL
            </button>
          </div>
        )}
      </div>

      <Hierarchy
        playerName={selectedPlayer}
        opponentTeam={selectedTeam}
        onPlayerClick={(player, team) => {
          setSelectedPlayer(player)
          setSelectedTeam(team)
        }}
      />
      
    </div>
  )
}
