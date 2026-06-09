import { useState, useRef, useCallback } from "react";
 
const API = "http://127.0.0.1:8000";
 
const LEGEND = [
  { label: "Aligns with Standard",    color: "#2d6a4f", desc: "Clause aligns with UoA standard position",         bg: "#f0faf5", border: "#a8d5b5" },
  { label: "Partial Alignment",       color: "#7d5a00", desc: "Partial match — review recommended",               bg: "#fffbeb", border: "#f5d87a" },
  { label: "Conflicts with Standard", color: "#9b2335", desc: "Conflicts with UoA standard — action required",    bg: "#fff5f5", border: "#f5b8be" },
  { label: "Requires Assessment",     color: "#1a3f6f", desc: "Not addressed in current UoA standard positions",  bg: "#f0f6ff", border: "#a8c4e8" },
];
 
const STEPS = [
  { id: "idle",       icon: "01", label: "Upload PDF"  },
  { id: "uploading",  icon: "02", label: "Uploading"   },
  { id: "processing", icon: "03", label: "Processing"  },
  { id: "done",       icon: "04", label: "Complete"    },
];
 
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@300;400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
 
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
 
  body {
    background: #f7f5f0;
    color: #1a1a1a;
    font-family: 'IBM Plex Sans', sans-serif;
    min-height: 100vh;
  }
 
  .pdf-app {
    min-height: 100vh;
    background: #f7f5f0;
    position: relative;
  }
 
  /* ── Top bar ── */
  .topbar {
    background: #fff;
    border-bottom: 1px solid #e8e3d8;
    padding: 0 2rem;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
  }
 
  .topbar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }
 
  .topbar-logo {
    width: 28px;
    height: 28px;
    background: #1a3f6f;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: -.02em;
    flex-shrink: 0;
  }
 
  .topbar-name {
    font-size: 13px;
    font-weight: 500;
    color: #1a1a1a;
    letter-spacing: .01em;
  }
 
  .topbar-tag {
    font-size: 10px;
    font-family: 'IBM Plex Mono', monospace;
    background: #eef3fb;
    color: #1a3f6f;
    border: 1px solid #c2d4ef;
    border-radius: 99px;
    padding: 2px 9px;
    letter-spacing: .06em;
    text-transform: uppercase;
  }
 
  /* ── Layout ── */
  .container {
    max-width: 900px;
    margin: 0 auto;
    padding: 3rem 2rem 5rem;
  }
 
  /* ── Hero ── */
  .hero {
    margin-bottom: 2.75rem;
    padding-bottom: 2.25rem;
    border-bottom: 1px solid #e0dbd0;
  }
 
  .hero-kicker {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: .18em;
    text-transform: uppercase;
    color: #7d5a00;
    margin-bottom: 1.1rem;
  }
 
  .hero-kicker-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #7d5a00;
  }
 
  .hero-title {
    font-family: 'Lora', serif;
    font-size: clamp(1.7rem, 4vw, 2.5rem);
    font-weight: 600;
    line-height: 1.15;
    color: #111;
    margin-bottom: .65rem;
    letter-spacing: -.02em;
  }
 
  .hero-title em {
    font-style: italic;
    font-weight: 400;
    color: #1a3f6f;
  }
 
  .hero-sub {
    font-size: 13px;
    color: #6b6560;
    line-height: 1.7;
    max-width: 520px;
  }
 
  /* ── Section label ── */
  .section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    letter-spacing: .22em;
    text-transform: uppercase;
    color: #9e9890;
    margin-bottom: .85rem;
  }
 
  /* ── Legend ── */
  .legend-section { margin-bottom: 2.25rem; }
 
  .legend-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 8px;
  }
 
  .legend-card {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 11px 14px;
    border-radius: 6px;
    border: 1px solid transparent;
    cursor: default;
    user-select: none;
    transition: transform .15s, box-shadow .15s;
  }
 
  .legend-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 3px 12px rgba(0,0,0,.07);
  }
 
  .legend-card-bar {
    width: 3px;
    border-radius: 99px;
    flex-shrink: 0;
    align-self: stretch;
    min-height: 32px;
  }
 
  .legend-card-body { flex: 1; min-width: 0; }
 
  .legend-card-label {
    font-size: 11.5px;
    font-weight: 500;
    line-height: 1.3;
    margin-bottom: 2px;
  }
 
  .legend-card-desc {
    font-size: 10.5px;
    line-height: 1.5;
    opacity: .7;
  }
 
  .legend-tooltip {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: #1a1a1a;
    color: #f0ede8;
    border-radius: 5px;
    padding: 7px 11px;
    font-size: 10.5px;
    white-space: nowrap;
    pointer-events: none;
    z-index: 30;
    font-family: 'IBM Plex Sans', sans-serif;
    box-shadow: 0 4px 16px rgba(0,0,0,.18);
  }
 
  .legend-tooltip::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 5px solid transparent;
    border-top-color: #1a1a1a;
  }
 
  /* ── Step tracker ── */
  .step-tracker {
    display: flex;
    align-items: center;
    margin-bottom: 1.75rem;
    background: #fff;
    border: 1px solid #e0dbd0;
    border-radius: 8px;
    padding: 14px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.04);
  }
 
  .step-item {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 0;
  }
 
  .step-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 500;
    letter-spacing: .06em;
    min-width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    flex-shrink: 0;
    transition: all .25s;
  }
 
  .step-badge.active  { background: #1a3f6f; color: #fff; }
  .step-badge.done    { background: #e8f5ee; color: #2d6a4f; }
  .step-badge.inactive{ background: #f0ede8; color: #b0a898; }
 
  .step-text {
    font-size: 11px;
    letter-spacing: .05em;
    text-transform: uppercase;
    font-family: 'IBM Plex Mono', monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: color .25s;
  }
 
  .step-text.active   { color: #1a1a1a; font-weight: 500; }
  .step-text.done     { color: #2d6a4f; }
  .step-text.inactive { color: #c0b8ad; }
 
  .step-line {
    flex: 1;
    height: 1px;
    background: #e8e3d8;
    margin: 0 8px;
    min-width: 12px;
  }
 
  /* ── Drop zone ── */
  .drop-zone {
    border: 1.5px dashed #d4cfc5;
    border-radius: 10px;
    padding: 60px 40px;
    text-align: center;
    cursor: pointer;
    transition: all .2s;
    background: #fff;
    position: relative;
    overflow: hidden;
  }
 
  .drop-zone:hover {
    border-color: #1a3f6f;
    background: #f5f8fd;
  }
 
  .drop-zone.dragging {
    border-color: #1a3f6f;
    background: #eef3fb;
  }
 
  .drop-zone.disabled { cursor: not-allowed; opacity: .5; }
 
  .drop-zone-inner { position: relative; z-index: 1; }
 
  .drop-file-icon {
    width: 64px;
    height: 72px;
    margin: 0 auto 1.5rem;
    position: relative;
  }
 
  .drop-file-page {
    width: 100%;
    height: 100%;
    background: #f0ede8;
    border-radius: 6px;
    border: 1.5px solid #d4cfc5;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    transition: all .2s;
  }
 
  .drop-zone:hover .drop-file-page,
  .drop-zone.dragging .drop-file-page {
    background: #dce8f7;
    border-color: #7da8d8;
  }
 
  .drop-file-line {
    width: 32px;
    height: 2.5px;
    border-radius: 99px;
    background: #c0b8ad;
    transition: background .2s;
  }
 
  .drop-zone:hover .drop-file-line,
  .drop-zone.dragging .drop-file-line { background: #7da8d8; }
 
  .drop-file-line.short { width: 20px; }
 
  .drop-corner {
    position: absolute;
    top: 0;
    right: 0;
    width: 18px;
    height: 18px;
    background: #fff;
    border-bottom-left-radius: 4px;
    border-left: 1.5px solid #d4cfc5;
    border-bottom: 1.5px solid #d4cfc5;
    transition: border-color .2s;
  }
 
  .drop-zone:hover .drop-corner,
  .drop-zone.dragging .drop-corner { border-color: #7da8d8; }
 
  .drop-title {
    font-family: 'Lora', serif;
    font-size: 18px;
    font-weight: 400;
    color: #1a1a1a;
    margin-bottom: .4rem;
  }
 
  .drop-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #9e9890;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
 
  .drop-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 1.25rem;
    padding: 9px 20px;
    border-radius: 5px;
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    letter-spacing: .1em;
    text-transform: uppercase;
    background: #1a3f6f;
    color: #fff;
    border: none;
    cursor: pointer;
    transition: background .2s;
  }
 
  .drop-btn:hover { background: #153459; }
 
  /* ── Progress card ── */
  .progress-card {
    background: #fff;
    border: 1px solid #e0dbd0;
    border-radius: 10px;
    padding: 28px 28px 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,.04);
  }
 
  .progress-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 18px;
  }
 
  .progress-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: .15em;
    text-transform: uppercase;
    color: #6b6560;
    margin-bottom: 4px;
  }
 
  .progress-file {
    font-family: 'Lora', serif;
    font-size: 15px;
    color: #1a1a1a;
    font-weight: 400;
  }
 
  .progress-pct {
    font-family: 'Lora', serif;
    font-size: 36px;
    font-weight: 600;
    color: #1a3f6f;
    line-height: 1;
    letter-spacing: -.03em;
  }
 
  .progress-track {
    height: 3px;
    background: #ede9e0;
    border-radius: 99px;
    overflow: hidden;
  }
 
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #1a3f6f, #4a7cc7);
    transition: width .4s ease;
    border-radius: 99px;
  }
 
  .progress-status {
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #9e9890;
    letter-spacing: .06em;
  }
 
  .spinner {
    width: 12px;
    height: 12px;
    border: 1.5px solid #d4cfc5;
    border-top-color: #1a3f6f;
    border-radius: 50%;
    animation: spin .8s linear infinite;
    flex-shrink: 0;
  }
 
  @keyframes spin { to { transform: rotate(360deg); } }
 
  /* ── Done card ── */
  .done-card {
    background: #fff;
    border: 1px solid #b8ddc9;
    border-radius: 10px;
    padding: 24px 28px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.04);
  }
 
  .done-top {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 16px;
  }
 
  .done-check {
    width: 44px;
    height: 44px;
    border-radius: 8px;
    background: #e8f5ee;
    border: 1px solid #b8ddc9;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
 
  .done-check svg { width: 20px; height: 20px; }
 
  .done-title {
    font-family: 'Lora', serif;
    font-size: 19px;
    font-weight: 600;
    color: #111;
    margin-bottom: 4px;
  }
 
  .done-sub {
    font-size: 12px;
    color: #6b6560;
    line-height: 1.65;
  }
 
  .done-actions {
    display: flex;
    gap: 10px;
    margin-top: 16px;
    flex-wrap: wrap;
    align-items: center;
  }
 
  .btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 10px 22px;
    border-radius: 5px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: .12em;
    text-transform: uppercase;
    background: #1a3f6f;
    color: #fff;
    text-decoration: none;
    border: none;
    cursor: pointer;
    transition: background .2s;
  }
 
  .btn-primary:hover { background: #153459; }
 
  .btn-secondary {
    display: inline-flex;
    align-items: center;
    padding: 10px 22px;
    border-radius: 5px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: .12em;
    text-transform: uppercase;
    background: transparent;
    color: #6b6560;
    border: 1px solid #d4cfc5;
    cursor: pointer;
    transition: all .2s;
  }
 
  .btn-secondary:hover {
    border-color: #9e9890;
    color: #1a1a1a;
    background: #f7f5f0;
  }
 
  /* ── PDF Preview Panel ── */
  .preview-panel {
    margin-top: 20px;
    border: 1px solid #e0dbd0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,.06);
    animation: fadeSlideIn .35s ease both;
  }
 
  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }
 
  .preview-header {
    background: #fff;
    border-bottom: 1px solid #e0dbd0;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }
 
  .preview-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }
 
  .preview-header-icon {
    width: 28px;
    height: 28px;
    background: #eef3fb;
    border: 1px solid #c2d4ef;
    border-radius: 5px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
 
  .preview-header-icon svg { width: 14px; height: 14px; }
 
  .preview-header-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #1a3f6f;
    font-weight: 500;
  }
 
  .preview-header-file {
    font-size: 11px;
    color: #9e9890;
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 1px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 320px;
  }
 
  .preview-resize-bar {
    display: flex;
    align-items: center;
    gap: 6px;
  }
 
  .preview-resize-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 12px;
    border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    letter-spacing: .1em;
    text-transform: uppercase;
    border: 1px solid #e0dbd0;
    background: #f7f5f0;
    color: #6b6560;
    cursor: pointer;
    transition: all .15s;
    white-space: nowrap;
  }
 
  .preview-resize-btn:hover {
    border-color: #1a3f6f;
    color: #1a3f6f;
    background: #eef3fb;
  }
 
  .preview-resize-btn.active {
    border-color: #1a3f6f;
    background: #eef3fb;
    color: #1a3f6f;
  }
 
  .preview-body {
    background: #e8e3d8;
    transition: height .3s ease;
    position: relative;
  }
 
  .preview-iframe {
    width: 100%;
    height: 100%;
    display: block;
    border: none;
  }
 
  .preview-fallback {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 10px;
    padding: 40px;
    text-align: center;
  }
 
  .preview-fallback-text {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #6b6560;
    letter-spacing: .06em;
    line-height: 1.65;
  }
 
  /* ── Error ── */
  .error-banner {
    margin-top: 12px;
    padding: 14px 18px;
    border-radius: 7px;
    background: #fff8f8;
    border: 1px solid #f5b8be;
    font-size: 12px;
    color: #9b2335;
    line-height: 1.6;
  }
 
  /* ── How it works ── */
  .how-section {
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #e0dbd0;
  }
 
  .how-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1px;
    background: #e0dbd0;
    border: 1px solid #e0dbd0;
    border-radius: 8px;
    overflow: hidden;
    margin-top: 1rem;
  }
 
  .how-step {
    background: #fff;
    padding: 16px 18px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
 
  .how-num {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    color: #1a3f6f;
    letter-spacing: .08em;
    flex-shrink: 0;
    margin-top: 1px;
  }
 
  .how-text {
    font-size: 12px;
    color: #6b6560;
    line-height: 1.6;
  }
 
  /* ── Footer ── */
  .footer-note {
    margin-top: 3rem;
    padding: 14px 18px;
    border-radius: 7px;
    background: #fffbeb;
    border: 1px solid #f5d87a;
    font-size: 11.5px;
    color: #7d5a00;
    line-height: 1.6;
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }
 
  .footer-icon { font-size: 14px; flex-shrink: 0; margin-top: 1px; }
`;
 
function LegendCard({ color, label, desc, bg, border }) {
  const [show, setShow] = useState(false);
  return (
    <div
      className="legend-card"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      style={{ background: bg, borderColor: border }}
    >
      <div className="legend-card-bar" style={{ background: color }} />
      <div className="legend-card-body">
        <div className="legend-card-label" style={{ color }}>{label}</div>
        <div className="legend-card-desc" style={{ color }}>{desc}</div>
      </div>
      {show && <div className="legend-tooltip">{desc}</div>}
    </div>
  );
}
 
function DropZone({ onFile, disabled }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();
 
  const handleDrop = useCallback(e => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") onFile(f);
  }, [onFile]);
 
  const handleChange = e => {
    const f = e.target.files[0];
    if (f) onFile(f);
    e.target.value = "";
  };
 
  return (
    <div
      className={`drop-zone ${dragging ? "dragging" : ""} ${disabled ? "disabled" : ""}`}
      onClick={() => !disabled && inputRef.current.click()}
      onDragOver={e => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input ref={inputRef} type="file" accept=".pdf" style={{ display: "none" }} onChange={handleChange} />
      <div className="drop-zone-inner">
        <div className="drop-file-icon">
          <div className="drop-file-page">
            <div className="drop-file-line" />
            <div className="drop-file-line" />
            <div className="drop-file-line short" />
          </div>
          <div className="drop-corner" />
        </div>
        <p className="drop-title">Drop your contract PDF here</p>
        <p className="drop-sub">or click to browse · max 100 MB</p>
        <button className="drop-btn" tabIndex={-1}>
          <span>↑</span> Select PDF
        </button>
      </div>
    </div>
  );
}
 
function ProgressBar({ pct }) {
  return (
    <div className="progress-track">
      <div className="progress-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}
 
const PREVIEW_HEIGHTS = { compact: 480, standard: 720, full: 1020 };
 
function PdfPreview({ url, fileName }) {
  const [heightKey, setHeightKey] = useState("standard");
  const height = PREVIEW_HEIGHTS[heightKey];
 
  return (
    <div className="preview-panel">
      <div className="preview-header">
        <div className="preview-header-left">
          <div className="preview-header-icon">
            <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 2h7l3 3v9a1 1 0 01-1 1H3a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="#1a3f6f" strokeWidth="1.2" fill="none"/>
              <path d="M10 2v3h3" stroke="#1a3f6f" strokeWidth="1.2" strokeLinecap="round"/>
              <path d="M5 8h6M5 10.5h4" stroke="#1a3f6f" strokeWidth="1.2" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <div className="preview-header-title">Annotated PDF Preview</div>
            <div className="preview-header-file">{fileName}</div>
          </div>
        </div>
 
        <div className="preview-resize-bar">
          {Object.keys(PREVIEW_HEIGHTS).map(k => (
            <button
              key={k}
              className={`preview-resize-btn ${heightKey === k ? "active" : ""}`}
              onClick={() => setHeightKey(k)}
            >
              {k === "compact" ? "↕ Compact" : k === "standard" ? "↕ Standard" : "↕ Full"}
            </button>
          ))}
        </div>
      </div>
 
      <div className="preview-body" style={{ height }}>
        <iframe
          className="preview-iframe"
          src={`${url}#toolbar=1&navpanes=1&scrollbar=1&view=FitH`}
          title="Annotated PDF Preview"
          style={{ height }}
        />
      </div>
    </div>
  );
}
 
