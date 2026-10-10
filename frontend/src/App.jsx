import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const MAX_RECIPIENTS = 500;
const MAX_UPLOAD_SIZE = 10 * 1024 * 1024;
const TERMINAL_STATES = new Set(["completed", "partially_failed", "failed"]);
const emptyRecipient = () => ({ name: "", email: "" });

function App() {
  const [certificate, setCertificate] = useState({ course_name: "", issuer: "", completion_date: "" });
  const [manualRecipients, setManualRecipients] = useState([emptyRecipient()]);
  const [importedRows, setImportedRows] = useState([]);
  const [mode, setMode] = useState("manual");
  const [upload, setUpload] = useState({ name: "", size: 0, error: "", loading: false });
  const [importSummary, setImportSummary] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [errors, setErrors] = useState({});
  const [job, setJob] = useState(null);
  const [submitError, setSubmitError] = useState("");
  const [statusError, setStatusError] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const pollingRef = useRef(false);
  const fileInputRef = useRef(null);
  const [theme, setTheme] = useState(() => {
    const saved = window.localStorage.getItem("certificate-theme");
    return saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("certificate-theme", theme);
  }, [theme]);

  const recipients = mode === "manual" ? manualRecipients : importedRows;
  const importedHasErrors = importedRows.some((row) => row.errors?.length || row.duplicate);
  const importedValidCount = importedRows.filter((row) => !row.errors?.length && !row.duplicate && row.name.trim() && row.email.trim()).length;

  const validateRecipients = useCallback((items) => {
    const next = {};
    const emails = new Map();
    items.forEach((item, index) => {
      const rowId = item.row_id || index;
      const name = item.name.trim();
      const email = item.email.trim();
      if (!name) next[`name-${rowId}`] = "Name is required.";
      else if (name.length > 100) next[`name-${rowId}`] = "Use 100 characters or fewer.";
      if (!email) next[`email-${rowId}`] = "Email is required.";
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next[`email-${rowId}`] = "Enter a valid email.";
      const normalized = email.toLowerCase();
      if (normalized) emails.set(normalized, [...(emails.get(normalized) || []), rowId]);
    });
    emails.forEach((rowIds) => {
      if (rowIds.length > 1) rowIds.forEach((rowId) => { next[`email-${rowId}`] = "Duplicate email address."; });
    });
    if (items.length < 1 || items.length > MAX_RECIPIENTS) next.recipients = "Use between 1 and 500 recipients.";
    return next;
  }, []);

  const validateForm = () => {
    const next = {};
    ["course_name", "issuer", "completion_date"].forEach((field) => {
      if (!certificate[field].trim()) next[field] = "This field is required.";
    });
    if (certificate.course_name.length > 150) next.course_name = "Use 150 characters or fewer.";
    if (certificate.issuer.length > 150) next.issuer = "Use 150 characters or fewer.";
    Object.assign(next, validateRecipients(recipients));
    setErrors(next);
    return Object.keys(next).length === 0 && (mode === "manual" || confirmed);
  };

  const fetchJob = useCallback(async (jobId, isRetry = false) => {
    if (pollingRef.current && !isRetry) return;
    pollingRef.current = true;
    setIsRefreshing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
      if (!response.ok) throw new Error(await getErrorMessage(response));
      setJob(await response.json());
      setStatusError("");
    } catch (error) {
      setStatusError(error.message || "Could not refresh job status.");
    } finally {
      pollingRef.current = false;
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (!job || TERMINAL_STATES.has(job.status)) return undefined;
    const timer = window.setInterval(() => fetchJob(job.job_id), 1500);
    return () => window.clearInterval(timer);
  }, [job, fetchJob]);

  const handleFile = async (file) => {
    setUpload({ name: file?.name || "", size: file?.size || 0, error: "", loading: false });
    setImportSummary(null);
    setImportedRows([]);
    setConfirmed(false);
    if (!file) return;
    if (file.type !== "application/pdf" || !file.name.toLowerCase().endsWith(".pdf")) {
      setUpload((current) => ({ ...current, error: "Choose a PDF file." }));
      return;
    }
    if (file.size > MAX_UPLOAD_SIZE) {
      setUpload((current) => ({ ...current, error: "The PDF must be 10 MB or smaller." }));
      return;
    }
    setUpload((current) => ({ ...current, loading: true }));
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE_URL}/import-students-pdf`, { method: "POST", body: formData });
      if (!response.ok) throw new Error(await getErrorMessage(response));
      const result = await response.json();
      setImportedRows(result.rows);
      setImportSummary(result.summary);
    } catch (error) {
      setUpload((current) => ({ ...current, error: error.message || "Could not import this PDF." }));
    } finally {
      setUpload((current) => ({ ...current, loading: false }));
    }
  };

  const updateImportedRow = (rowId, field, value) => {
    setImportedRows((rows) => {
      const updatedRows = rows.map((row) => row.row_id === rowId ? { ...row, [field]: value } : row);
      const validation = validateRecipients(updatedRows);
      return updatedRows.map((row) => {
        const rowErrors = [validation[`name-${row.row_id}`], validation[`email-${row.row_id}`]].filter(Boolean);
        return { ...row, errors: rowErrors, duplicate: rowErrors.includes("Duplicate email address.") };
      });
    });
    setConfirmed(false);
  };

  const removeImportedRow = (rowId) => {
    setImportedRows((rows) => {
      const remainingRows = rows.filter((row) => row.row_id !== rowId);
      const validation = validateRecipients(remainingRows);
      return remainingRows.map((row) => {
        const rowErrors = [validation[`name-${row.row_id}`], validation[`email-${row.row_id}`]].filter(Boolean);
        return { ...row, errors: rowErrors, duplicate: rowErrors.includes("Duplicate email address.") };
      });
    });
    setConfirmed(false);
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitError("");
    setDownloadError("");
    if (!validateForm()) return;
    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          certificate,
          recipients: recipients.map(({ name, email }) => ({ name: name.trim(), email: email.trim() })),
        }),
      });
      if (!response.ok) throw new Error(await getErrorMessage(response));
      const created = await response.json();
      setJob({ ...created, recipients: [], processed_count: 0, success_count: 0, failed_count: 0, progress_percent: 0 });
      await fetchJob(created.job_id, true);
    } catch (error) {
      setSubmitError(error.message || "Could not create the generation job.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateManual = (index, field, value) => {
    setManualRecipients((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item));
  };

  const download = async (recipient) => {
    setDownloadError("");
    try {
      const response = await fetch(`${API_BASE_URL}${recipient.certificate_url}`);
      if (!response.ok) throw new Error(await getErrorMessage(response));
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `certificate_${recipient.recipient_id}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setDownloadError(error.message || "Certificate download failed.");
    }
  };

  const reset = () => {
    setJob(null);
    setSubmitError("");
    setStatusError("");
    setDownloadError("");
    setErrors({});
  };

  const changeMode = (nextMode) => {
    setMode(nextMode);
    setErrors({});
    setSubmitError("");
  };

  return (
    <main className="page-shell">
      <header className="hero">
        <div className="brand-mark" aria-hidden="true">BC</div>
        <div className="hero-copy-block"><p className="eyebrow">Certificate operations</p><h1>Bulk Certificate Generator</h1><p className="hero-copy">Create polished certificates for your entire cohort in one simple workflow.</p></div>
        <button className="theme-toggle" type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>{theme === "dark" ? "☀ Light" : "☾ Dark"}</button>
      </header>
      <div className="content-grid">
        <section className="card form-card" aria-labelledby="request-title">
          <div className="section-heading"><div><p className="eyebrow">Step 1</p><h2 id="request-title">Certificate details</h2></div><span className="limit-note">Up to 500 recipients</span></div>
          <form onSubmit={submit} noValidate>
            <div className="field-grid">
              <Field label="Course name" value={certificate.course_name} error={errors.course_name} onChange={(value) => setCertificate({ ...certificate, course_name: value })} placeholder="e.g. Python Programming" />
              <Field label="Issuer" value={certificate.issuer} error={errors.issuer} onChange={(value) => setCertificate({ ...certificate, issuer: value })} placeholder="e.g. ABC Institute" />
            </div>
            <Field label="Completion date" type="date" value={certificate.completion_date} error={errors.completion_date} onChange={(value) => setCertificate({ ...certificate, completion_date: value })} />
            <div className="mode-selector" role="tablist" aria-label="Recipient input mode">
              <button type="button" role="tab" aria-selected={mode === "manual"} className={mode === "manual" ? "mode-button active" : "mode-button"} onClick={() => changeMode("manual")}>Enter manually</button>
              <button type="button" role="tab" aria-selected={mode === "pdf"} className={mode === "pdf" ? "mode-button active" : "mode-button"} onClick={() => changeMode("pdf")}>Upload student PDF</button>
            </div>
            {mode === "manual" ? <ManualRecipients recipients={manualRecipients} errors={errors} update={updateManual} setRecipients={setManualRecipients} /> : <PdfRecipients fileInputRef={fileInputRef} upload={upload} summary={importSummary} rows={importedRows} validCount={importedValidCount} confirmed={confirmed} setConfirmed={setConfirmed} onFile={handleFile} updateRow={updateImportedRow} removeRow={removeImportedRow} isSubmitting={isSubmitting} />}
            {errors.recipients && <p className="field-error">{errors.recipients}</p>}
            {submitError && <Alert message={submitError} />}
            {mode === "manual" && <button className="button primary submit-button" type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating job…" : "Generate certificates"} <span aria-hidden="true">→</span></button>}
          </form>
        </section>
        <Results job={job} isRefreshing={isRefreshing} statusError={statusError} downloadError={downloadError} fetchJob={fetchJob} download={download} reset={reset} />
      </div>
      <footer>Built for teams who celebrate learning.</footer>
    </main>
  );
}

