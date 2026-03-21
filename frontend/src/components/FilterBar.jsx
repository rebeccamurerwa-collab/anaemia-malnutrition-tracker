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

      <select value={filters.scope}
              onChange={e => set("scope", e.target.value)}>
        <option value="">Central &amp; State</option>
        <option value="central">Central only</option>
        <option value="state">State only</option>
      </select>

      <select value={filters.status}
              onChange={e => set("status", e.target.value)}>
        <option value="">All Statuses</option>
        <option value="active">Active</option>
        <option value="proposed">Proposed</option>
        <option value="under review">Under Review</option>
        <option value="discontinued">Discontinued</option>
      </select>

      <input
        type="text"
        placeholder="Filter by state name…"
        value={filters.state}
        onChange={e => set("state", e.target.value)}
      />

      <button
        className="clear-btn"
        onClick={() => setFilters({ ministry: "", scope: "", status: "", state: "" })}
      >
        Clear
      </button>
    </div>
  );
}
export default FilterBar;