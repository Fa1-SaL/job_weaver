import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, ArrowLeft, History, Link, Check
} from 'lucide-react';
import TetrisLoading from './components/ui/tetris-loader';

const API_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

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
  const [isDomainView, setIsDomainView] = useState(false);
  const [domainPageSelection, setDomainPageSelection] = useState("crossing_hurdles");
  const [outputCheckmarks, setOutputCheckmarks] = useState({ inmail: true, jd: true });
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [hoveredLinkUrl, setHoveredLinkUrl] = useState<string | null>(null);

  const [lastRunData, setLastRunData] = useState<any>(() => {
    try {
      const saved = localStorage.getItem("job_weaver_last_run");
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });


  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);
      const localStr = localStorage.getItem("job_weaver_history");
      let localHist: any[] = [];
      if (localStr) {
        try { localHist = JSON.parse(localStr); } catch (e) { }
      }
      setHistoryItems(localHist);

      const res = await fetch(`${API_URL}/history`);
      const data = await res.json();
      if (data.success && Array.isArray(data.history)) {
        const map = new Map();
        [...data.history, ...localHist].forEach((it: any) => {
          if (it && it.id && !map.has(it.id)) map.set(it.id, it);
        });
        const merged = Array.from(map.values()).sort((a: any, b: any) =>
          new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime()
        );
        setHistoryItems(merged);
        localStorage.setItem("job_weaver_history", JSON.stringify(merged));
      }
    } catch (e) {
      console.error("Error fetching history from backend, showing local cache:", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadHistoryItem = async (itemId: string) => {
    try {
      setLoadingStep("Loading from cache...");
      setStep(2);
      setShowHistoryModal(false);
      let payload: any = null;

      try {
        const res = await fetch(`${API_URL}/history/${itemId}`);
        const data = await res.json();
        if (data.success && data.data) {
          payload = data.data;
        }
      } catch (err) {
        console.error("Backend fetch failed, checking localStorage detail...");
      }

      if (!payload) {
        const localDetailStr = localStorage.getItem(`jw_detail_${itemId}`);
        if (localDetailStr) {
          try { payload = JSON.parse(localDetailStr); } catch (e) { }
        }
      }

      if (payload) {
        if (payload._raw_jd) setRawJd(payload._raw_jd);
        if (payload._url) setJobUrl(payload._url);
        if (payload._client) {
          if (DOMAIN_PAGES.has(payload._client)) {
            setClient("domain_page");
            setDomainPageSelection(payload._client);
          } else {
            setClient(payload._client);
          }
        }

        const defaultTitles = [
          `${payload.role || 'Role'} (Research & Reporting)`,
          "Content Analyst (Media & Insights)",
          "Reporting Specialist (Analysis & Review)",
          "Media Reviewer (Content & Accuracy)"
        ];
        const loadedTitles = payload.titles && payload.titles.length > 0 ? payload.titles : defaultTitles;
        const loadedSkills = payload.skills && payload.skills.length > 0 ? payload.skills : ["Data Evaluation", "Quality Assurance", "Content Analysis"];
        const loadedFunctions = payload.job_functions && payload.job_functions.length > 0 ? payload.job_functions : ["Writing/Editing", "Analytics", "Project Management"];
        const loadedIndustries = payload.industries && payload.industries.length > 0 ? payload.industries : ["Technology, Information and Media", "Professional Services", "Education"];

        setStructuredJd(payload.jd || "");
        setEmailTemplate(payload.email || payload.inmail_draft || "");
        setSuggestedTitles(loadedTitles.join("\n"));
        setSubject(payload.subject || "");
        setLinkedinTitle(payload.linkedin_title || "");
        setSkills(loadedSkills);
        setJobFunctions(loadedFunctions);
        setIndustries(loadedIndustries);
        setJustifications(payload.justifications || {});
        setIsDomainView(payload.is_domain_page || DOMAIN_PAGES.has(payload._client) || payload._client === "domain_page");

        const restoredRun = {
          rawJd: payload._raw_jd || rawJd,
          jobUrl: payload._url || jobUrl,
          client: payload._client || client,
          domainPageSelection: DOMAIN_PAGES.has(payload._client) ? payload._client : domainPageSelection,
          outputCheckmarks,
          structuredJd: payload.jd || "",
          emailTemplate: payload.email || payload.inmail_draft || "",
          suggestedTitles: loadedTitles.join("\n"),
          subject: payload.subject || "",
          linkedinTitle: payload.linkedin_title || "",
          skills: loadedSkills,
          jobFunctions: loadedFunctions,
          industries: loadedIndustries,
          justifications: payload.justifications || {},
          isDomainView: payload.is_domain_page || DOMAIN_PAGES.has(payload._client)
        };
        setLastRunData(restoredRun);
        localStorage.setItem("job_weaver_last_run", JSON.stringify(restoredRun));

        setStep(3);
      } else {
        showToast("Could not load history item.");
        setStep(1);
      }
    } catch (e) {
      console.error(e);
      showToast("Error loading history item.");
      setStep(1);
    }
  };

  const clearHistory = async () => {
    try {
      await fetch(`${API_URL}/history`, { method: "DELETE" });
    } catch (e) { }
    localStorage.removeItem("job_weaver_history");
    setHistoryItems([]);
    showToast("History cleared!");
  };


  const DOMAIN_PAGES = new Set([
    'crossing_hurdles',
    'codegeniusrecruit',
    'curasenseai',
    'legaltrustai',
    'capitexai',
    'stemsyncai',
    'linguasenseai',
    'designmeshai'
  ]);

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

    const effectiveClient = client === "domain_page" ? domainPageSelection : client;

    if (lastRunData &&
      lastRunData.rawJd.trim() === rawJd.trim() &&
      lastRunData.client === client &&
      (client !== "domain_page" || lastRunData.domainPageSelection === domainPageSelection)) {
      const fallbackRole = lastRunData.subject?.split('|')[0]?.trim() || 'Role';
      const defaultTitles = [
        `${fallbackRole} (Research & Reporting)`,
        "Content Analyst (Media & Insights)",
        "Reporting Specialist (Analysis & Review)",
        "Media Reviewer (Content & Accuracy)"
      ];
      const loadedTitles = lastRunData.suggestedTitles && lastRunData.suggestedTitles.trim() ? lastRunData.suggestedTitles : defaultTitles.join("\n");
      const loadedSkills = lastRunData.skills && lastRunData.skills.length > 0 ? lastRunData.skills : ["Data Evaluation", "Quality Assurance", "Content Analysis"];
      const loadedFunctions = lastRunData.jobFunctions && lastRunData.jobFunctions.length > 0 ? lastRunData.jobFunctions : ["Writing/Editing", "Analytics", "Project Management"];
      const loadedIndustries = lastRunData.industries && lastRunData.industries.length > 0 ? lastRunData.industries : ["Technology, Information and Media", "Professional Services", "Education"];

      setStructuredJd(lastRunData.structuredJd || "");
      setEmailTemplate(lastRunData.emailTemplate || "");
      setSuggestedTitles(loadedTitles);
      setSubject(lastRunData.subject || "");
      setLinkedinTitle(lastRunData.linkedinTitle || "");
      setSkills(loadedSkills);
      setJobFunctions(loadedFunctions);
      setIndustries(loadedIndustries);
      setJustifications(lastRunData.justifications || {});
      setIsDomainView(lastRunData.isDomainView);
      setStep(3);
      showToast("Loaded from cache memory!");
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
      const res = await fetch(`${API_URL}/parse-jd`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          raw_jd: rawJd,
          url: jobUrl,
          client: effectiveClient,
          output_selection: client === "domain_page" ? outputCheckmarks : null
        })
      });

      const data = await res.json();

      const fallbackRole = data.subject?.split('|')[0]?.trim() || 'Role';
      const defaultTitles = [
        `${fallbackRole} (Research & Reporting)`,
        "Content Analyst (Media & Insights)",
        "Reporting Specialist (Analysis & Review)",
        "Media Reviewer (Content & Accuracy)"
      ];
      const loadedTitles = data.titles && data.titles.length > 0 ? data.titles : defaultTitles;
      const loadedSkills = data.skills && data.skills.length > 0 ? data.skills : ["Data Evaluation", "Quality Assurance", "Content Analysis"];
      const loadedFunctions = data.job_functions && data.job_functions.length > 0 ? data.job_functions : ["Writing/Editing", "Analytics", "Project Management"];
      const loadedIndustries = data.industries && data.industries.length > 0 ? data.industries : ["Technology, Information and Media", "Professional Services", "Education"];

      setStructuredJd(data.jd || "");
      setEmailTemplate(data.email || data.inmail_draft || "");
      setSuggestedTitles(loadedTitles.join("\n"));
      setSubject(data.subject || "");
      setLinkedinTitle(data.linkedin_title || "");
      setSkills(loadedSkills);
      setJobFunctions(loadedFunctions);
      setIndustries(loadedIndustries);
      setJustifications(data.justifications || {});
      setIsDomainView(data.is_domain_page || DOMAIN_PAGES.has(effectiveClient) || client === "domain_page");

      const runData = {
        rawJd,
        jobUrl,
        client,
        domainPageSelection,
        outputCheckmarks,
        structuredJd: data.jd || "",
        emailTemplate: data.email || data.inmail_draft || "",
        suggestedTitles: loadedTitles.join("\n"),
        subject: data.subject || "",
        linkedinTitle: data.linkedin_title || "",
        skills: loadedSkills,
        jobFunctions: loadedFunctions,
        industries: loadedIndustries,
        justifications: data.justifications || {},
        isDomainView: data.is_domain_page || DOMAIN_PAGES.has(effectiveClient) || client === "domain_page"
      };
      setLastRunData(runData);
      localStorage.setItem("job_weaver_last_run", JSON.stringify(runData));

      if (data._id || data.id) {
        const itemObj = { ...data, _raw_jd: rawJd, _url: jobUrl, _client: effectiveClient };
        localStorage.setItem(`jw_detail_${data._id || data.id}`, JSON.stringify(itemObj));
      }

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
            <span className="logo" onClick={() => setStep(1)} style={{ cursor: "pointer" }} title="Go to Homepage">Job Weaver</span>
            {step === 1 && <span className="logo-sub">CROSSING HURDLES</span>}
          </div>

          <div className="nav-right">
            <button
              className="btn-ghost-box"
              onClick={() => {
                setShowHistoryModal(true);
                fetchHistory();
              }}
              style={{ marginRight: "12px", display: "flex", alignItems: "center", gap: "6px" }}
              title="View History / Cache"
            >
              <History className="w-4 h-4 text-slate-600" />
              History
            </button>
            {step === 1 && (
              <>
                <div className="step-indicator">
                  STEP 1 OF 2
                  <div className="progress-bars">
                    <div className="bar active"></div>
                    <div className="bar"></div>
                  </div>
                </div>
                {lastRunData && (
                  <button
                    className="btn-back"
                    onClick={() => {
                      const fallbackRole = lastRunData.subject?.split('|')[0]?.trim() || 'Role';
                      const defaultTitles = [
                        `${fallbackRole} (Research & Reporting)`,
                        "Content Analyst (Media & Insights)",
                        "Reporting Specialist (Analysis & Review)",
                        "Media Reviewer (Content & Accuracy)"
                      ];
                      const loadedTitles = lastRunData.suggestedTitles && lastRunData.suggestedTitles.trim() ? lastRunData.suggestedTitles : defaultTitles.join("\n");
                      const loadedSkills = lastRunData.skills && lastRunData.skills.length > 0 ? lastRunData.skills : ["Data Evaluation", "Quality Assurance", "Content Analysis"];
                      const loadedFunctions = lastRunData.jobFunctions && lastRunData.jobFunctions.length > 0 ? lastRunData.jobFunctions : ["Writing/Editing", "Analytics", "Project Management"];
                      const loadedIndustries = lastRunData.industries && lastRunData.industries.length > 0 ? lastRunData.industries : ["Technology, Information and Media", "Professional Services", "Education"];

                      setStructuredJd(lastRunData.structuredJd || "");
                      setEmailTemplate(lastRunData.emailTemplate || "");
                      setSuggestedTitles(loadedTitles);
                      setSubject(lastRunData.subject || "");
                      setLinkedinTitle(lastRunData.linkedinTitle || "");
                      setSkills(loadedSkills);
                      setJobFunctions(loadedFunctions);
                      setIndustries(loadedIndustries);
                      setJustifications(lastRunData.justifications || {});
                      setIsDomainView(lastRunData.isDomainView);
                      setStep(3);
                      showToast("Returned to output view!");
                    }}
                    title="Forward to Output"
                  >
                    Forward <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </>
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
                  <ArrowLeft className="w-4 h-4" /> Back to Input
                </button>
              </>
            )}
          </div>
        </nav>
      )}

      <main className="main-content">

        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="wizard-input-view"
          >
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
              <label className="input-label">SELECT TARGET CLIENT</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "28px" }}>
                {[
                  { id: "mercor", name: "Mercor" },
                  { id: "micro1", name: "Micro1" },
                  { id: "turing", name: "Turing" },
                  { id: "domain_page", name: "Domain Page" }
                ].map((item) => {
                  const isSelected = client === item.id;
                  return (
                    <motion.div
                      key={item.id}
                      whileHover={{ scale: 1.02, translateY: -2 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setClient(item.id)}
                      style={{
                        padding: "18px 16px",
                        borderRadius: "14px",
                        border: isSelected ? "2px solid #2563eb" : "1.5px solid #e2e8f0",
                        backgroundColor: isSelected ? "#eff6ff" : "#ffffff",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: isSelected ? "0 10px 25px -5px rgba(37, 99, 235, 0.25)" : "0 2px 4px rgba(0,0,0,0.02)",
                        transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)"
                      }}
                    >
                      <span style={{ fontWeight: 700, fontSize: "1.05rem", color: isSelected ? "#1e40af" : "#0f172a" }}>{item.name}</span>
                    </motion.div>
                  );
                })}
              </div>

              <AnimatePresence>
                {client === "domain_page" && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    style={{ marginBottom: "28px", padding: "24px", backgroundColor: "#f8fafc", border: "1.5px solid #e2e8f0", borderRadius: "16px", overflow: "hidden" }}
                  >
                    <label className="input-label" style={{ color: "#334155" }}>SELECT DOMAIN PAGE</label>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", marginBottom: "24px" }}>
                      {[
                        { id: "crossing_hurdles", name: "Crossing Hurdles" },
                        { id: "codegeniusrecruit", name: "CodeGeniusRecruit" },
                        { id: "curasenseai", name: "CuraSenseAI" },
                        { id: "legaltrustai", name: "LegalTrustAI" },
                        { id: "capitexai", name: "CapitexAI" },
                        { id: "stemsyncai", name: "STEMSyncAI" },
                        { id: "linguasenseai", name: "LinguaSenseAI" },
                        { id: "designmeshai", name: "DesignMeshAI" }
                      ].map((dom) => {
                        const isDomSelected = domainPageSelection === dom.id;
                        return (
                          <motion.div
                            key={dom.id}
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.97 }}
                            onClick={() => setDomainPageSelection(dom.id)}
                            style={{
                              padding: "12px 14px",
                              borderRadius: "10px",
                              border: isDomSelected ? "2px solid #2563eb" : "1px solid #cbd5e1",
                              backgroundColor: isDomSelected ? "#2563eb" : "#ffffff",
                              color: isDomSelected ? "#ffffff" : "#1e293b",
                              cursor: "pointer",
                              fontSize: "0.86rem",
                              fontWeight: isDomSelected ? 700 : 600,
                              textAlign: "center",
                              boxShadow: isDomSelected ? "0 6px 16px rgba(37, 99, 235, 0.35)" : "0 1px 2px rgba(0,0,0,0.02)",
                              transition: "all 0.18s ease",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center"
                            }}
                          >
                            {dom.name}
                          </motion.div>
                        );
                      })}
                    </div>

                    <label className="input-label" style={{ color: "#334155" }}>OPTIONS</label>
                    <div style={{ display: "flex", gap: "14px" }}>
                      {[
                        { key: "inmail", label: "InMail Draft" },
                        { key: "jd", label: "Job Description" }
                      ].map((opt) => {
                        const isChecked = outputCheckmarks[opt.key as "inmail" | "jd"];
                        return (
                          <motion.div
                            key={opt.key}
                            whileHover={{ scale: 1.015 }}
                            whileTap={{ scale: 0.985 }}
                            onClick={() => {
                              if (isChecked && outputCheckmarks.inmail && outputCheckmarks.jd) {
                                setOutputCheckmarks({ ...outputCheckmarks, [opt.key]: false });
                              } else if (!isChecked) {
                                setOutputCheckmarks({ ...outputCheckmarks, [opt.key]: true });
                              } else {
                                showToast("At least one output option must be selected.");
                              }
                            }}
                            style={{
                              flex: 1,
                              padding: "16px 18px",
                              borderRadius: "12px",
                              border: isChecked ? "2px solid #2563eb" : "1.5px solid #cbd5e1",
                              backgroundColor: isChecked ? "#ffffff" : "#f1f5f9",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: "14px",
                              boxShadow: isChecked ? "0 8px 20px -4px rgba(37, 99, 235, 0.15)" : "none",
                              transition: "all 0.2s ease"
                            }}
                          >
                            <div style={{
                              width: "24px",
                              height: "24px",
                              borderRadius: "6px",
                              border: isChecked ? "none" : "2px solid #94a3b8",
                              backgroundColor: isChecked ? "#2563eb" : "transparent",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "#ffffff"
                            }}>
                              {isChecked && <Check className="w-4 h-4 stroke-[3]" />}
                            </div>
                            <div style={{ flex: 1, fontWeight: 700, fontSize: "0.98rem", color: isChecked ? "#0f172a" : "#475569" }}>
                              {opt.label}
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <label className="input-label">JOB LINK</label>
              <div className="input-with-icon" style={{ marginBottom: "26px" }}>
                <Link className="w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  className="input-field-clean"
                  placeholder="Paste the target job URL..."
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                />
              </div>

              <label className="input-label">PASTE RAW JOB DESCRIPTION</label>
              <textarea
                className="input-field-clean textarea-large"
                placeholder="Paste the full job description or specification here..."
                value={rawJd}
                onChange={(e) => setRawJd(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    handleGenerate();
                  }
                }}
              />

              {error && <motion.p initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="error-text">{error}</motion.p>}

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => { setRawJd(''); setJobUrl(''); }}
                >
                  Clear
                </button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  className="btn-primary"
                >
                  Generate
                </motion.button>
              </div>
            </form>

            <div className="version-label">2.0 ALPHA</div>
          </motion.div>
        )}

        {step === 2 && (
          <div className="wizard-processing-view">
            <TetrisLoading 
              size="md" 
              speed="normal" 
              showLoadingText={true} 
              loadingText={loadingStep || "Analyzing Job Description..."} 
            />
          </div>
        )}

        {step === 3 && (
          <div
            className="wizard-output-view animate-fade-in"
            onMouseOver={(e) => {
              const target = (e.target as HTMLElement).closest('a');
              if (target && target.href) {
                setHoveredLinkUrl(target.href);
              }
            }}
            onMouseOut={(e) => {
              const target = (e.target as HTMLElement).closest('a');
              if (target) {
                setHoveredLinkUrl(null);
              }
            }}
            onClick={(e) => {
              const target = (e.target as HTMLElement).closest('a');
              if (target && target.href && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                window.open(target.href, '_blank', 'noopener,noreferrer');
              }
            }}
          >

            <div className="output-col-left">
              {(!isDomainView || outputCheckmarks.inmail) && (
                <div className="output-section">
                  <div className="section-header">
                    <div>
                      <h3>{isDomainView ? "InMail Draft" : "Outreach Email"}</h3>
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
                        onClick={() => copyHtml(emailTemplate, isDomainView ? "InMail Draft" : "template")}
                      >
                        <CopyIcon /> {isDomainView ? "Copy InMail" : "Copy Template"}
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
              )}

              {(!isDomainView || outputCheckmarks.jd) && (
                <div className="output-section" style={{ marginTop: (!isDomainView || outputCheckmarks.inmail) ? "48px" : "0px" }}>
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
              )}
            </div>

            <div className="output-col-right">
              {/* 1. SUGGESTED TITLES */}
              {suggestedTitles && (
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
              )}

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

            {hoveredLinkUrl && (
              <div
                style={{
                  position: 'fixed',
                  bottom: 0,
                  left: 0,
                  backgroundColor: '#f8fafc',
                  color: '#334155',
                  padding: '4px 12px',
                  fontSize: '12px',
                  fontFamily: 'sans-serif',
                  borderTopRightRadius: '6px',
                  borderTop: '1px solid #cbd5e1',
                  borderRight: '1px solid #cbd5e1',
                  boxShadow: '0 -2px 6px rgba(0, 0, 0, 0.08)',
                  zIndex: 99999,
                  maxWidth: '80vw',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  pointerEvents: 'none'
                }}
              >
                {hoveredLinkUrl}
              </div>
            )}
          </div>
        )}
      </main>

      {toastMessage && (
        <div className="toast-notification">
          {toastMessage}
        </div>
      )}

      {showHistoryModal && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(15, 23, 42, 0.6)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 1000,
          padding: "24px"
        }}>
          <div className="card animate-fade-in" style={{
            backgroundColor: "#ffffff",
            borderRadius: "12px",
            width: "100%",
            maxWidth: "680px",
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            overflow: "hidden"
          }}>
            <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "var(--text-main)" }}>Recent Generation History</h3>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                {historyItems.length > 0 && (
                  <button className="btn-ghost-box" onClick={clearHistory} style={{ color: "#ef4444", fontSize: "0.85rem" }}>
                    Clear All
                  </button>
                )}
                <button
                  onClick={() => setShowHistoryModal(false)}
                  style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer", color: "var(--text-muted)", lineHeight: 1 }}
                >
                  &times;
                </button>
              </div>
            </div>

            <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1 }}>
              {loadingHistory ? (
                <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)" }}>Loading history cache...</div>
              ) : historyItems.length === 0 ? (
                <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)" }}>No cached history found yet. Generate a job description to get started!</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {historyItems.map((item) => (
                    <div
                      key={item.id}
                      style={{
                        padding: "16px",
                        border: "1px solid var(--border-color)",
                        borderRadius: "8px",
                        backgroundColor: "#f8fafc",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "16px",
                        transition: "all 0.15s ease"
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                          <span style={{ fontWeight: 700, fontSize: "1rem", color: "var(--text-main)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {item.role || "Untitled Job"}
                          </span>
                          <span style={{ fontSize: "0.75rem", padding: "2px 8px", borderRadius: "9999px", backgroundColor: "#e2e8f0", color: "#475569", fontWeight: 600, textTransform: "uppercase" }}>
                            {item.client}
                          </span>
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {item.raw_jd_snippet || item.url || "No details provided"}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px" }}>
                          {new Date(item.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <button
                        className="btn-primary-box"
                        onClick={() => loadHistoryItem(item.id)}
                        style={{ padding: "8px 16px", fontSize: "0.85rem", whiteSpace: "nowrap" }}
                      >
                        Load Output
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Inline SVGs tailored for the mockups

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);