function ManualRecipients({ recipients, errors, update, setRecipients }) {
  return <div className="recipient-section"><div className="recipient-heading"><div><p className="eyebrow">Step 2</p><h2>Recipients</h2></div><button type="button" className="button secondary small" onClick={() => setRecipients([...recipients, emptyRecipient()])} disabled={recipients.length >= MAX_RECIPIENTS}>+ Add recipient</button></div><div className="recipient-list">{recipients.map((recipient, index) => <div className="recipient-row" key={index}><span className="row-number">{index + 1}</span><div className="row-field"><label htmlFor={`manual-name-${index}`}>Full name</label><input id={`manual-name-${index}`} value={recipient.name} onChange={(event) => update(index, "name", event.target.value)} aria-invalid={Boolean(errors[`name-${index}`])} placeholder="Recipient name" />{errors[`name-${index}`] && <small className="field-error">{errors[`name-${index}`]}</small>}</div><div className="row-field"><label htmlFor={`manual-email-${index}`}>Email address</label><input id={`manual-email-${index}`} type="email" value={recipient.email} onChange={(event) => update(index, "email", event.target.value)} aria-invalid={Boolean(errors[`email-${index}`])} placeholder="name@example.com" />{errors[`email-${index}`] && <small className="field-error">{errors[`email-${index}`]}</small>}</div><button type="button" className="icon-button" aria-label={`Remove recipient ${index + 1}`} onClick={() => setRecipients(recipients.filter((_, itemIndex) => itemIndex !== index))} disabled={recipients.length === 1}>×</button></div>)}</div></div>;
}

