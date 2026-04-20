import { Suspense, lazy, useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Search, LayoutDashboard, FileText, Loader2, AlertCircle,
  Plus, MessageSquare, Trash2, ClipboardList, CheckCircle, XCircle,
  TrendingUp, TrendingDown, Minus, Sun, Moon, Upload, Database,
  FolderOpen, Send,
} from 'lucide-react';
import './App.css';

const Chart = lazy(() => import('react-apexcharts'));
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function ChartFallback() {
  return (
    <div className="chart-loading-placeholder" role="status" aria-live="polite">
      Loading chart...
    </div>
  );
}

async function parseJsonResponse(response, fallbackMessage) {
  const text = await response.text();
  let payload = null;

  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      if (!response.ok) throw new Error(fallbackMessage);
    }
  }

  if (!response.ok) {
    throw new Error(payload?.error || fallbackMessage);
  }

  return payload;
}

// ── localStorage helpers ──────────────────────────────────────────────────────
const STORAGE_KEY = 'budget-dashboard-conversations';
const THEME_KEY   = 'budget-dashboard-theme';
const MAX_UPLOAD_BYTES = 250 * 1024 * 1024;
const MAX_FILES_PER_ANALYSIS = 10;

function normalizeConversation(conv) {
  if (!conv || typeof conv !== 'object') return conv;
  const datasetPath = conv.datasetPath ?? conv.data?.dataset_path ?? null;
  const datasetName = conv.datasetName ?? conv.data?.dataset_name ?? null;
  const datasetAlias = conv.datasetAlias ?? conv.data?.dataset_alias ?? null;
  return { ...conv, datasetPath, datasetName, datasetAlias };
}

function loadConversations() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]').map(normalizeConversation); }
  catch { return []; }
}

function saveConversations(convs) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(convs.slice(0, 50).map(normalizeConversation))); }
  catch { /* ignore quota errors */ }
}

function getConversationDatasetMeta(conv) {
  const name = (conv?.datasetName || '').trim() || 'Dataset unknown';
  const alias = (conv?.datasetAlias || '').trim();
  const hasDistinctAlias = alias && alias.toLowerCase() !== name.toLowerCase();
  return {
    name,
    alias: hasDistinctAlias ? alias : '',
  };
}

