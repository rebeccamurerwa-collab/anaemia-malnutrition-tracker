const STATES = [
  "", "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Gujarat", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha",
  "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
  "Uttar Pradesh", "West Bengal",
];

const YEARS = [""];
for (let y = new Date().getFullYear(); y >= 1980; y--) {
  YEARS.push(String(y));
}

export function FilterBar({ filters, setFilters }) {
  const set = (k, v) => setFilters(f => ({ ...f, [k]: v }));
  return (
    <div className="filter-bar">
      <select value={filters.category}
              onChange={e => set("category", e.target.value)}>
        <option value="">All Categories</option>
        <option value="anaemia">Anaemia</option>
        <option value="malnutrition">Malnutrition</option>
        <option value="both">Both</option>
      </select>

      <select value={filters.state}
              onChange={e => set("state", e.target.value)}>
        <option value="">All States</option>
        {STATES.filter(Boolean).map(s => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <select value={filters.year}
              onChange={e => set("year", e.target.value)}>
        <option value="">All Years</option>
        {YEARS.filter(Boolean).map(y => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>

      <select value={filters.source}
              onChange={e => set("source", e.target.value)}>
        <option value="">All Sources</option>
        <option value="PIB">PIB Press Releases</option>
        <option value="Gmail">Google Alerts</option>
        <option value="Seed">Seed Data</option>
      </select>

      <button
        className="clear-btn"
        onClick={() => setFilters({ category: "", state: "", year: "", source: "" })}
      >
        Clear
      </button>
    </div>
  );
}
export default FilterBar;