function PdfRecipients({ fileInputRef, upload, summary, rows, validCount: importedValidCount, confirmed, setConfirmed, onFile, updateRow, removeRow, isSubmitting }) {
  const onDrop = (event) => { event.preventDefault(); onFile(event.dataTransfer.files[0]); };
  const hasInvalidRows = rows.some((row) => row.errors?.length || row.duplicate);
  const validCount = importedValidCount;
  const currentInvalidCount = rows.filter((row) => row.errors?.length).length;
  const currentDuplicateCount = rows.filter((row) => row.duplicate).length;

  return (
    <div className="recipient-section pdf-import-panel">
      <div className="recipient-heading">
        <div><p className="eyebrow">Step 2</p><h2>Import students</h2></div>
        {upload.name && <button type="button" className="button secondary small" onClick={() => fileInputRef.current?.click()}>Replace PDF</button>}
      </div>
      <div className="upload-zone" onDragOver={(event) => event.preventDefault()} onDrop={onDrop}>
        <input ref={fileInputRef} type="file" accept="application/pdf,.pdf" onChange={(event) => onFile(event.target.files[0])} hidden />
        <div className="upload-icon">↑</div>
        <strong>{upload.loading ? "Extracting student records…" : "Drop a student-list PDF here"}</strong>
        <span>or <button type="button" className="link-button" onClick={() => fileInputRef.current?.click()}>browse files</button></span>
        <small>Text-based PDF only · Name and Email columns · max 10 MB</small>
      </div>
      {upload.name && <div className="file-chip"><span>▣ {upload.name} <small>({formatBytes(upload.size)})</small></span>{upload.loading && <span>Working…</span>}</div>}
      {upload.error && <Alert message={upload.error} />}
      {summary && <div className="import-summary" aria-label="Student import summary">
        <SummaryStat label="Total extracted" value={summary.total_candidates} />
        <SummaryStat label="Valid" value={validCount} tone="good" />
        <SummaryStat label="Invalid" value={currentInvalidCount} tone="warn" />
        <SummaryStat label="Duplicate emails" value={currentDuplicateCount} tone="bad" />
      </div>}
      {rows.length > 0 && <div className="preview-panel">
        <div className="preview-header"><strong>Review imported students</strong><span>{rows.length} rows</span></div>
        <div className="preview-list" aria-label="Imported student rows">
          {rows.map((row) => <div className="preview-row" key={row.row_id}>
            <div className="row-id">{row.row_id}</div>
            <div className="row-field"><label htmlFor={`import-name-${row.row_id}`}>Name</label><input id={`import-name-${row.row_id}`} value={row.name} onChange={(event) => updateRow(row.row_id, "name", event.target.value)} aria-invalid={Boolean(row.errors?.length)} />{row.errors?.filter((error) => error.toLowerCase().includes("name")).map((error) => <small className="field-error" key={error}>{error}</small>)}</div>
            <div className="row-field"><label htmlFor={`import-email-${row.row_id}`}>Email</label><input id={`import-email-${row.row_id}`} type="email" value={row.email} onChange={(event) => updateRow(row.row_id, "email", event.target.value)} aria-invalid={Boolean(row.errors?.length || row.duplicate)} />{row.errors?.filter((error) => error.toLowerCase().includes("email")).map((error) => <small className="field-error" key={error}>{error}</small>)}</div>
            <button type="button" className="icon-button" aria-label={`Remove imported row ${row.row_id}`} onClick={() => removeRow(row.row_id)}>×</button>
          </div>)}
        </div>
        <div className="preview-actions">
          <label className="confirm-row"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} disabled={hasInvalidRows || validCount === 0} /> I reviewed these students and confirm the list is ready.</label>
          {hasInvalidRows && <small className="action-hint">Correct or remove invalid rows before confirming.</small>}
          <button className="button primary submit-button" type="submit" disabled={isSubmitting || upload.loading || rows.length === 0 || hasInvalidRows || validCount === 0 || rows.length > MAX_RECIPIENTS || !confirmed}>{isSubmitting ? "Creating job…" : "Confirm and generate certificates"} <span aria-hidden="true">→</span></button>
        </div>
      </div>}
    </div>
  );
}

