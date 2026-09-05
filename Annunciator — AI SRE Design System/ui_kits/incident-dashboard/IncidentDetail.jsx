const { Panel, Divider, StatusBadge, Stepper, DataReadout, MetaLabel, ApproveButton, Tooltip } =
  window.AnnunciatorAISREDesignSystem_cada24;

function EvidenceRow({ label, value }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: "var(--space-md)",
        padding: "var(--space-sm) 0",
      }}
    >
      <MetaLabel>{label}</MetaLabel>
      <span
        style={{
          fontSize: "var(--type-data-sm-size)",
          color: "var(--text-body)",
          fontFeatureSettings: "var(--figures-tabular)",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function IncidentDetail({ incident, onBack, onApprove }) {
  const failed = incident.status === "failed";
  const inFlight = incident.status === "executing" || incident.status === "verifying";
  return (
    <div style={{ display: "grid", gap: "var(--space-md)" }}>
      <div style={{ padding: "0 var(--space-md)" }}>
        <span
          onClick={onBack}
          style={{
            fontFamily: "var(--font-pixel)",
            fontSize: "var(--type-label-caps-size)",
            letterSpacing: "var(--type-label-caps-tracking)",
            color: "var(--text-meta)",
            cursor: "pointer",
          }}
        >
          ← ALL INCIDENTS
        </span>
      </div>

      <Panel>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-lg)" }}>
          <div>
            <h1
              style={{
                margin: 0,
                fontSize: "var(--type-headline-size)",
                fontWeight: "var(--type-headline-weight)",
                lineHeight: "var(--type-headline-leading)",
                letterSpacing: "var(--type-headline-tracking)",
                color: "var(--text-body)",
              }}
            >
              {incident.title}
            </h1>
            <MetaLabel style={{ display: "block", marginTop: "var(--space-sm)" }}>
              {incident.id} · {incident.service} · opened {incident.opened}
            </MetaLabel>
          </div>
          <StatusBadge status={incident.status} />
        </div>

        <div style={{ marginTop: "var(--space-lg)" }}>
          <Stepper current={failed ? 4 : incident.step} failed={failed} labels={window.STEP_LABELS} />
        </div>
      </Panel>

      <Panel>
        <div style={{ display: "flex", gap: "var(--space-xl)", alignItems: "flex-end" }}>
          <DataReadout label="Confidence" value={incident.confidence} />
          <div style={{ paddingBottom: "var(--space-xs)" }}>
            <MetaLabel variant="caps" style={{ display: "block", marginBottom: "var(--space-xs)" }}>
              {incident.metric.label}
            </MetaLabel>
            <Tooltip content={incident.metric.threshold}>
              <span
                style={{
                  fontSize: "var(--type-data-lg-size)",
                  color: failed ? "var(--signal-warning)" : "var(--text-body)",
                  fontFeatureSettings: "var(--figures-tabular)",
                  borderBottom: "var(--hairline) solid var(--rule-hairline)",
                }}
              >
                {incident.metric.value}
              </span>
            </Tooltip>
          </div>
        </div>
      </Panel>

      <Panel label="Root cause">
        <p style={{ margin: 0, maxWidth: "var(--measure)", textWrap: "pretty" }}>{incident.cause}</p>
        <Divider style={{ margin: "var(--space-lg) 0 var(--space-sm)" }} />
        <MetaLabel variant="caps" style={{ display: "block", margin: "var(--space-md) 0 var(--space-xs)" }}>
          Evidence
        </MetaLabel>
        {incident.evidence.map(([label, value], i) => (
          <React.Fragment key={label}>
            <EvidenceRow label={label} value={value} />
            {i < incident.evidence.length - 1 && <Divider />}
          </React.Fragment>
        ))}
      </Panel>

      <Panel label="Remediation">
        <p style={{ margin: 0, maxWidth: "var(--measure)", textWrap: "pretty" }}>{incident.remediation}</p>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-md)",
            marginTop: "var(--space-lg)",
          }}
        >
          {incident.status === "pending_approval" && (
            <ApproveButton onClick={onApprove}>APPROVE RESTART</ApproveButton>
          )}
          {inFlight && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "var(--space-sm)",
                color: "var(--signal-caution)",
                fontSize: "var(--type-data-sm-size)",
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: 6,
                  height: 6,
                  background: "var(--signal-caution)",
                  animation: "annunciator-pulse var(--pulse-duration) var(--pulse-easing) infinite",
                }}
              />
              {incident.status === "executing" ? "restarting…" : "verifying…"}
            </span>
          )}
          {incident.status === "resolved" && (
            <MetaLabel>Verified healthy at {incident.updated}.</MetaLabel>
          )}
          {failed && (
            <MetaLabel style={{ color: "var(--signal-warning)" }}>
              Health did not recover after restart.
            </MetaLabel>
          )}
        </div>
      </Panel>
    </div>
  );
}

Object.assign(window, { IncidentDetail, EvidenceRow });
