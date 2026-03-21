export function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="stats-bar">
      <div className="stat-chip">
        <span className="stat-num">{stats.total}</span>
        <span className="stat-label">Total Programs</span>
      </div>
      <div className="stat-chip">
        <span className="stat-num">{stats.by_status?.active || 0}</span>
        <span className="stat-label">Active</span>
      </div>
      <div className="stat-chip">
        <span className="stat-num">{stats.by_scope?.state || 0}</span>
        <span className="stat-label">State-specific</span>
      </div>
      <div className="stat-chip">
        <span className="stat-num">{stats.by_scope?.central || 0}</span>
        <span className="stat-label">Central</span>
      </div>
      <div className="stat-chip">
        <span className="stat-num">{Object.keys(stats.by_ministry || {}).length}</span>
        <span className="stat-label">Ministries</span>
      </div>
    </div>
  );
}
export default StatsBar;