function needsDatasetBackfill(conv) {
  if (!conv?.sessionId) return false;
  return !(conv.datasetPath && conv.datasetName);
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1).replace(/\.0$/, '')} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1).replace(/\.0$/, '')} KB`;
  return `${bytes} B`;
}

function timeLabel(ts) {
  const d = Math.floor((Date.now() - ts) / 86400000);
  if (d === 0) return 'Today';
  if (d === 1) return 'Yesterday';
  if (d < 7)  return `${d}d ago`;
  return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function cloneResult(value) {
  if (value == null) return value;
  if (typeof structuredClone === 'function') return structuredClone(value);
  return JSON.parse(JSON.stringify(value));
}

// ── Number formatters for charts ──────────────────────────────────────────────
function formatChartNumber(val) {
  if (val == null || typeof val !== 'number' || isNaN(val)) return '';
  const abs = Math.abs(val);
  if (abs >= 1_000_000_000) return (val / 1_000_000_000).toFixed(1).replace(/\.0$/, '') + 'B';
  if (abs >= 1_000_000)     return (val / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (abs >= 1_000)         return (val / 1_000).toFixed(1).replace(/\.0$/, '') + 'K';
  if (Number.isInteger(val)) return val.toLocaleString();
  return val.toFixed(2);
}

function formatTooltipNumber(val) {
  if (val == null || typeof val !== 'number' || isNaN(val)) return '';
  return val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ForecastCard({ fc }) {
  const TrendIcon = fc.trend_direction === 'upward' ? TrendingUp
    : fc.trend_direction === 'downward' ? TrendingDown : Minus;

  const trendStyle = fc.trend_direction === 'upward'
    ? { color: 'var(--trend-up)',   borderColor: 'var(--trend-up)',   background: 'var(--trend-up-bg)' }
    : fc.trend_direction === 'downward'
    ? { color: 'var(--trend-down)', borderColor: 'var(--trend-down)', background: 'var(--trend-down-bg)' }
    : { color: 'var(--trend-flat)', borderColor: 'var(--trend-flat)', background: 'var(--trend-flat-bg)' };

  const borderLeft = `4px solid ${fc.trend_direction === 'upward' ? 'var(--trend-up)' : fc.trend_direction === 'downward' ? 'var(--trend-down)' : 'var(--trend-flat)'}`;

  const lastProj = fc.projected?.values?.at(-1);
  const lastCat  = fc.projected?.categories?.at(-1);
  const lastLo   = fc.projected?.lower_bound?.at(-1);
  const lastHi   = fc.projected?.upper_bound?.at(-1);
  const fmt = (n) => n == null ? '–' : Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 });

  const r2Class = fc.r_squared >= 0.9 ? 'r2-high' : fc.r_squared >= 0.7 ? 'r2-mid' : 'r2-low';
  const r2Label = fc.r_squared >= 0.9 ? 'High confidence' : fc.r_squared >= 0.7 ? 'Moderate confidence' : 'Low confidence';

  return (
    <div className="forecast-card" style={{ borderLeft }}>
      {fc.low_confidence_warning && (
        <div className="forecast-warning-banner">
          <AlertCircle size={13} />
          <span>{fc.low_confidence_warning}</span>
        </div>
      )}
      <div className="forecast-card-header">
        <span className="forecast-title">{fc.title}</span>
        <span className="forecast-trend-badge" style={trendStyle}>
          <TrendIcon size={13} />
          {fc.trend_direction}
        </span>
      </div>
      <p className="forecast-summary">{fc.trend_summary}</p>
      <div className="forecast-projected-value">
        <span className="forecast-big-number">{fmt(lastProj)}</span>
        {fc.unit && <span className="forecast-unit">{fc.unit}</span>}
        {lastCat && <span className="forecast-unit">({lastCat})</span>}
      </div>
      <div className="forecast-stats">
        <div className="forecast-stat">
          <span className="forecast-stat-label">95% CI</span>
          <span className="forecast-stat-value">{fmt(lastLo)} – {fmt(lastHi)}</span>
        </div>
        <div className="forecast-stat">
          <span className="forecast-stat-label">R² <span className="forecast-stat-subtitle">(model fit)</span></span>
          <span className={`forecast-stat-value ${r2Class}`}>
            {fc.r_squared?.toFixed(2)} <span className="r2-label">{r2Label}</span>
          </span>
        </div>
        {fc.model_type && (
          <div className="forecast-stat">
            <span className="forecast-stat-label">Model</span>
            <span className="forecast-stat-value forecast-model-type">{fc.model_type}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function PlanApprovalCard({ pendingPlan, onApprove, onReject }) {
  return (
    <div className="approval-card">
      <div className="card-header">
        <ClipboardList className="card-icon" />
        <h2>Review Analysis Plan</h2>
      </div>
      <p className="approval-subtitle">
        Approve the steps below to run the full analysis, or reject to revise your question.
      </p>
      <ol className="plan-steps">
        {pendingPlan.analyses?.map(step => (
          <li key={step.id} className="plan-step">
            <span className="step-label">{step.output_label}</span>
            <span className="step-desc">{step.description}</span>
          </li>
        ))}
      </ol>
      <div className="approval-actions">
        <button type="button" className="btn-approve" onClick={onApprove}>
          <CheckCircle size={15} /> Approve &amp; Run
        </button>
        <button type="button" className="btn-reject" onClick={onReject}>
          <XCircle size={15} /> Reject
        </button>
      </div>
    </div>
  );
}

function WelcomeState({ onSuggestionClick }) {
  return (
    <div className="welcome-state">
      <LayoutDashboard size={64} className="welcome-icon" />
      <h2>JNJ Budget Dashboard</h2>
      <p>
        Ask for a broad read on the dataset, a breakdown of key patterns, or a focused comparison.
        The app will inspect the uploaded data, draft a plan, and turn the results into charts and a report.
      </p>
      <div className="suggestions">
        <button
          type="button"
          onClick={() => onSuggestionClick('Perform a thorough analysis of this dataset and highlight the most important trends, outliers, and actionable insights.')}
        >
          "Perform a thorough analysis and surface the most important insights"
        </button>
        <button
          type="button"
          onClick={() => onSuggestionClick('Summarize the structure of this dataset, identify the strongest patterns, and show the visuals that best explain what stands out.')}
        >
          "Summarize the dataset structure and show the clearest patterns"
        </button>
        <button
          type="button"
          onClick={() => onSuggestionClick('Analyze this data like an expert analyst: compare major segments, explain notable relationships, and point out anything unusual or worth investigating further.')}
        >
          "Compare major segments, explain relationships, and flag anomalies"
        </button>
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
function App() {
  const [question, setQuestion]           = useState('');
  // 'idle' | 'loading_start' | 'pending_approval' | 'loading_resume' | 'complete' | 'error'
  const [appState, setAppState]           = useState('idle');
  const [error, setError]                 = useState(null);
  const [threadId, setThreadId]           = useState(null);
  const [pendingPlan, setPendingPlan]     = useState(null);
  const [conversations, setConversations] = useState(loadConversations);
  const [activeConvId, setActiveConvId]   = useState(null);
  const [theme, setTheme]                 = useState(() => localStorage.getItem(THEME_KEY) || 'light');
  const [datasets, setDatasets]           = useState([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [uploading, setUploading]         = useState(false);
  const [datasetBackfillRetryTick, setDatasetBackfillRetryTick] = useState(0);

  // Follow-up state
  const [sessionId, setSessionId]                   = useState(null);
  const [dashboardSections, setDashboardSections]   = useState([]);
  const [followupDrafts, setFollowupDrafts]         = useState({});
  const [loadingFollowupConvId, setLoadingFollowupConvId] = useState(null);
  const followupEndRef = useRef(null);
  const activeConvIdRef = useRef(null);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const attemptedDatasetBackfillsRef = useRef(new Set());

  useEffect(() => {
    if (!folderInputRef.current) return;
    folderInputRef.current.setAttribute('webkitdirectory', '');
    folderInputRef.current.setAttribute('directory', '');
  }, []);

  const fetchDatasets = useCallback(async () => {
    try {
      const res = await fetch(apiUrl('/api/datasets'));
      const json = await parseJsonResponse(res, 'Unable to load datasets');
      setDatasets(json.datasets || []);
      setSelectedDataset(current => current || json.datasets?.[0]?.path || '');
    } catch { /* ignore — backend may not be running */ }
  }, []);

  useEffect(() => { fetchDatasets(); }, [fetchDatasets]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(apiUrl('/api/upload'), { method: 'POST', body: formData });
      const json = await parseJsonResponse(res, 'Upload failed');
      await fetchDatasets();
      setSelectedDataset(json.path);
      setAppState(current => (current === 'error' ? 'idle' : current));
    } catch (err) {
      setError(err.message);
      setAppState('error');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleFolderUpload = async (e) => {
    const files = Array.from(e.target.files || []).filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase();
      return ext === 'csv' || ext === 'json';
    });
    if (files.length === 0) {
      setError('No CSV or JSON files were found in that folder.');
      setAppState('error');
      e.target.value = '';
      return;
    }
    if (files.length > MAX_FILES_PER_ANALYSIS) {
      setError(`That folder contains ${files.length} supported files. The current limit is ${MAX_FILES_PER_ANALYSIS}.`);
      setAppState('error');
      e.target.value = '';
      return;
    }
    const totalBytes = files.reduce((sum, file) => sum + (file.size || 0), 0);
    if (totalBytes > MAX_UPLOAD_BYTES) {
      setError(`That folder is ${formatBytes(totalBytes)}. Folder uploads must stay under ${formatBytes(MAX_UPLOAD_BYTES)}.`);
      setAppState('error');
      e.target.value = '';
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      files.forEach(f => formData.append('files', f));
      // Use the webkitRelativePath to derive folder name
      const firstPath = files[0].webkitRelativePath || '';
      const folderName = firstPath.split('/')[0] || '';
      if (folderName) formData.append('folder_name', folderName);
      const res = await fetch(apiUrl('/api/upload-folder'), { method: 'POST', body: formData });
      const json = await parseJsonResponse(res, 'Upload failed');
      await fetchDatasets();
      setSelectedDataset(json.folder_path);
      setAppState(current => (current === 'error' ? 'idle' : current));
    } catch (err) {
      setError(err.message);
      setAppState('error');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  useEffect(() => { saveConversations(conversations); }, [conversations]);

  useEffect(() => {
    const pendingSessionIds = Array.from(new Set(
      conversations
        .filter(conv => needsDatasetBackfill(conv))
        .map(conv => conv.sessionId)
        .filter(sessionId => {
          if (!sessionId) return false;
          if (attemptedDatasetBackfillsRef.current.has(sessionId)) return false;
          attemptedDatasetBackfillsRef.current.add(sessionId);
          return true;
        })
    ));

    if (pendingSessionIds.length === 0) return;

    let cancelled = false;
    let retryTimer = null;

    const backfillDatasetMetadata = async () => {
      const results = await Promise.all(
        pendingSessionIds.map(async (sessionId) => {
          try {
            const response = await fetch(apiUrl(`/api/sessions/${encodeURIComponent(sessionId)}/dataset`));
            if (response.status === 404) {
              return [sessionId, 'missing'];
            }
            const payload = await parseJsonResponse(response, 'Unable to load saved dataset metadata');
            return [sessionId, {
              datasetPath: payload.dataset_path || null,
              datasetName: payload.dataset_name || null,
              datasetAlias: payload.dataset_alias || null,
            }];
          } catch {
            return [sessionId, null];
          }
        })
      );

      if (cancelled) return;
      const failedSessionIds = [];
      const metadataBySessionId = new Map(results.filter(([, value]) => value));
      results.forEach(([sessionId, value]) => {
        if (value === null) {
          attemptedDatasetBackfillsRef.current.delete(sessionId);
          failedSessionIds.push(sessionId);
        }
      });
      if (failedSessionIds.length > 0) {
        retryTimer = window.setTimeout(() => {
          setDatasetBackfillRetryTick(tick => tick + 1);
        }, 5000);
      }
      if (metadataBySessionId.size === 0) return;

      setConversations(current => {
        let changed = false;
        const next = current.map(conv => {
          if (!needsDatasetBackfill(conv)) return conv;
          const recovered = metadataBySessionId.get(conv.sessionId);
          if (!recovered) return conv;
          const merged = {
            ...conv,
            datasetPath: conv.datasetPath || recovered.datasetPath,
            datasetName: conv.datasetName || recovered.datasetName,
            datasetAlias: conv.datasetAlias ?? recovered.datasetAlias,
          };
          if (
            merged.datasetPath !== conv.datasetPath ||
            merged.datasetName !== conv.datasetName ||
            merged.datasetAlias !== conv.datasetAlias
          ) {
            changed = true;
            return merged;
          }
          return conv;
        });
        return changed ? next : current;
      });
    };

    backfillDatasetMetadata();

    return () => {
      cancelled = true;
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, [conversations, datasetBackfillRetryTick]);

  useEffect(() => {
    activeConvIdRef.current = activeConvId;
  }, [activeConvId]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', theme === 'dark' ? '#141414' : '#D51130');
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const loading = appState === 'loading_start' || appState === 'loading_resume';
  const hasDataset = Boolean(selectedDataset);
  const activeConversation = conversations.find(conv => conv.id === activeConvId) || null;
  const activeDatasetMeta = activeConversation ? getConversationDatasetMeta(activeConversation) : null;

  // ── sidebar actions ────────────────────────────────────────────────────────
  const handleNewChat = () => {
    setQuestion(''); setError(null);
    setThreadId(null); setPendingPlan(null);
    setActiveConvId(null); setAppState('idle');
    setSessionId(null); setDashboardSections([]);
  };

  const handleLoadConversation = (conv) => {
    setQuestion(conv.question);
    setError(null); setThreadId(null); setPendingPlan(null);
    setActiveConvId(conv.id); setAppState('complete');
    // Restore sections if available, otherwise wrap old format into initial section
    if (conv.sections) {
      setDashboardSections(cloneResult(conv.sections));
    } else if (conv.data) {
      setDashboardSections([{
        type: 'initial',
        question: conv.question,
        charts: conv.data.graphs?.charts || [],
        forecasts: conv.data.forecast_output?.forecasts || [],
        summary: conv.data.summary,
      }]);
    }
    setSessionId(conv.sessionId || null);
  };

  const handleDeleteConversation = (id) => {
    setConversations(prev => prev.filter(c => c.id !== id));
    setFollowupDrafts(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    if (loadingFollowupConvId === id) setLoadingFollowupConvId(null);
    if (activeConvId === id) handleNewChat();
  };

  // ── analysis flow ──────────────────────────────────────────────────────────
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    setAppState('loading_start');
    setError(null); setThreadId(null);
    setPendingPlan(null); setActiveConvId(null);
    setSessionId(null); setDashboardSections([]);

    try {
      const response = await fetch(apiUrl('/api/analyze/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          dataset_path: selectedDataset || undefined,
          // If selected dataset is a folder (ends with /), find its files from datasets list
          ...(selectedDataset?.endsWith('/')
            ? { filepaths: datasets.find(d => d.path === selectedDataset)?.files || [] }
            : { filepath: selectedDataset || undefined }),
        }),
      });
      const result = await parseJsonResponse(response, 'Failed to fetch data from the server');
      if (result.status === 'pending_approval') {
        setThreadId(result.thread_id);
        setPendingPlan(result.plan);
        setAppState('pending_approval');
      } else if (result.status === 'error') {
        throw new Error(result.error);
      } else {
        finishAnalysis(result);
      }
    } catch (err) {
      setError(err.message);
      setAppState('error');
    }
  };

  const handleApprove = async () => {
    setAppState('loading_resume'); setError(null);
    try {
      const response = await fetch(apiUrl('/api/analyze/resume'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, approved: true }),
      });
      const result = await parseJsonResponse(response, 'Failed to fetch data from the server');
      if (result.status === 'error') throw new Error(result.error);
      finishAnalysis(result);
    } catch (err) {
      setError(err.message);
      setAppState('error');
    }
  };

  const handleReject = async () => {
    try {
      await fetch(apiUrl('/api/analyze/resume'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, approved: false }),
      });
    } catch { /* ignore */ }
    setThreadId(null); setPendingPlan(null); setAppState('idle');
  };

  const finishAnalysis = (result) => {
    const snapshot = cloneResult(result);
    const initialSection = {
      type: 'initial',
      question,
      charts: snapshot.graphs?.charts || [],
      forecasts: snapshot.forecast_output?.forecasts || [],
      summary: snapshot.summary,
    };
    const sections = [initialSection];
    const conv = {
      id: Date.now().toString(), question, timestamp: Date.now(),
      data: snapshot, sections, sessionId: snapshot.session_id || null,
      datasetPath: snapshot.dataset_path || null,
      datasetName: snapshot.dataset_name || null,
      datasetAlias: snapshot.dataset_alias || null,
    };
    setConversations(prev => [conv, ...prev]);
    setFollowupDrafts(prev => ({ ...prev, [conv.id]: '' }));
    setActiveConvId(conv.id);
    setDashboardSections(sections);
    setSessionId(snapshot.session_id || null);
    setAppState('complete');
  };

  // ── follow-up flow ────────────────────────────────────────────────────
  const handleFollowup = async (e) => {
    e.preventDefault();
    const sourceConvId = activeConvId;
    const sourceSessionId = sessionId;
    const sourceQuestion = (followupDrafts[sourceConvId] || '').trim();

    if (!sourceConvId || !sourceQuestion || !sourceSessionId || loadingFollowupConvId) return;
    setLoadingFollowupConvId(sourceConvId);
    setError(null);

    try {
      const response = await fetch(apiUrl('/api/analyze/followup'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: sourceQuestion, session_id: sourceSessionId }),
      });
      const result = await parseJsonResponse(response, 'Follow-up failed');

      const newSection = {
        type: 'followup',
        question: sourceQuestion,
        charts: result.new_charts || [],
        forecasts: result.forecast_output?.forecasts || [],
        explanation: result.explanation,
      };

      let updatedSections = null;
      setConversations(convs => convs.map(c => {
        if (c.id !== sourceConvId) return c;
        updatedSections = [...(c.sections || []), newSection];
        return { ...c, sections: cloneResult(updatedSections) };
      }));

      if (updatedSections && activeConvIdRef.current === sourceConvId) {
        setDashboardSections(cloneResult(updatedSections));
      }
      setFollowupDrafts(prev => ({ ...prev, [sourceConvId]: '' }));

      // Auto-scroll to new section
      if (activeConvIdRef.current === sourceConvId) {
        setTimeout(() => followupEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingFollowupConvId(current => (current === sourceConvId ? null : current));
    }
  };

  const activeFollowupQuestion = activeConvId ? (followupDrafts[activeConvId] || '') : '';
  const followupLoading = loadingFollowupConvId === activeConvId;

  const isInputDisabled = loading || appState === 'pending_approval';
  const isAnalyzeDisabled = isInputDisabled || !hasDataset || !question.trim();

  return (
    <div className="app-container">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header className="header">
        <div className="logo-section">
          <LayoutDashboard className="logo-icon" />
          <h1>Budget Dashboard</h1>
        </div>
        <form onSubmit={handleSearch} className="search-form">
          <label className="sr-only" htmlFor="analysis-question">Ask a question</label>
          <div className="search-input-wrapper">
            <Search className="search-icon" aria-hidden="true" />
            <input
              id="analysis-question"
              type="text"
              placeholder="Ask a question about the selected dataset..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={isInputDisabled}
              aria-describedby={!hasDataset ? 'dataset-required-message' : undefined}
            />
          </div>
          <button type="submit" disabled={isAnalyzeDisabled} aria-busy={loading}>
            {loading ? <Loader2 className="animate-spin" aria-hidden="true" /> : 'Analyze'}
          </button>
        </form>
        <div className="dataset-picker">
          <label className="sr-only" htmlFor="dataset-select">Choose a dataset</label>
          <Database size={16} className="dataset-icon" aria-hidden="true" />
          <select
            id="dataset-select"
            aria-label="Select dataset"
            value={selectedDataset}
            onChange={(e) => {
              setSelectedDataset(e.target.value);
              setError(null);
              setAppState(current => (current === 'error' ? 'idle' : current));
            }}
            disabled={loading || appState === 'pending_approval'}
          >
            {datasets.length === 0 && <option value="">No datasets found</option>}
            {datasets.map(ds => (
              <option key={ds.path} value={ds.path}>
                {ds.type === 'folder'
                  ? `📁 ${ds.name} (${ds.file_count} files)`
                  : `${ds.name} (${(ds.size / 1024).toFixed(0)} KB)`}
              </option>
            ))}
          </select>
          <div className="upload-btn-group">
            <button
              type="button"
              className="upload-btn upload-btn--file"
              title="Upload a single CSV or JSON file"
              aria-label="Upload a single CSV or JSON file"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading
                ? <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                : <Upload size={14} aria-hidden="true" />}
              <span className="upload-btn-label">File</span>
            </button>
            <button
              type="button"
              className="upload-btn upload-btn--folder"
              title="Upload a folder of CSV/JSON files"
              aria-label="Upload a folder of CSV or JSON files"
              onClick={() => folderInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading
                ? <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                : <FolderOpen size={14} aria-hidden="true" />}
              <span className="upload-btn-label">Folder</span>
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json"
            onChange={handleUpload}
            hidden
            disabled={uploading}
          />
          <input
            type="file"
            ref={folderInputRef}
            accept=".csv,.json"
            multiple
            onChange={handleFolderUpload}
            hidden
            disabled={uploading}
          />
        </div>
        <div className="header-actions">
          <button
            className="theme-toggle"
            type="button"
            onClick={toggleTheme}
            title="Toggle theme"
            aria-pressed={theme === 'dark'}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
        </div>
      </header>

      {/* ── Body row: sidebar + main ──────────────────────────────────────── */}
      <div className="body-row">

        {/* Sidebar */}
        <aside className="sidebar">
          <button className="new-analysis-btn" type="button" onClick={handleNewChat}>
            <Plus size={15} />
            New Analysis
          </button>

          <div className="sidebar-list">
            {conversations.length === 0
              ? <p className="sidebar-empty">No analyses yet</p>
              : conversations.map(conv => {
                  const datasetMeta = getConversationDatasetMeta(conv);
                  const datasetTitle = datasetMeta.alias
                    ? `${datasetMeta.name} (${datasetMeta.alias})`
                    : datasetMeta.name;
                  return (
                  <div key={conv.id} className={`sidebar-item${activeConvId === conv.id ? ' active' : ''}`}>
                    <button
                      type="button"
                      className="sidebar-load"
                      onClick={() => handleLoadConversation(conv)}
                      aria-current={activeConvId === conv.id ? 'page' : undefined}
                      title={`${conv.question}\n${datasetTitle}`}
                    >
                      <MessageSquare size={13} className="sidebar-item-icon" aria-hidden="true" />
                      <div className="sidebar-item-text">
                        <span className="sidebar-item-q">{conv.question}</span>
                        <span className="sidebar-item-dataset">{datasetMeta.name}</span>
                        <div className="sidebar-item-meta">
                          <span className="sidebar-item-time">{timeLabel(conv.timestamp)}</span>
                          {datasetMeta.alias && (
                            <span className="sidebar-item-alias">{datasetMeta.alias}</span>
                          )}
                        </div>
                      </div>
                    </button>
                    <button
                      className="sidebar-delete"
                      type="button"
                      onClick={() => handleDeleteConversation(conv.id)}
                      title={`Delete analysis: ${conv.question}`}
                      aria-label={`Delete analysis: ${conv.question}`}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                )})
            }
          </div>
        </aside>

        {/* ── Main content ─────────────────────────────────────────────────── */}
        <main className="main-content">

          {!hasDataset && (
            <div id="dataset-required-message" className="info-card" role="status">
              <Database className="info-icon" aria-hidden="true" />
              <p>Select or upload a dataset before running an analysis.</p>
            </div>
          )}

          {/* Error */}
          {appState === 'error' && (
            <div className="error-card" role="alert">
              <AlertCircle className="error-icon" aria-hidden="true" />
              <p>{error}</p>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="loading-state" role="status" aria-live="polite">
              <Loader2 className="animate-spin loading-icon" aria-hidden="true" />
              <p>
                {appState === 'loading_start'
                  ? 'Preprocessing data and building analysis plan...'
                  : 'Analyzing data and generating insights...'}
              </p>
            </div>
          )}

          {/* Plan approval */}
          {appState === 'pending_approval' && pendingPlan && (
            <PlanApprovalCard
              pendingPlan={pendingPlan}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          )}

          {/* Welcome */}
          {appState === 'idle' && (
            <WelcomeState onSuggestionClick={setQuestion} />
          )}

          {/* Dashboard — renders all sections (initial + follow-ups) */}
          {appState === 'complete' && dashboardSections.length > 0 && (
            <div key={activeConvId || 'live-dashboard'} className="dashboard-additive">
              {activeConversation && (
                <section className="dataset-context-card" aria-label="Dataset used for this analysis">
                  <div className="dataset-context-eyebrow">Dataset used</div>
                  <div className="dataset-context-title" title={activeDatasetMeta.name}>
                    {activeDatasetMeta.name}
                  </div>
                  {activeDatasetMeta.alias && (
                    <div
                      className="dataset-context-alias"
                      title={activeDatasetMeta.alias}
                    >
                      {activeDatasetMeta.alias}
                    </div>
                  )}
                </section>
              )}
              {dashboardSections.map((section, sIdx) => {
                const sectionKey = `${activeConvId || 'live'}-section-${sIdx}`;

                if (section.type === 'initial') {
                  return (
                    <div key={sectionKey} className="dashboard-grid">
                      <section className="charts-section">
                        <div className="card-header">
                          <LayoutDashboard className="card-icon" />
                          <h2>Visual Insights</h2>
                        </div>
                        <div className="charts-grid">
                          {section.charts?.length > 0 ? (
                            section.charts.map((chart, index) => {
                              const chartKey = `${sectionKey}:${chart.id || index}:${index}`;
                              const isHorizontal = chart.options?.plotOptions?.bar?.horizontal === true;
                              const catCount = chart.options?.xaxis?.categories?.length || 0;
                              const chartHeight = isHorizontal
                                ? Math.max(260, catCount * 32 + 50)
                                : 260;
                              const chartOptions = cloneResult(chart.options || {});
                              const chartSeries = cloneResult(chart.series || []);
                              return (
                                <div key={chartKey} className="chart-card">
                                  <h3>{chart.title || chart.options?.title?.text || `Chart ${index + 1}`}</h3>
                                  <Suspense fallback={<ChartFallback />}>
                                    <Chart
                                      key={chartKey}
                                      options={{
                                        ...chartOptions,
                                        theme: { mode: theme },
                                        chart: {
                                          ...(chartOptions.chart || {}),
                                          background: 'transparent',
                                          foreColor: theme === 'dark' ? '#a3a3a3' : '#6b7280',
                                          parentHeightOffset: 0,
                                          sparkline: { enabled: false },
                                        },
                                        grid: {
                                          ...(chartOptions.grid || {}),
                                          borderColor: theme === 'dark' ? '#333333' : '#e5e5e5',
                                          padding: { left: 8, right: 8, top: -10, bottom: -5 },
                                        },
                                        tooltip: {
                                          ...(chartOptions.tooltip || {}),
                                          theme,
                                          y: { formatter: (val) => formatTooltipNumber(val) },
                                        },
                                        xaxis: {
                                          ...(chartOptions.xaxis || {}),
                                          labels: {
                                            ...(chartOptions.xaxis?.labels || {}),
                                          },
                                        },
                                        yaxis: {
                                          ...(chartOptions.yaxis || {}),
                                          labels: {
                                            ...(chartOptions.yaxis?.labels || {}),
                                            formatter: (val) => formatChartNumber(val),
                                          },
                                        },
                                      }}
                                      series={chartSeries}
                                      type={chart.type || 'bar'}
                                      width="100%"
                                      height={chartHeight}
                                    />
                                  </Suspense>
                                </div>
                              );
                            })
                          ) : (
                            <p className="no-charts">No visual data generated for this query.</p>
                          )}
                        </div>
                      </section>

                      <div className="right-panel">
                        {section.forecasts?.length > 0 && (
                          <section className="forecast-section">
                            <div className="card-header">
                              <TrendingUp className="card-icon" />
                              <h2>Future Outlook</h2>
                            </div>
                            <div className="forecast-grid">
                              {section.forecasts.map((fc, i) => (
                                <ForecastCard key={`${sectionKey}:fc-${fc.forecast_id || i}`} fc={fc} />
                              ))}
                            </div>
                          </section>
                        )}

                        <section className="report-section">
                          <div className="card-header">
                            <FileText className="card-icon" />
                            <h2>Analysis Report</h2>
                          </div>
                          <div className="report-content">
                            <ReactMarkdown>{section.summary}</ReactMarkdown>
                          </div>
                        </section>
                      </div>
                    </div>
                  );
                }

                /* Follow-up section */
                return (
                  <div key={sectionKey} className="followup-section">
                    <div className="followup-divider">
                      <MessageSquare size={14} />
                      <span className="followup-question-label">{section.question}</span>
                    </div>
                    {section.charts?.length > 0 && (
                      <div className="followup-charts-grid">
                        {section.charts.map((chart, index) => {
                          const chartKey = `${sectionKey}:${chart.id || index}:${index}`;
                          const isHorizontal = chart.options?.plotOptions?.bar?.horizontal === true;
                          const catCount = chart.options?.xaxis?.categories?.length || 0;
                          const chartHeight = isHorizontal
                            ? Math.max(320, catCount * 38 + 60)
                            : 320;
                          const chartOptions = cloneResult(chart.options || {});
                          const chartSeries = cloneResult(chart.series || []);
                          return (
                            <div key={chartKey} className="chart-card">
                              <h3>{chart.title || chart.options?.title?.text || `Chart ${index + 1}`}</h3>
                              <Suspense fallback={<ChartFallback />}>
                                <Chart
                                  key={chartKey}
                                  options={{
                                    ...chartOptions,
                                    theme: { mode: theme },
                                    chart: {
                                      ...(chartOptions.chart || {}),
                                      background: 'transparent',
                                      foreColor: theme === 'dark' ? '#a3a3a3' : '#6b7280',
                                      parentHeightOffset: 0,
                                      sparkline: { enabled: false },
                                    },
                                    grid: {
                                      ...(chartOptions.grid || {}),
                                      borderColor: theme === 'dark' ? '#333333' : '#e5e5e5',
                                      padding: { left: 8, right: 8, top: -10, bottom: -5 },
                                    },
                                    tooltip: {
                                      ...(chartOptions.tooltip || {}),
                                      theme,
                                      y: { formatter: (val) => formatTooltipNumber(val) },
                                    },
                                    xaxis: {
                                      ...(chartOptions.xaxis || {}),
                                      labels: {
                                        ...(chartOptions.xaxis?.labels || {}),
                                      },
                                    },
                                    yaxis: {
                                      ...(chartOptions.yaxis || {}),
                                      labels: {
                                        ...(chartOptions.yaxis?.labels || {}),
                                        formatter: (val) => formatChartNumber(val),
                                      },
                                    },
                                  }}
                                  series={chartSeries}
                                  type={chart.type || 'bar'}
                                  width="100%"
                                  height={chartHeight}
                                />
                              </Suspense>
                            </div>
                          );
                        })}
                      </div>
                    )}
                    {section.forecasts?.length > 0 && (
                      <div className="forecast-grid" style={{ marginBottom: '1rem' }}>
                        {section.forecasts.map((fc, i) => (
                          <ForecastCard key={`${sectionKey}:fc-${fc.forecast_id || i}`} fc={fc} />
                        ))}
                      </div>
                    )}
                    {section.explanation && (
                      <div className="followup-explanation">
                        <ReactMarkdown>{section.explanation}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Follow-up loading indicator */}
              {followupLoading && (
                <div className="loading-state followup-loading" role="status" aria-live="polite">
                  <Loader2 className="animate-spin loading-icon" aria-hidden="true" />
                  <p>Analyzing follow-up question...</p>
                </div>
              )}

              {/* Follow-up input bar */}
              {sessionId && (
                <form onSubmit={handleFollowup} className="followup-form">
                  <label className="sr-only" htmlFor="followup-question">Ask a follow-up question</label>
                  <div className="followup-input-wrapper">
                    <MessageSquare size={16} className="followup-input-icon" aria-hidden="true" />
                    <input
                      id="followup-question"
                      type="text"
                      placeholder="Ask a follow-up about this data..."
                      value={activeFollowupQuestion}
                      onChange={(e) => {
                        if (!activeConvId) return;
                        const value = e.target.value;
                        setFollowupDrafts(prev => ({ ...prev, [activeConvId]: value }));
                      }}
                      disabled={followupLoading}
                    />
                  </div>
                  <button type="submit" aria-label="Send follow-up question" disabled={followupLoading || !activeFollowupQuestion.trim()}>
                    {followupLoading ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
                  </button>
                </form>
              )}

              <div ref={followupEndRef} />
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

export default App;