function Results({ job, isRefreshing, statusError, downloadError, fetchJob, download, reset }) {
  const summary = useMemo(() => job ? `${job.success_count} successful · ${job.failed_count} failed · ${job.total_count} total` : "", [job]);
  return <section className="card results-card" aria-labelledby="results-title"><div className="section-heading"><div><p className="eyebrow">Step 3</p><h2 id="results-title">Generation status</h2></div>{job && <StatusBadge status={job.status} />}</div>{!job ? <div className="empty-state"><div className="empty-icon">✦</div><h3>Your results will appear here</h3><p>Submit a certificate request to monitor progress and download each completed PDF.</p></div> : <div className="results"><div className="job-meta"><span>Job #{job.job_id}</span><span>{summary}</span>{isRefreshing && <span className="refreshing">Updating…</span>}</div><div className="progress-header"><strong>{job.progress_percent}% complete</strong><span>{job.processed_count} of {job.total_count} processed</span></div><div className="progress-track" role="progressbar" aria-valuenow={job.progress_percent} aria-valuemin="0" aria-valuemax="100" aria-label="Certificate generation progress"><div className="progress-fill" style={{ width: `${job.progress_percent}%` }} /></div>{statusError && <div className="inline-error"><span>{statusError}</span><button type="button" onClick={() => fetchJob(job.job_id, true)}>Retry</button></div>}{downloadError && <Alert message={downloadError} />}<div className="recipient-results">{(job.recipients || []).map((recipient) => <div className="result-row" key={recipient.recipient_id}><div className={`status-dot ${recipient.status}`} /><div className="result-info"><strong>{recipient.name}</strong><span>{recipient.email}</span>{recipient.error_message && <small className="failure-message">{recipient.error_message}</small>}</div>{recipient.status === "succeeded" && recipient.certificate_url && <button type="button" className="button download-button" onClick={() => download(recipient)}>Download PDF</button>}<span className={`result-status ${recipient.status}`}>{recipient.status === "succeeded" ? "Ready" : recipient.status === "failed" ? "Failed" : "Pending"}</span></div>)}</div>{TERMINAL_STATES.has(job.status) && <button type="button" className="button secondary another-button" onClick={reset}>Start another job</button>}</div>}</section>;
}

function Field({ label, value, error, onChange, type = "text", placeholder }) {
  const id = label.toLowerCase().replaceAll(" ", "-");
  return <div className="field"><label htmlFor={id}>{label}</label><input id={id} type={type} value={value} onChange={(event) => onChange(event.target.value)} aria-invalid={Boolean(error)} placeholder={placeholder} />{error && <small className="field-error">{error}</small>}</div>;
}

function SummaryStat({ label, value, tone = "" }) { return <div className={`summary-stat ${tone}`}><strong>{value}</strong><span>{label}</span></div>; }
function StatusBadge({ status }) { const labels = { pending: "Pending", processing: "Processing", completed: "Completed", partially_failed: "Partial success", failed: "Failed" }; return <span className={`status-badge ${status}`}>{labels[status] || status}</span>; }
function Alert({ message }) { return <div className="alert" role="alert">{message}</div>; }
function formatBytes(bytes) { return `${(bytes / 1024 / 1024).toFixed(2)} MB`; }
async function getErrorMessage(response) { try { const body = await response.json(); if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).join(" "); return body.detail || `Request failed (${response.status}).`; } catch { return `Request failed (${response.status}).`; } }

export default App;
