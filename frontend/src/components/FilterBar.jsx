const MINISTRIES = [
  { label: "All Ministries", value: "" },
  { label: "MoHFW", value: "Ministry of Health and Family Welfare" },
  { label: "MoWCD", value: "Ministry of Women and Child Development" },
  { label: "MoCAFPD", value: "Consumer Affairs" },
  { label: "MoE", value: "Ministry of Education" },
  { label: "MoTA", value: "Tribal Affairs" },
  { label: "NITI Aayog", value: "NITI Aayog" },
  { label: "Google Alerts", value: "Google Alert" },
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
        {MINISTRIES.map(m => (
          <option key={m.value} value={m.value}>{m.label}</option>
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
