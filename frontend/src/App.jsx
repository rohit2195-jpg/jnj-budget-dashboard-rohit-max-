import { useState, useEffect, useRef } from 'react';
import Chart from 'react-apexcharts';
import ReactMarkdown from 'react-markdown';
import {
  Search, LayoutDashboard, FileText, Loader2, AlertCircle,
  Plus, MessageSquare, Trash2, ClipboardList, CheckCircle, XCircle,
  TrendingUp, TrendingDown, Minus, Sun, Moon, Upload, Database,
  Send,
} from 'lucide-react';
import './App.css';

// ── localStorage helpers ──────────────────────────────────────────────────────
const STORAGE_KEY = 'budget-dashboard-conversations';
const THEME_KEY   = 'budget-dashboard-theme';

function loadConversations() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
  catch { return []; }
}

function saveConversations(convs) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(convs.slice(0, 50))); }
  catch { /* ignore quota errors */ }
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
        <button className="btn-approve" onClick={onApprove}>
          <CheckCircle size={15} /> Approve &amp; Run
        </button>
        <button className="btn-reject" onClick={onReject}>
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
      <h2>Ready to Explore Spending Data?</h2>
      <p>Enter a question above to get a detailed report and visual dashboard.</p>
      <div className="suggestions">
        <button onClick={() => onSuggestionClick('Show me the top 5 departments by spending')}>
          "Top 5 departments by spending"
        </button>
        <button onClick={() => onSuggestionClick('How much was spent on education in 2023?')}>
          "Spending on education in 2023"
        </button>
        <button onClick={() => onSuggestionClick('Compare spending across different sub-agencies')}>
          "Compare sub-agency spending"
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

  // Follow-up state
  const [sessionId, setSessionId]                   = useState(null);
  const [dashboardSections, setDashboardSections]   = useState([]);
  const [followupQuestion, setFollowupQuestion]     = useState('');
  const [followupLoading, setFollowupLoading]       = useState(false);
  const followupEndRef = useRef(null);

  const fetchDatasets = async () => {
    try {
      const res = await fetch('http://localhost:5001/api/datasets');
      const json = await res.json();
      setDatasets(json.datasets || []);
      if (!selectedDataset && json.datasets?.length > 0) {
        setSelectedDataset(json.datasets[0].path);
      }
    } catch { /* ignore — backend may not be running */ }
  };

  useEffect(() => { fetchDatasets(); }, []);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('http://localhost:5001/api/upload', { method: 'POST', body: formData });
      const text = await res.text();
      let json;
      try { json = JSON.parse(text); } catch { throw new Error('Upload failed — server returned an unexpected response'); }
      if (!res.ok) throw new Error(json.error || 'Upload failed');
      await fetchDatasets();
      setSelectedDataset(json.path);
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
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const loading = appState === 'loading_start' || appState === 'loading_resume';

  // ── sidebar actions ────────────────────────────────────────────────────────
  const handleNewChat = () => {
    setQuestion(''); setError(null);
    setThreadId(null); setPendingPlan(null);
    setActiveConvId(null); setAppState('idle');
    setSessionId(null); setDashboardSections([]);
    setFollowupQuestion('');
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
    setFollowupQuestion('');
  };

  const handleDeleteConversation = (id) => {
    setConversations(prev => prev.filter(c => c.id !== id));
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
      const response = await fetch('http://localhost:5001/api/analyze/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, filepath: selectedDataset || undefined }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Failed to fetch data from the server');
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
      const response = await fetch('http://localhost:5001/api/analyze/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, approved: true }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Failed to fetch data from the server');
      if (result.status === 'error') throw new Error(result.error);
      finishAnalysis(result);
    } catch (err) {
      setError(err.message);
      setAppState('error');
    }
  };

  const handleReject = async () => {
    try {
      await fetch('http://localhost:5001/api/analyze/resume', {
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
    };
    setConversations(prev => [conv, ...prev]);
    setActiveConvId(conv.id);
    setDashboardSections(sections);
    setSessionId(snapshot.session_id || null);
    setAppState('complete');
  };

  // ── follow-up flow ────────────────────────────────────────────────────
  const handleFollowup = async (e) => {
    e.preventDefault();
    if (!followupQuestion.trim() || !sessionId || followupLoading) return;
    setFollowupLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5001/api/analyze/followup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: followupQuestion, session_id: sessionId }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Follow-up failed');

      const newSection = {
        type: 'followup',
        question: followupQuestion,
        charts: result.new_charts || [],
        forecasts: result.forecast_output?.forecasts || [],
        explanation: result.explanation,
      };
      setDashboardSections(prev => {
        const updated = [...prev, newSection];
        // Also update the saved conversation
        setConversations(convs => convs.map(c =>
          c.id === activeConvId ? { ...c, sections: cloneResult(updated) } : c
        ));
        return updated;
      });
      setFollowupQuestion('');
      // Auto-scroll to new section
      setTimeout(() => followupEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch (err) {
      setError(err.message);
    } finally {
      setFollowupLoading(false);
    }
  };

  const isInputDisabled = loading || appState === 'pending_approval';

  return (
    <div className="app-container">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header className="header">
        <div className="logo-section">
          <LayoutDashboard className="logo-icon" />
          <h1>Budget Dashboard</h1>
        </div>
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-wrapper">
            <Search className="search-icon" />
            <input
              type="text"
              placeholder="Ask a question about US spending data..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={isInputDisabled}
            />
          </div>
          <button type="submit" disabled={isInputDisabled}>
            {loading ? <Loader2 className="animate-spin" /> : 'Analyze'}
          </button>
        </form>
        <div className="dataset-picker">
          <Database size={16} className="dataset-icon" />
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            disabled={loading || appState === 'pending_approval'}
          >
            {datasets.length === 0 && <option value="">No datasets found</option>}
            {datasets.map(ds => (
              <option key={ds.path} value={ds.path}>{ds.name} ({(ds.size / 1024).toFixed(0)} KB)</option>
            ))}
          </select>
          <label className="upload-btn" title="Upload CSV or JSON">
            {uploading ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
            <input type="file" accept=".csv,.json" onChange={handleUpload} hidden disabled={uploading} />
          </label>
        </div>
        <div className="header-actions">
          <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      {/* ── Body row: sidebar + main ──────────────────────────────────────── */}
      <div className="body-row">

        {/* Sidebar */}
        <aside className="sidebar">
          <button className="new-analysis-btn" onClick={handleNewChat}>
            <Plus size={15} />
            New Analysis
          </button>

          <div className="sidebar-list">
            {conversations.length === 0
              ? <p className="sidebar-empty">No analyses yet</p>
              : conversations.map(conv => (
                  <div
                    key={conv.id}
                    className={`sidebar-item${activeConvId === conv.id ? ' active' : ''}`}
                    onClick={() => handleLoadConversation(conv)}
                  >
                    <MessageSquare size={13} className="sidebar-item-icon" />
                    <div className="sidebar-item-text">
                      <span className="sidebar-item-q">{conv.question}</span>
                      <span className="sidebar-item-time">{timeLabel(conv.timestamp)}</span>
                    </div>
                    <button
                      className="sidebar-delete"
                      onClick={e => { e.stopPropagation(); handleDeleteConversation(conv.id); }}
                      title="Delete"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
            }
          </div>
        </aside>

        {/* ── Main content ─────────────────────────────────────────────────── */}
        <main className="main-content">

          {/* Error */}
          {appState === 'error' && (
            <div className="error-card">
              <AlertCircle className="error-icon" />
              <p>{error}</p>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="loading-state">
              <Loader2 className="animate-spin loading-icon" />
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
                                ? Math.max(320, catCount * 38 + 60)
                                : 320;
                              const chartOptions = cloneResult(chart.options || {});
                              const chartSeries = cloneResult(chart.series || []);
                              return (
                                <div key={chartKey} className="chart-card">
                                  <h3>{chart.title || chart.options?.title?.text || `Chart ${index + 1}`}</h3>
                                  <Chart
                                    key={chartKey}
                                    options={{
                                      ...chartOptions,
                                      theme: { mode: theme, palette: 'palette1' },
                                      chart: {
                                        ...(chartOptions.chart || {}),
                                        background: 'transparent',
                                        foreColor: theme === 'dark' ? '#94a3b8' : '#64748b',
                                      },
                                      grid: {
                                        ...(chartOptions.grid || {}),
                                        borderColor: theme === 'dark' ? '#334155' : '#e2e8f0',
                                      },
                                      tooltip: {
                                        ...(chartOptions.tooltip || {}),
                                        theme,
                                        y: { formatter: undefined },
                                      },
                                      xaxis: {
                                        ...(chartOptions.xaxis || {}),
                                        labels: {
                                          ...(chartOptions.xaxis?.labels || {}),
                                          formatter: undefined,
                                        },
                                      },
                                    }}
                                    series={chartSeries}
                                    type={chart.type || 'bar'}
                                    width="100%"
                                    height={chartHeight}
                                  />
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
                              <Chart
                                key={chartKey}
                                options={{
                                  ...chartOptions,
                                  theme: { mode: theme, palette: 'palette1' },
                                  chart: {
                                    ...(chartOptions.chart || {}),
                                    background: 'transparent',
                                    foreColor: theme === 'dark' ? '#94a3b8' : '#64748b',
                                  },
                                  grid: {
                                    ...(chartOptions.grid || {}),
                                    borderColor: theme === 'dark' ? '#334155' : '#e2e8f0',
                                  },
                                  tooltip: {
                                    ...(chartOptions.tooltip || {}),
                                    theme,
                                    y: { formatter: undefined },
                                  },
                                  xaxis: {
                                    ...(chartOptions.xaxis || {}),
                                    labels: {
                                      ...(chartOptions.xaxis?.labels || {}),
                                      formatter: undefined,
                                    },
                                  },
                                }}
                                series={chartSeries}
                                type={chart.type || 'bar'}
                                width="100%"
                                height={chartHeight}
                              />
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
                <div className="loading-state followup-loading">
                  <Loader2 className="animate-spin loading-icon" />
                  <p>Analyzing follow-up question...</p>
                </div>
              )}

              {/* Follow-up input bar */}
              {sessionId && (
                <form onSubmit={handleFollowup} className="followup-form">
                  <div className="followup-input-wrapper">
                    <MessageSquare size={16} className="followup-input-icon" />
                    <input
                      type="text"
                      placeholder="Ask a follow-up about this data..."
                      value={followupQuestion}
                      onChange={(e) => setFollowupQuestion(e.target.value)}
                      disabled={followupLoading}
                    />
                  </div>
                  <button type="submit" disabled={followupLoading || !followupQuestion.trim()}>
                    {followupLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
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
