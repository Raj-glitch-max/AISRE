/* @ds-bundle: {"format":4,"namespace":"AnnunciatorAISREDesignSystem_cada24","components":[{"name":"ApproveButton","sourcePath":"components/controls/ApproveButton.jsx"},{"name":"Tooltip","sourcePath":"components/controls/Tooltip.jsx"},{"name":"DataReadout","sourcePath":"components/readout/DataReadout.jsx"},{"name":"MetaLabel","sourcePath":"components/readout/MetaLabel.jsx"},{"name":"StatusBadge","sourcePath":"components/status/StatusBadge.jsx"},{"name":"Stepper","sourcePath":"components/status/Stepper.jsx"},{"name":"Divider","sourcePath":"components/surface/Divider.jsx"},{"name":"Panel","sourcePath":"components/surface/Panel.jsx"}],"sourceHashes":{"components/controls/ApproveButton.jsx":"3b368b87ed8e","components/controls/Tooltip.jsx":"361c0bb9c722","components/readout/DataReadout.jsx":"01dbcde154f0","components/readout/MetaLabel.jsx":"c4097ddcb9dd","components/status/StatusBadge.jsx":"019071818546","components/status/Stepper.jsx":"e3ab20fc240e","components/surface/Divider.jsx":"bade154251a5","components/surface/Panel.jsx":"ff909487b8a2","ui_kits/incident-dashboard/IncidentDetail.jsx":"a1cce9a88972","ui_kits/incident-dashboard/IncidentList.jsx":"85611e93d945","ui_kits/incident-dashboard/data.js":"64cb459b6958"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.AnnunciatorAISREDesignSystem_cada24 = window.AnnunciatorAISREDesignSystem_cada24 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/controls/ApproveButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* The only button in the system. If a screen needs a second one,
   the screen is doing too much. Light text on amber fails 1.61:1 — never. */
function ApproveButton({
  children = "APPROVE",
  disabled = false,
  onClick,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", _extends({}, rest, {
    type: "button",
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      appearance: "none",
      border: 0,
      borderRadius: 0,
      cursor: disabled ? "default" : "pointer",
      background: disabled ? "var(--surface-float)" : hover ? "var(--action-fill-hover)" : "var(--action-fill)",
      color: disabled ? "var(--text-meta)" : "var(--action-ink)",
      fontFamily: "var(--type-label-caps-family)",
      fontSize: "var(--type-label-caps-size)",
      fontWeight: 700,
      lineHeight: "var(--type-label-caps-leading)",
      letterSpacing: "var(--type-label-caps-tracking)",
      padding: "var(--space-md)",
      transition: "none",
      transform: "none",
      boxShadow: "none",
      ...style
    }
  }), children);
}
Object.assign(__ds_scope, { ApproveButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/controls/ApproveButton.jsx", error: String((e && e.message) || e) }); }

// components/controls/Tooltip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* The one surface a full step brighter than Panel — the only genuinely
   floating context in the system. */
function Tooltip({
  content,
  placement = "top",
  children,
  style,
  ...rest
}) {
  const [open, setOpen] = React.useState(false);
  const offset = placement === "bottom" ? {
    top: "100%",
    marginTop: "var(--space-xs)"
  } : {
    bottom: "100%",
    marginBottom: "var(--space-xs)"
  };
  return /*#__PURE__*/React.createElement("span", _extends({}, rest, {
    style: {
      position: "relative",
      display: "inline-flex",
      ...style
    },
    onMouseEnter: () => setOpen(true),
    onMouseLeave: () => setOpen(false),
    onFocus: () => setOpen(true),
    onBlur: () => setOpen(false)
  }), children, open && /*#__PURE__*/React.createElement("span", {
    role: "tooltip",
    style: {
      position: "absolute",
      left: 0,
      ...offset,
      zIndex: 20,
      whiteSpace: "nowrap",
      background: "var(--surface-float)",
      color: "var(--text-body)",
      fontFamily: "var(--type-data-sm-family)",
      fontSize: "var(--type-data-sm-size)",
      lineHeight: "var(--type-data-sm-leading)",
      fontFeatureSettings: "var(--figures-tabular)",
      padding: "var(--space-sm)",
      borderRadius: 0,
      boxShadow: "none"
    }
  }, content));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/controls/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/readout/DataReadout.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* The confidence percentage. Set like a gauge value, not a heading. */
function DataReadout({
  value,
  unit = "%",
  label,
  align = "left",
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({}, rest, {
    style: {
      textAlign: align,
      ...style
    }
  }), label && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--type-label-caps-family)",
      fontSize: "var(--type-label-caps-size)",
      lineHeight: "var(--type-label-caps-leading)",
      letterSpacing: "var(--type-label-caps-tracking)",
      color: "var(--text-meta)",
      textTransform: "uppercase",
      marginBottom: "var(--space-sm)"
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--type-display-family)",
      fontSize: "var(--type-display-size)",
      fontWeight: "var(--type-display-weight)",
      lineHeight: "var(--type-display-leading)",
      letterSpacing: "var(--type-display-tracking)",
      fontFeatureSettings: "var(--figures-tabular)",
      color: "var(--text-body)"
    }
  }, value, unit && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: "0.5em",
      marginLeft: "0.12em",
      color: "var(--text-meta)"
    }
  }, unit)));
}
Object.assign(__ds_scope, { DataReadout });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/readout/DataReadout.jsx", error: String((e && e.message) || e) }); }

