import { useState, useEffect } from "react";
import Header from "./components/Header";
import StatsBar from "./components/StatsBar";
import FilterBar from "./components/FilterBar";
import ProgramCard from "./components/ProgramCard";

const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

export default function App() {
  const [programs, setPrograms]   = useState([]);
  const [stats, setStats]         = useState(null);
  const [loading, setLoading]     = useState(true);
  const [filters, setFilters]     = useState({
    category: "", state: "", year: ""
  });

  const fetchPrograms = async () => {
    setLoading(true);
    const params = new URLSearchParams(
      Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
    );
    try {
      const res  = await fetch(`${API}/api/programs?${params}`);
      const data = await res.json();
      setPrograms(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const res  = await fetch(`${API}/api/stats`);
      const data = await res.json();
      setStats(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchPrograms(); }, [filters]);
  useEffect(() => { fetchStats(); }, []);

  return (
    <div className="app-shell">
      <Header />
      {stats && <StatsBar stats={stats} />}
      <main className="main-content">
        <FilterBar filters={filters} setFilters={setFilters} />
        {loading ? (
          <div className="loading-wrap">
            <div className="spinner" />
            <p>Loading programs…</p>
          </div>
        ) : programs.length === 0 ? (
          <div className="empty-state">
            <p>No programs found. Try adjusting your filters, or trigger a scrape.</p>
          </div>
        ) : (
          <div className="card-grid">
            {programs.map(p => <ProgramCard key={p.id} program={p} />)}
          </div>
        )}
      </main>
      <footer className="footer">
        <p>Data sourced from PIB India · Powered by Gemini AI · Updated weekly</p>
      </footer>
    </div>
  );
}