export default function App() {
  const [phase, setPhase] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [downloadName, setDownloadName] = useState("");
 
  const reset = () => {
    setPhase("idle"); setProgress(0); setError("");
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    setDownloadUrl(null);
  };
 
  const handleFile = async (file) => {
    setFileName(file.name);
    setError("");
    setDownloadUrl(null);
 
    // --- UPLOAD PHASE ---
    setPhase("uploading");
    let fakeP = 0;
    const ticker = setInterval(() => {
      fakeP = Math.min(fakeP + 6, 60);
      setProgress(fakeP);
    }, 120);
 
    let response;
    try {
      const fd = new FormData();
      fd.append("file", file);
      response = await fetch(`${API}/process-pdf`, { method: "POST", body: fd });
      clearInterval(ticker);
    } catch {
      clearInterval(ticker);
      setError("Cannot reach the FastAPI server. Make sure it is running on port 8000.");
      setPhase("error");
      return;
    }
 
    if (!response.ok) {
      const msg = await response.text().catch(() => "Unknown error");
      setError(`Server error: ${msg}`);
      setPhase("error");
      return;
    }
 
    // --- PROCESSING PHASE ---
    setPhase("processing");
    for (let p = 61; p <= 92; p += 4) {
      await new Promise(r => setTimeout(r, 90));
      setProgress(p);
    }
 
    const blob = await response.blob();
    setProgress(100);
 
    // --- DONE PHASE ---
    const url = URL.createObjectURL(blob);
    const outName = file.name.replace(/\.pdf$/i, "_highlighted.pdf");
    setDownloadUrl(url);
    setDownloadName(outName);
 
    setPhase("done");
  };
 
  const stepIndex = { idle: 0, uploading: 1, processing: 2, done: 3, error: 1 };
  const currentStep = stepIndex[phase] ?? 0;
 
  return (
    <>
      <style>{css}</style>
      <div className="pdf-app">
 
        {/* ── Top bar ── */}
        <div className="topbar">
          <div className="topbar-brand">
            <div className="topbar-logo">RGC</div>
            <span className="topbar-name">Research Contract Adviser</span>
          </div>
          <span className="topbar-tag">Proof of concept</span>
        </div>
 
        <div className="container">
 
          {/* ── Hero ── */}
          <header className="hero">
            <div className="hero-kicker" style={{ color: "#7d5a00", fontSize: 20}}>
              {/* <span className="hero-kicker-dot" /> */}
              University of Auckland - RGC Team
            </div>
            <h1 className="hero-title">
              Contract Clause <em>Review Tool</em>
            </h1>
            <h4>
              Upload a research contract PDF. The system scans every clause against UoA standard positions, applies colour-coded annotations, and returns a fully marked-up copy for review.
            </h4>
          </header>
 
          {/* ── Legend ── */}
          <div className="legend-section">
            <div className="section-label">Annotation categories</div>
            <div className="legend-grid">
              {LEGEND.map(l => <LegendCard key={l.label} {...l} />)}
            </div>
          </div>
 
          {/* ── Step Tracker ── */}
          <div className="step-tracker">
            {STEPS.map((s, i) => {
              const state = currentStep === i ? "active" : currentStep > i ? "done" : "inactive";
              return (
                <span key={s.id} style={{ display: "flex", alignItems: "center", flex: i < STEPS.length - 1 ? "1" : "none" }}>
                  <span className="step-item">
                    <span className={`step-badge ${state}`}>{currentStep > i ? "✓" : s.icon}</span>
                    <span className={`step-text ${state}`}>{s.label}</span>
                  </span>
                  {i < STEPS.length - 1 && <span className="step-line" />}
                </span>
              );
            })}
          </div>
 
          {/* ── Upload Zone ── */}
          {(phase === "idle" || phase === "error") && (
            <DropZone onFile={handleFile} disabled={false} />
          )}
 
          {/* ── Progress Card ── */}
          {(phase === "uploading" || phase === "processing") && (
            <div className="progress-card">
              <div className="progress-top">
                <div>
                  <div className="progress-label">
                    {phase === "uploading" ? "Uploading file" : "Applying annotations"}
                  </div>
                  <div className="progress-file">{fileName}</div>
                </div>
                <div className="progress-pct">{Math.round(progress)}%</div>
              </div>
              <ProgressBar pct={progress} />
              <div className="progress-status">
                <div className="spinner" />
                {phase === "uploading" ? "Sending to server…" : "Scanning clauses and applying highlights…"}
              </div>
            </div>
          )}
 
          {/* ── Done Card + Preview ── */}
          {phase === "done" && (
            <>
              <div className="done-card">
                <div className="done-top">
                  <div className="done-check">
                    <svg viewBox="0 0 20 20" fill="none">
                      <circle cx="10" cy="10" r="9" stroke="#2d6a4f" strokeWidth="1.5"/>
                      <polyline points="6,10.5 9,13.5 14,7.5" stroke="#2d6a4f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <div>
                    <div className="done-title">Annotations applied</div>
                    <div className="done-sub">
                      Your marked-up PDF is previewed below. Hover over highlights in a full PDF viewer to see clause notes.
                    </div>
                  </div>
                </div>
                <ProgressBar pct={100} />
                <div className="done-actions">
                  <a href={downloadUrl} download={downloadName} className="btn-primary">
                    ↓ Download PDF
                  </a>
                  <button onClick={reset} className="btn-secondary">
                    Review another contract
                  </button>
                </div>
              </div>
 
              {/* ── Inline PDF Preview ── */}
              <PdfPreview url={downloadUrl} fileName={downloadName} />
            </>
          )}
 
          {/* ── Error ── */}
          {phase === "error" && (
            <div className="error-banner">⚠ {error}</div>
          )}
 
          {/* ── How It Works ── */}
          <div className="how-section">
            <div className="section-label">How it works</div>
            <div className="how-grid">
              {[
                "Upload any contract PDF via drag-and-drop or the file picker.",
                "FastAPI backend (PyMuPDF) scans every page for clause patterns.",
                "Matching clauses receive coloured rectangle highlights + tooltip annotations.",
                "Annotated PDF previews inline on this page — no external viewer needed.",
                "Download the PDF anytime or review another contract when ready.",
              ].map((text, i) => (
                <div className="how-step" key={i}>
                  <span className="how-num">0{i + 1}</span>
                  <span className="how-text">{text}</span>
                </div>
              ))}
            </div>
          </div>
 
          {/* ── Disclaimer ── */}
          <div className="footer-note">
            <span className="footer-icon">ℹ</span>
            <span>AI adviser output supports human review only — not legal advice. All flagged clauses should be reviewed by the RGC team before decisions are made.</span>
          </div>
        </div>
 
        {/* ── Footer ── */}
        <footer style={{
          borderTop: "1px solid #e0dbd0",
          background: "#fff",
          padding: "18px 2rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}>

          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 11,
            color: "#9e9890",
            letterSpacing: ".06em",
          }}>

            Developed by <strong style={{ color: "#1a3f6f", fontWeight: 500 }}>Team 27</strong>
          </span>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 11,
            color: "#9e9890",
            letterSpacing: ".06em",
          }}>
            © {new Date().getFullYear()} University of Auckland · All rights reserved
          </span>
        </footer>
      </div>
    </>
  );
}