// components/readout/MetaLabel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Incident IDs, service names, timestamps. Never a signal color.
   variant="caps" is the label-caps role: Departure Mono, +0.15em, uppercase.
   Keep caps labels to roughly ten characters — the pixel face stops being
   legible past that, so anything longer must stay on the body face. */
function MetaLabel({
  children,
  size = "sm",
  variant = "meta",
  uppercase = false,
  as = "span",
  style,
  ...rest
}) {
  const Tag = as;
  const caps = variant === "caps";
  const s = caps ? "label-caps" : size === "caption" ? "caption" : "data-sm";
  return /*#__PURE__*/React.createElement(Tag, _extends({}, rest, {
    style: {
      fontFamily: "var(--type-" + s + "-family)",
      fontSize: "var(--type-" + s + "-size)",
      fontWeight: "var(--type-" + s + "-weight)",
      lineHeight: "var(--type-" + s + "-leading)",
      letterSpacing: "var(--type-" + s + "-tracking)",
      fontFeatureSettings: caps ? "normal" : "var(--figures-tabular)",
      color: "var(--text-meta)",
      textTransform: caps || uppercase ? "uppercase" : "none",
      ...style
    }
  }), children);
}
Object.assign(__ds_scope, { MetaLabel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/readout/MetaLabel.jsx", error: String((e && e.message) || e) }); }

// components/status/StatusBadge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const STATUS = {
  open: {
    variant: "caution",
    label: "OPEN"
  },
  investigating: {
    variant: "caution",
    label: "INVESTIGATING"
  },
  pending_approval: {
    variant: "caution",
    label: "AWAITING",
    pulse: true
  },
  executing: {
    variant: "caution",
    label: "EXECUTING",
    dot: true
  },
  verifying: {
    variant: "caution",
    label: "VERIFYING",
    dot: true
  },
  resolved: {
    variant: "nominal",
    label: "RESOLVED"
  },
  failed: {
    variant: "warning",
    label: "FAILED"
  }
};
const INK = {
  nominal: "var(--signal-nominal)",
  caution: "var(--signal-caution)",
  warning: "var(--signal-warning)"
};

/* Never a filled pill — the signal color is the text, the way a lamp's own
   color is the readout. The status word is load-bearing, not decorative. */
function StatusBadge({
  status,
  variant,
  label,
  on = "panel",
  style,
  ...rest
}) {
  const spec = status && STATUS[status] || {};
  const tone = variant || spec.variant || "caution";
  const word = label || spec.label || "UNKNOWN";
  return /*#__PURE__*/React.createElement("span", _extends({}, rest, {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: "var(--space-xs)",
      background: on === "page" ? "var(--surface-page)" : "var(--surface-panel)",
      color: INK[tone],
      fontFamily: "var(--type-label-caps-family)",
      fontSize: "var(--type-label-caps-size)",
      lineHeight: "var(--type-label-caps-leading)",
      letterSpacing: "var(--type-label-caps-tracking)",
      padding: "var(--space-xs)",
      borderRadius: 0,
      animation: spec.pulse ? "annunciator-pulse var(--pulse-duration) var(--pulse-easing) infinite" : "none",
      ...style
    }
  }), spec.dot && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      width: 6,
      height: 6,
      background: INK[tone],
      animation: "annunciator-pulse var(--pulse-duration) var(--pulse-easing) infinite"
    }
  }), word);
}
Object.assign(__ds_scope, { StatusBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/StatusBadge.jsx", error: String((e && e.message) || e) }); }

// components/status/Stepper.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const FILL = {
  done: "var(--signal-nominal)",
  current: "var(--signal-caution)",
  failed: "var(--signal-warning)",
  future: "var(--signal-inert)"
};

/* Six flush segments reading as one bar with a state boundary in it.
   A failed run replaces every remaining segment with a single red one. */
function Stepper({
  steps,
  count = 6,
  current = 0,
  failed = false,
  labels = [],
  style,
  ...rest
}) {
  let cells;
  if (steps && steps.length) {
    cells = steps.map(s => ({
      state: s,
      span: 1
    }));
  } else if (failed) {
    cells = [];
    for (let i = 0; i < current; i++) cells.push({
      state: "done",
      span: 1
    });
    cells.push({
      state: "failed",
      span: Math.max(1, count - current)
    });
  } else {
    cells = Array.from({
      length: count
    }, (_, i) => ({
      state: i < current ? "done" : i === current ? "current" : "future",
      span: 1
    }));
  }
  return /*#__PURE__*/React.createElement("div", _extends({}, rest, {
    style: style
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "var(--space-xs)",
      alignItems: "stretch"
    }
  }, cells.map((c, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: c.span,
      height: "var(--stepper-height)",
      background: FILL[c.state] || FILL.future
    }
  }))), labels.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      marginTop: "var(--space-sm)"
    }
  }, labels.map((l, i) => /*#__PURE__*/React.createElement("span", {
    key: l,
    style: {
      fontFamily: "var(--type-caption-family)",
      fontSize: "var(--type-caption-size)",
      lineHeight: "var(--type-caption-leading)",
      letterSpacing: "var(--type-caption-tracking)",
      color: i === current ? failed ? "var(--signal-warning)" : "var(--signal-caution)" : "var(--text-meta)"
    }
  }, l))));
}
Object.assign(__ds_scope, { Stepper });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/Stepper.jsx", error: String((e && e.message) || e) }); }

