import { useState, useRef } from 'react';

function splitParts(text: string) {
  if (!text) return { prefix: "", suffix: "" };
  const parts = text.split("|");
  return {
    prefix: parts[0]?.trim() || "",
    suffix: parts.slice(1).join("|").trim()
  };
}

export default function App() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [client, setClient] = useState('mercor');
  const [jobUrl, setJobUrl] = useState('');
  const [rawJd, setRawJd] = useState('');
  const [structuredJd, setStructuredJd] = useState('');
  const [emailTemplate, setEmailTemplate] = useState('');
  const [suggestedTitles, setSuggestedTitles] = useState('');
  const [subject, setSubject] = useState('');
  const [linkedinTitle, setLinkedinTitle] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [jobFunctions, setJobFunctions] = useState<string[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  const [justifications, setJustifications] = useState<Record<string, string>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [mirrorSync, setMirrorSync] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState("");

  const showToast = (message: string) => {
    setToastMessage(message);
    const timeout = (window as any)._toastTimeout;
    if (timeout) clearTimeout(timeout);
    (window as any)._toastTimeout = setTimeout(() => {
      setToastMessage(null);
    }, 2000);
  };

  const copyToClipboard = async (text: string, label?: string) => {
    try {
      if (text) {
        await navigator.clipboard.writeText(text);
        showToast(label ? `Copied ${label}!` : "Copied to clipboard!");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubjectChange = (e: any) => {
    const val = e.target.value;
    setSubject(val);
    if (mirrorSync) {
      const { prefix: newPrefix } = splitParts(val);
      if (!newPrefix) return;
      setLinkedinTitle(prev => {
        if (!prev) return prev;
        const { prefix: oldPrefix, suffix } = splitParts(prev);
        if (oldPrefix === newPrefix) return prev;
        return suffix ? `${newPrefix} | ${suffix}` : newPrefix;
      });
    }
  };

  const handleLinkedinChange = (e: any) => {
    const val = e.target.value;
    setLinkedinTitle(val);
    if (mirrorSync) {
      const { prefix: newPrefix } = splitParts(val);
      if (!newPrefix) return;
      setSubject(prev => {
        if (!prev) return prev;
        const { prefix: oldPrefix, suffix } = splitParts(prev);
        if (oldPrefix === newPrefix) return prev;
        return suffix ? `${newPrefix} | ${suffix}` : newPrefix;
      });
    }
  };

  const jdRef = useRef<HTMLDivElement>(null);
  const emailRef = useRef<HTMLDivElement>(null);

  const handleGenerate = async () => {
    if (!rawJd.trim() && !jobUrl.trim()) {
      setError('Please provide a job link or paste the job description.');
      return;
    }

    setStep(2);
    setError(null);
    setLoadingStep("Analyzing job description...");

    const t1 = setTimeout(() => {
      setLoadingStep("Extracting key insights...");
    }, 1200);

    const t2 = setTimeout(() => {
      setLoadingStep("Generating structured output...");
    }, 2400);

    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL}/parse-jd`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          raw_jd: rawJd,
          url: jobUrl,
          client: client
        })
      });

      const data = await res.json();

      setStructuredJd(data.jd || "");
      setEmailTemplate(data.email || "");
      setSuggestedTitles((data.titles || []).join("\n"));
      setSubject(data.subject || "");
      setLinkedinTitle(data.linkedin_title || "");
      setSkills(data.skills || []);
      setJobFunctions(data.job_functions || []);
      setIndustries(data.industries || []);
      setJustifications(data.justifications || {});

      clearTimeout(t1);
      clearTimeout(t2);
      setStep(3);
    } catch (err: any) {
      clearTimeout(t1);
      clearTimeout(t2);
      setError(err.message || "Error processing your request.");
      setStep(1);
    }
  };

  const copyHtml = async (html: string, label?: string) => {
    try {
      const blob = new Blob([html], { type: "text/html" });
      const data = [new ClipboardItem({ "text/html": blob })];
      await navigator.clipboard.write(data);
      showToast(label ? `Copied ${label}!` : "Copied to clipboard!");
    } catch (e) {
      console.error(e);
    }
  };
  //Name suggested by Samarth
  return (
    <div className="layout-root">

      {step !== 2 && (
        <nav className="nav-top">
          <div className="nav-left">
            <span className="logo">Job Weaver</span>
            {step === 1 && <span className="logo-sub">CROSSING HURDLES</span>}
          </div>

          <div className="nav-right">
            {step === 1 && (
              <div className="step-indicator">
                STEP 1 OF 2
                <div className="progress-bars">
                  <div className="bar active"></div>
                  <div className="bar"></div>
                </div>
              </div>
            )}
            {step === 3 && (
              <>
                <div className="step-indicator">
                  STEP 2 OF 2
                  <div className="progress-bars">
                    <div className="bar active"></div>
                    <div className="bar active"></div>
                  </div>
                </div>
                <button className="btn-back" onClick={() => setStep(1)}>
                  <ArrowLeftIcon /> Back to Input
                </button>
              </>
            )}
          </div>
        </nav>
      )}

      <main className="main-content">

        {step === 1 && (
          <div className="wizard-input-view animate-fade-in">
            <div className="hero">
              <h1>Define Your Search</h1>
              <p>Paste the job description below to begin the structural analysis<br />of role requirements and latent expectations.</p>
            </div>

            <form 
              className="card form-card"
              onSubmit={(e) => {
                e.preventDefault();
                handleGenerate();
              }}
            >
              <label className="input-label">CLIENT</label>
              <div className="input-with-icon" style={{ marginBottom: "24px" }}>
                <select
                  className="input-field-clean"
                  value={client}
                  onChange={(e: any) => setClient(e.target.value)}
                  style={{ width: "100%", appearance: "auto" }}
                >
                  <option value="mercor">Mercor</option>
                  <option value="micro1">Micro1</option>
                  <option value="turing">Turing</option>
                </select>
              </div>

              <label className="input-label">JOB LINK</label>
              <div className="input-with-icon" style={{ marginBottom: "24px" }}>
                <LinkIcon />
                <input
                  type="text"
                  className="input-field-clean"
                  placeholder="Carefully enter the job link..."
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                />
              </div>

              <label className="input-label">PASTE RAW JOB DESCRIPTION</label>
              <textarea
                className="input-field-clean textarea-large"
                placeholder="Paste the full description here..."
                value={rawJd}
                onChange={(e) => setRawJd(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    handleGenerate();
                  }
                }}
              />

              {error && <p className="error-text">{error}</p>}

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => { setRawJd(''); setJobUrl(''); }}
                >
                  Clear
                </button>
                <button type="submit" className="btn-primary">
                  Generate Analysis <ArrowRightIcon />
                </button>
              </div>
            </form>

            <div className="version-label">V1.5 ALPHA</div>
          </div>
        )}

        {step === 2 && (
          <div className="wizard-processing-view">
            <div className="loading-container">
              <p className="loading-text">{loadingStep}<span className="dot-flashing"></span></p>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-output-view animate-fade-in">

            <div className="output-col-left">
              <div className="output-section">
                <div className="section-header">
                  <div>
                    <h3>Outreach Email</h3>
                  </div>
                  <div className="header-actions">
                    <label style={{ display: 'flex', alignItems: 'center', fontSize: '13px', fontWeight: 600, color: '#475569', cursor: 'pointer', marginRight: '8px' }}>
                      <input
                        type="checkbox"
                        checked={mirrorSync}
                        onChange={(e) => setMirrorSync(e.target.checked)}
                        style={{ marginRight: '6px' }}
                      />
                      Mirror Prefix
                    </label>
                    <button
                      className="btn-primary-box"
                      onClick={() => copyHtml(emailTemplate, "template")}
                    >
                      <CopyIcon /> Copy Template
                    </button>
                  </div>
                </div>

                {subject && (
                  <div style={{ marginBottom: "16px", padding: "12px 16px", backgroundColor: "#f8f9fa", borderRadius: "8px", border: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ flex: 1, marginRight: "16px" }}>
                      <div className="mini-title" style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>SUBJECT LINE</div>
                      <input
                        value={subject}
                        onChange={handleSubjectChange}
                        style={{ width: "100%", border: "none", background: "transparent", fontWeight: 600, color: "#0f172a", outline: "none", fontSize: "15px", fontFamily: "inherit" }}
                      />
                    </div>
                    <button className="btn-ghost-box" onClick={() => copyToClipboard(subject, "subject")} title="Copy Subject">
                      <CopyIcon /> Copy
                    </button>
                  </div>
                )}

                <div className="card output-card">
                  <div
                    className="rich-text-content"
                    ref={emailRef}
                    contentEditable
                    style={{ whiteSpace: 'normal' }}
                    dangerouslySetInnerHTML={{ __html: emailTemplate || "<p>No data</p>" }}
                  />
                </div>
              </div>

              <div className="output-section" style={{ marginTop: "48px" }}>
                <div className="section-header">
                  <div>
                    <h3>Job Description</h3>
                  </div>
                  <div className="header-actions">
                    <button
                      className="btn-primary-box"
                      onClick={() => copyHtml(structuredJd, "JD")}
                    >
                      <CopyIcon /> Copy JD
                    </button>
                  </div>
                </div>

                {linkedinTitle && (
                  <div style={{ marginBottom: "16px", padding: "12px 16px", backgroundColor: "#f8f9fa", borderRadius: "8px", border: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ flex: 1, marginRight: "16px" }}>
                      <div className="mini-title" style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>LINKEDIN TITLE</div>
                      <input
                        value={linkedinTitle}
                        onChange={handleLinkedinChange}
                        style={{ width: "100%", border: "none", background: "transparent", fontWeight: 600, color: "#0f172a", outline: "none", fontSize: "15px", fontFamily: "inherit" }}
                      />
                    </div>
                    <button className="btn-ghost-box" onClick={() => copyToClipboard(linkedinTitle, "LinkedIn title")} title="Copy LinkedIn Title">
                      <CopyIcon /> Copy
                    </button>
                  </div>
                )}
                <div className="card output-card">
                  <div
                    className="rich-text-content"
                    ref={jdRef}
                    contentEditable
                    style={{ whiteSpace: 'normal' }}
                    dangerouslySetInnerHTML={{ __html: structuredJd || "<p>No data</p>" }}
                  />
                </div>
              </div>
            </div>

            <div className="output-col-right">
              {/* 1. SUGGESTED TITLES */}
              <div className="card gray-card" style={{ padding: "24px" }}>
                <div className="mini-title" style={{ marginBottom: "12px" }}>SUGGESTED TITLES (TAP TO COPY)</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {suggestedTitles.split("\n").filter(Boolean).map((t: string, i: number) => {
                    const cleanT = t.replace(/^- /, '').trim();
                    return (
                      <div
                        key={i}
                        className="clickable-pill"
                        onClick={() => copyToClipboard(cleanT, "title")}
                        title={justifications[cleanT] || "Alternative job title matching role requirements."}
                      >
                        {cleanT}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 2. INDUSTRIES */}
              {industries && industries.length > 0 && (
                <div className="card gray-card" style={{ marginTop: "16px", padding: "24px" }}>
                  <div className="mini-title" style={{ marginBottom: "12px" }}>INDUSTRIES (TAP TO COPY)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {industries.map((s: string, i: number) => (
                      <div
                        key={i}
                        className="clickable-pill"
                        onClick={() => copyToClipboard(s, "industry")}
                        title={justifications[s] || "Industry sector relevant to the role's domain."}
                      >
                        {s}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. JOB FUNCTIONS */}
              {jobFunctions && jobFunctions.length > 0 && (
                <div className="card gray-card" style={{ marginTop: "16px", padding: "24px" }}>
                  <div className="mini-title" style={{ marginBottom: "12px" }}>JOB FUNCTIONS (TAP TO COPY)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {jobFunctions.map((s: string, i: number) => (
                      <div
                        key={i}
                        className="clickable-pill"
                        onClick={() => copyToClipboard(s, "job function")}
                        title={justifications[s] || "Core function related to the primary responsibilities."}
                      >
                        {s}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 4. TARGET SKILLS */}
              {skills && skills.length > 0 && (
                <div className="card gray-card" style={{ marginTop: "16px", padding: "24px" }}>
                  <div className="mini-title" style={{ marginBottom: "12px" }}>TARGET SKILLS (TAP TO COPY)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {skills.map((s: string, i: number) => (
                      <div
                        key={i}
                        className="clickable-pill"
                        onClick={() => copyToClipboard(s, "skill")}
                        title={justifications[s] || "Technical skill or framework required for the role."}
                      >
                        {s}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

          </div>
        )}
      </main>

      {toastMessage && (
        <div className="toast-notification">
          {toastMessage}
        </div>
      )}
    </div>
  );
}

// Inline SVGs tailored for the mockups
const LinkIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);

const ArrowRightIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" />
    <polyline points="12 5 19 12 12 19" />
  </svg>
);

const ArrowLeftIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12" />
    <polyline points="12 19 5 12 12 5" />
  </svg>
);

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);
