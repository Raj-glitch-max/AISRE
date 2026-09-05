const { Panel, Divider, StatusBadge, MetaLabel } = window.AnnunciatorAISREDesignSystem_cada24;

function IncidentRow({ incident, onOpen }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div
      onClick={() => onOpen(incident.id)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "grid",
        gridTemplateColumns: "92px 1fr 132px",
        alignItems: "center",
        gap: "var(--space-md)",
        padding: "var(--space-sm) var(--space-md)",
        background: hover ? "var(--surface-row-hover)" : "var(--surface-page)",
        cursor: "pointer",
        transition: "none",
      }}
    >
      <MetaLabel>{incident.id}</MetaLabel>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: "var(--type-body-md-size)", color: "var(--text-body)", lineHeight: 1.3 }}>
          {incident.title}
        </div>
        <MetaLabel size="caption" style={{ display: "block", marginTop: 2 }}>
          {incident.service} · {incident.updated}
        </MetaLabel>
      </div>
      <StatusBadge status={incident.status} on={hover ? "panel" : "page"} style={{ justifySelf: "end" }} />
    </div>
  );
}

function IncidentList({ incidents, onOpen }) {
  const awaiting = incidents.filter((i) => i.status === "pending_approval").length;
  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          padding: "0 var(--space-md) var(--space-md)",
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "baseline", gap: "var(--space-sm)" }}>
          <MetaLabel variant="caps">Incidents</MetaLabel>
          <MetaLabel>{incidents.length} active</MetaLabel>
        </span>
        {awaiting > 0 && <StatusBadge variant="caution" label={awaiting + " AWAITING"} on="page" />}
      </div>
      <Divider />
      {incidents.map((incident, i) => (
        <React.Fragment key={incident.id}>
          <IncidentRow incident={incident} onOpen={onOpen} />
          {i < incidents.length - 1 && <Divider />}
        </React.Fragment>
      ))}
      <Divider />
    </div>
  );
}

Object.assign(window, { IncidentList, IncidentRow });
