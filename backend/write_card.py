content = '''import { useState } from "react";

const STATUS_COLORS = {
  active:       { bg: "#e6f4f1", text: "#0097a7", border: "#0097a7" },
  proposed:     { bg: "#fdf3e7", text: "#e07b39", border: "#e07b39" },
  discontinued: { bg: "#fdecea", text: "#c0392b", border: "#c0392b" },
  "under review":{ bg: "#fdf3e7", text: "#8e6f00", border: "#f0c040" },
  unknown:      { bg: "#f5f5f5", text: "#777",    border: "#ccc" },
};

export default function ProgramCard({ program: p }) {
  const sc = STATUS_COLORS[p.status?.toLowerCase()] || STATUS_COLORS.unknown;
  return (
    <div className="program-card">
      <div className="card-header">
        <div className="card-title-block">
          <h3 className="card-title">{p.program_name}</h3>
          <span className="ministry-tag">{p.ministry}</span>
        </div>
        <span className="status-badge"
          style={{ background: sc.bg, color: sc.text, borderColor: sc.border }}>
          {p.status || "unknown"}
        </span>
      </div>
      <div className="card-meta">
        {p.scope && (
          <span className={`scope-pill ${p.scope}`}>
            {p.scope === "state" && p.state_name ? "State - " + p.state_name : "Central"}
          </span>
        )}
        {p.date_announced && <span className="meta-item">{p.date_announced}</span>}
        {p.budget_amount && <span className="meta-item">{p.budget_amount}</span>}
      </div>
      {p.summary && <p className="card-summary">{p.summary}</p>}
      {p.target_beneficiaries && (
        <div className="card-row">
          <span className="row-label">Beneficiaries</span>
          <span className="row-value">{p.target_beneficiaries}</span>
        </div>
      )}
      {p.key_interventions?.length > 0 && (
        <div className="interventions-block">
          <span className="row-label">Key interventions</span>
          <div className="intervention-tags">
            {p.key_interventions.map((ki, i) => (
              <span key={i} className="intervention-tag">{ki}</span>
            ))}
          </div>
        </div>
      )}
      <div className="card-footer">
        <a href={"https://www.google.com/search?q=" + encodeURIComponent(p.program_name + " India government program")}
          target="_blank" rel="noopener noreferrer" className="source-link">
          Search online
        </a>
        {p.source_url && p.source_url !== "Gmail Alert" && p.source_url !== "Seed data" && (
          <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
            View source
          </a>
        )}
        <span className="updated-text">Updated {p.updated_at ? p.updated_at.slice(0, 10) : ""}</span>
      </div>
    </div>
  );
}
'''

with open(r"C:\Users\rebec\OneDrive\Documents\anaemia-malnutrition-tracker\frontend\src\components\ProgramCard.jsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Done!")