// components/surface/Divider.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* A 1px rule. Never a box — this system has no bordered containers. */
function Divider({
  inset = 0,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({}, rest, {
    role: "separator",
    style: {
      height: "var(--hairline)",
      background: "var(--rule-hairline)",
      marginLeft: inset,
      marginRight: inset,
      border: 0,
      ...style
    }
  }));
}
Object.assign(__ds_scope, { Divider });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surface/Divider.jsx", error: String((e && e.message) || e) }); }

// components/surface/Panel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* A panel sits on the page the way an instrument face sits in a console:
   a distinct material, never an object floating above one. No shadow, ever. */
function Panel({
  as = "section",
  label,
  actions,
  flush = false,
  children,
  style,
  ...rest
}) {
  const Tag = as;
  return /*#__PURE__*/React.createElement(Tag, _extends({}, rest, {
    style: {
      background: "var(--surface-panel)",
      color: "var(--text-body)",
      fontFamily: "var(--type-body-md-family)",
      fontSize: "var(--type-body-md-size)",
      lineHeight: "var(--type-body-md-leading)",
      fontFeatureSettings: "var(--figures-tabular)",
      padding: flush ? 0 : "var(--space-lg)",
      borderRadius: 0,
      boxShadow: "none",
      ...style
    }
  }), (label || actions) && /*#__PURE__*/React.createElement("header", {
    style: {
      display: "flex",
      alignItems: "baseline",
      justifyContent: "space-between",
      gap: "var(--space-md)",
      marginBottom: "var(--space-md)",
      padding: flush ? "var(--space-lg) var(--space-lg) 0" : 0
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style:
    /* Departure Mono stops being legible past ~10 characters, so a
       long label stays on the body face rather than costing
       readability for costume. */
    typeof label === "string" && label.length > 11 ? {
      fontFamily: "var(--type-data-sm-family)",
      fontSize: "var(--type-data-sm-size)",
      lineHeight: "var(--type-data-sm-leading)",
      letterSpacing: "0.08em",
      color: "var(--text-meta)",
      textTransform: "uppercase"
    } : {
      fontFamily: "var(--type-label-caps-family)",
      fontSize: "var(--type-label-caps-size)",
      lineHeight: "var(--type-label-caps-leading)",
      letterSpacing: "var(--type-label-caps-tracking)",
      color: "var(--text-meta)",
      textTransform: "uppercase"
    }
  }, label), actions), children);
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surface/Panel.jsx", error: String((e && e.message) || e) }); }

// ui_kits/incident-dashboard/IncidentDetail.jsx
try { (() => {
const {
  Panel,
  Divider,
  StatusBadge,
  Stepper,
  DataReadout,
  MetaLabel,
  ApproveButton,
  Tooltip
} = window.AnnunciatorAISREDesignSystem_cada24;
function EvidenceRow({
  label,
  value
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr auto",
      gap: "var(--space-md)",
      padding: "var(--space-sm) 0"
    }
  }, /*#__PURE__*/React.createElement(MetaLabel, null, label), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: "var(--type-data-sm-size)",
      color: "var(--text-body)",
      fontFeatureSettings: "var(--figures-tabular)"
    }
  }, value));
}
function IncidentDetail({
  incident,
  onBack,
  onApprove
}) {
  const failed = incident.status === "failed";
  const inFlight = incident.status === "executing" || incident.status === "verifying";
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gap: "var(--space-md)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "0 var(--space-md)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    onClick: onBack,
    style: {
      fontFamily: "var(--font-pixel)",
      fontSize: "var(--type-label-caps-size)",
      letterSpacing: "var(--type-label-caps-tracking)",
      color: "var(--text-meta)",
      cursor: "pointer"
    }
  }, "\u2190 ALL INCIDENTS")), /*#__PURE__*/React.createElement(Panel, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-start",
      gap: "var(--space-lg)"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: "var(--type-headline-size)",
      fontWeight: "var(--type-headline-weight)",
      lineHeight: "var(--type-headline-leading)",
      letterSpacing: "var(--type-headline-tracking)",
      color: "var(--text-body)"
    }
  }, incident.title), /*#__PURE__*/React.createElement(MetaLabel, {
    style: {
      display: "block",
      marginTop: "var(--space-sm)"
    }
  }, incident.id, " \xB7 ", incident.service, " \xB7 opened ", incident.opened)), /*#__PURE__*/React.createElement(StatusBadge, {
    status: incident.status
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: "var(--space-lg)"
    }
  }, /*#__PURE__*/React.createElement(Stepper, {
    current: failed ? 4 : incident.step,
    failed: failed,
    labels: window.STEP_LABELS
  }))), /*#__PURE__*/React.createElement(Panel, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "var(--space-xl)",
      alignItems: "flex-end"
    }
  }, /*#__PURE__*/React.createElement(DataReadout, {
    label: "Confidence",
    value: incident.confidence
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      paddingBottom: "var(--space-xs)"
    }
  }, /*#__PURE__*/React.createElement(MetaLabel, {
    variant: "caps",
    style: {
      display: "block",
      marginBottom: "var(--space-xs)"
    }
  }, incident.metric.label), /*#__PURE__*/React.createElement(Tooltip, {
    content: incident.metric.threshold
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: "var(--type-data-lg-size)",
      color: failed ? "var(--signal-warning)" : "var(--text-body)",
      fontFeatureSettings: "var(--figures-tabular)",
      borderBottom: "var(--hairline) solid var(--rule-hairline)"
    }
  }, incident.metric.value))))), /*#__PURE__*/React.createElement(Panel, {
    label: "Root cause"
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      maxWidth: "var(--measure)",
      textWrap: "pretty"
    }
  }, incident.cause), /*#__PURE__*/React.createElement(Divider, {
    style: {
      margin: "var(--space-lg) 0 var(--space-sm)"
    }
  }), /*#__PURE__*/React.createElement(MetaLabel, {
    variant: "caps",
    style: {
      display: "block",
      margin: "var(--space-md) 0 var(--space-xs)"
    }
  }, "Evidence"), incident.evidence.map(([label, value], i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: label
  }, /*#__PURE__*/React.createElement(EvidenceRow, {
    label: label,
    value: value
  }), i < incident.evidence.length - 1 && /*#__PURE__*/React.createElement(Divider, null)))), /*#__PURE__*/React.createElement(Panel, {
    label: "Remediation"
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      maxWidth: "var(--measure)",
      textWrap: "pretty"
    }
  }, incident.remediation), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: "var(--space-md)",
      marginTop: "var(--space-lg)"
    }
  }, incident.status === "pending_approval" && /*#__PURE__*/React.createElement(ApproveButton, {
    onClick: onApprove
  }, "APPROVE RESTART"), inFlight && /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: "var(--space-sm)",
      color: "var(--signal-caution)",
      fontSize: "var(--type-data-sm-size)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      width: 6,
      height: 6,
      background: "var(--signal-caution)",
      animation: "annunciator-pulse var(--pulse-duration) var(--pulse-easing) infinite"
    }
  }), incident.status === "executing" ? "restarting…" : "verifying…"), incident.status === "resolved" && /*#__PURE__*/React.createElement(MetaLabel, null, "Verified healthy at ", incident.updated, "."), failed && /*#__PURE__*/React.createElement(MetaLabel, {
    style: {
      color: "var(--signal-warning)"
    }
  }, "Health did not recover after restart."))));
}
Object.assign(window, {
  IncidentDetail,
  EvidenceRow
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/incident-dashboard/IncidentDetail.jsx", error: String((e && e.message) || e) }); }

// ui_kits/incident-dashboard/IncidentList.jsx
try { (() => {
const {
  Panel,
  Divider,
  StatusBadge,
  MetaLabel
} = window.AnnunciatorAISREDesignSystem_cada24;
function IncidentRow({
  incident,
  onOpen
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    onClick: () => onOpen(incident.id),
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: "grid",
      gridTemplateColumns: "92px 1fr 132px",
      alignItems: "center",
      gap: "var(--space-md)",
      padding: "var(--space-sm) var(--space-md)",
      background: hover ? "var(--surface-row-hover)" : "var(--surface-page)",
      cursor: "pointer",
      transition: "none"
    }
  }, /*#__PURE__*/React.createElement(MetaLabel, null, incident.id), /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: "var(--type-body-md-size)",
      color: "var(--text-body)",
      lineHeight: 1.3
    }
  }, incident.title), /*#__PURE__*/React.createElement(MetaLabel, {
    size: "caption",
    style: {
      display: "block",
      marginTop: 2
    }
  }, incident.service, " \xB7 ", incident.updated)), /*#__PURE__*/React.createElement(StatusBadge, {
    status: incident.status,
    on: hover ? "panel" : "page",
    style: {
      justifySelf: "end"
    }
  }));
}
function IncidentList({
  incidents,
  onOpen
}) {
  const awaiting = incidents.filter(i => i.status === "pending_approval").length;
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "baseline",
      justifyContent: "space-between",
      padding: "0 var(--space-md) var(--space-md)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "baseline",
      gap: "var(--space-sm)"
    }
  }, /*#__PURE__*/React.createElement(MetaLabel, {
    variant: "caps"
  }, "Incidents"), /*#__PURE__*/React.createElement(MetaLabel, null, incidents.length, " active")), awaiting > 0 && /*#__PURE__*/React.createElement(StatusBadge, {
    variant: "caution",
    label: awaiting + " AWAITING",
    on: "page"
  })), /*#__PURE__*/React.createElement(Divider, null), incidents.map((incident, i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: incident.id
  }, /*#__PURE__*/React.createElement(IncidentRow, {
    incident: incident,
    onOpen: onOpen
  }), i < incidents.length - 1 && /*#__PURE__*/React.createElement(Divider, null))), /*#__PURE__*/React.createElement(Divider, null));
}
Object.assign(window, {
  IncidentList,
  IncidentRow
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/incident-dashboard/IncidentList.jsx", error: String((e && e.message) || e) }); }

// ui_kits/incident-dashboard/data.js
try { (() => {
const INCIDENTS = [{
  id: "INC-4471",
  service: "checkout-api",
  title: "Checkout latency regression",
  status: "pending_approval",
  opened: "14:01:07 UTC",
  updated: "14:02:18 UTC",
  confidence: 94,
  step: 3,
  metric: {
    label: "p95 latency",
    value: "2,410 ms",
    threshold: "threshold 800 ms"
  },
  cause: "The connection pool on checkout-api saturated at 14:01 UTC after deploy 8f31c raised per-request pool checkout from one connection to three. Latency crossed the p95 threshold ninety seconds later.",
  evidence: [["pool.active / pool.max", "48 / 48 for 214 s"], ["deploy 8f31c", "merged 13:57:40 UTC"], ["upstream auth-gateway", "nominal, 41 ms p95"], ["error rate", "0.4% — no 5xx spike"]],
  remediation: "Roll back deploy 8f31c and restart the checkout-api pool (3 replicas, rolling)."
}, {
  id: "INC-4470",
  service: "auth-gateway",
  title: "Token refresh backlog",
  status: "verifying",
  opened: "13:44:52 UTC",
  updated: "14:00:02 UTC",
  confidence: 88,
  step: 5,
  metric: {
    label: "queue depth",
    value: "1,118",
    threshold: "threshold 400"
  },
  cause: "Token refresh workers fell behind after a Redis failover at 13:44 UTC. The backlog drained once workers reconnected; verification is confirming queue depth stays under threshold for five minutes.",
  evidence: [["redis failover", "13:44:41 UTC"], ["worker reconnects", "6 / 6 healthy"], ["queue depth", "1,118 → 62"]],
  remediation: "Restart the refresh worker deployment (6 replicas)."
}, {
  id: "INC-4468",
  service: "ledger-worker",
  title: "Duplicate settlement writes",
  status: "failed",
  opened: "11:20:14 UTC",
  updated: "11:38:57 UTC",
  confidence: 41,
  step: 4,
  metric: {
    label: "dup writes",
    value: "37",
    threshold: "threshold 0"
  },
  cause: "Idempotency keys collided across two ledger-worker replicas. A rolling restart was approved and executed, but duplicate writes resumed within ninety seconds — health did not recover.",
  evidence: [["duplicate writes", "37 after restart"], ["restart", "completed 11:36:12 UTC"], ["idempotency cache", "hit rate 12%"]],
  remediation: "Roll restart ledger-worker (2 replicas)."
}, {
  id: "INC-4465",
  service: "search-indexer",
  title: "Index lag on shard 3",
  status: "resolved",
  opened: "09:02:31 UTC",
  updated: "09:19:08 UTC",
  confidence: 97,
  step: 6,
  metric: {
    label: "index lag",
    value: "911 s",
    threshold: "threshold 120 s"
  },
  cause: "Shard 3 fell behind after a node eviction. A single replica restart cleared the lag and index freshness returned to under twenty seconds.",
  evidence: [["node eviction", "09:01:55 UTC"], ["index lag", "911 s → 18 s"], ["shards", "4 / 4 nominal"]],
  remediation: "Restart the shard-3 indexer replica."
}, {
  id: "INC-4462",
  service: "notify-fanout",
  title: "Webhook retry storm",
  status: "investigating",
  opened: "08:41:09 UTC",
  updated: "08:44:30 UTC",
  confidence: 62,
  step: 1,
  metric: {
    label: "retries/min",
    value: "8,204",
    threshold: "threshold 1,000"
  },
  cause: "Retry volume to a single downstream endpoint is climbing. The agent is still correlating the spike against the endpoint's response codes; no verdict yet.",
  evidence: [["retries / min", "8,204 and rising"], ["downstream 4xx", "under review"]],
  remediation: "Pending — no remediation proposed yet."
}];
const STEP_LABELS = ["DETECT", "TRIAGE", "DIAGNOSE", "APPROVE", "EXECUTE", "VERIFY"];
Object.assign(window, {
  INCIDENTS,
  STEP_LABELS
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/incident-dashboard/data.js", error: String((e && e.message) || e) }); }

__ds_ns.ApproveButton = __ds_scope.ApproveButton;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.DataReadout = __ds_scope.DataReadout;

__ds_ns.MetaLabel = __ds_scope.MetaLabel;

__ds_ns.StatusBadge = __ds_scope.StatusBadge;

__ds_ns.Stepper = __ds_scope.Stepper;

__ds_ns.Divider = __ds_scope.Divider;

__ds_ns.Panel = __ds_scope.Panel;

})();
