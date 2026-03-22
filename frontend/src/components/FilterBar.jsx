const MINISTRIES = [
  "",
  "MoHFW",
  "MoWCD",
  "MoCAFPD",
  "MoE",
  "MoTA",
  "NITI Aayog",
  "Google Alert / News",
];

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
      <select value={filters.ministry}
              onChange={e => set("ministry", e.target.value)}>
        <option value="">All Ministries</option>
        {MINISTRIES.filter(Boolean).map(m => (
          <option key={m} value={m}>{m}</option>
        ))}
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

      <button
        className="clear-btn"
        onClick={() => setFilters({ ministry: "", state: "", year: "" })}
      >
        Clear
      </button>
    </div>
  );
}
export default FilterBar;
