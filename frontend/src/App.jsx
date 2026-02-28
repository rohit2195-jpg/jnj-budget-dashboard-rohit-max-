import { useState, useEffect } from 'react';
import Chart from 'react-apexcharts';
import ReactMarkdown from 'react-markdown';
import {
  Search, LayoutDashboard, FileText, Loader2, AlertCircle,
  Plus, MessageSquare, Trash2, ClipboardList, CheckCircle, XCircle,
} from 'lucide-react';
import './App.css';

// ── localStorage helpers ──────────────────────────────────────────────────────
const STORAGE_KEY = 'budget-dashboard-conversations';

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

// ── App ───────────────────────────────────────────────────────────────────────
function App() {
  const [question, setQuestion]           = useState('');
  // 'idle' | 'loading_start' | 'pending_approval' | 'loading_resume' | 'complete' | 'error'
  const [appState, setAppState]           = useState('idle');
  const [data, setData]                   = useState(null);
  const [error, setError]                 = useState(null);
  const [threadId, setThreadId]           = useState(null);
  const [pendingPlan, setPendingPlan]     = useState(null);
  const [conversations, setConversations] = useState(loadConversations);
  const [activeConvId, setActiveConvId]   = useState(null);

  useEffect(() => { saveConversations(conversations); }, [conversations]);

  const loading = appState === 'loading_start' || appState === 'loading_resume';

  // ── sidebar actions ────────────────────────────────────────────────────────
  const handleNewChat = () => {
    setQuestion(''); setData(null); setError(null);
    setThreadId(null); setPendingPlan(null);
    setActiveConvId(null); setAppState('idle');
  };

  const handleLoadConversation = (conv) => {
    setQuestion(conv.question); setData(conv.data);
    setError(null); setThreadId(null); setPendingPlan(null);
    setActiveConvId(conv.id); setAppState('complete');
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
    setError(null); setData(null); setThreadId(null);
    setPendingPlan(null); setActiveConvId(null);

    try {
      const response = await fetch('http://localhost:5001/api/analyze/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
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
    const conv = { id: Date.now().toString(), question, timestamp: Date.now(), data: result };
    setConversations(prev => [conv, ...prev]);
    setActiveConvId(conv.id);
    setData(result);
    setAppState('complete');
  };

  const isInputDisabled = loading || appState === 'pending_approval';

  return (
    <div className="app-container">

      {/* ── Header (unchanged from original) ───────────────────────────── */}
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
      </header>

      {/* ── Body row: sidebar + main ────────────────────────────────────── */}
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

        {/* ── Main content (original, unchanged structure) ─────────────── */}
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
                <button className="btn-approve" onClick={handleApprove}>
                  <CheckCircle size={15} /> Approve &amp; Run
                </button>
                <button className="btn-reject" onClick={handleReject}>
                  <XCircle size={15} /> Reject
                </button>
              </div>
            </div>
          )}

          {/* Welcome */}
          {appState === 'idle' && (
            <div className="welcome-state">
              <LayoutDashboard size={64} className="welcome-icon" />
              <h2>Ready to Explore Spending Data?</h2>
              <p>Enter a question above to get a detailed report and visual dashboard.</p>
              <div className="suggestions">
                <button onClick={() => setQuestion('Show me the top 5 departments by spending')}>
                  "Top 5 departments by spending"
                </button>
                <button onClick={() => setQuestion('How much was spent on education in 2023?')}>
                  "Spending on education in 2023"
                </button>
                <button onClick={() => setQuestion('Compare spending across different sub-agencies')}>
                  "Compare sub-agency spending"
                </button>
              </div>
            </div>
          )}

          {/* Dashboard (charts on top, report below) */}
          {appState === 'complete' && data && (
            <div className="dashboard-grid">
              <section className="charts-section">
                <div className="card-header">
                  <LayoutDashboard className="card-icon" />
                  <h2>Visual Insights</h2>
                </div>
                <div className="charts-grid">
                  {data.graphs?.charts?.length > 0 ? (
                    data.graphs.charts.map((chart, index) => {
                      const safeOptions = JSON.parse(JSON.stringify(chart.options || {}));
                      if (safeOptions?.xaxis?.labels?.formatter)  delete safeOptions.xaxis.labels.formatter;
                      if (safeOptions?.tooltip?.y?.formatter)     delete safeOptions.tooltip.y.formatter;
                      return (
                        <div key={chart.id || index} className="chart-card">
                          <h3>{chart.title || chart.options?.title?.text || `Chart ${index + 1}`}</h3>
                          <Chart
                            options={{
                              ...(chart.options || {}),
                              xaxis: {
                                ...(chart.options?.xaxis || {}),
                                labels: { ...(chart.options?.xaxis?.labels || {}), formatter: undefined },
                              },
                              tooltip: {
                                ...(chart.options?.tooltip || {}),
                                y: { ...(chart.options?.tooltip?.y || {}), formatter: undefined },
                              },
                            }}
                            series={chart.series || []}
                            type={chart.type || 'bar'}
                            width="100%"
                            height="450"
                          />
                        </div>
                      );
                    })
                  ) : (
                    <p className="no-charts">No visual data generated for this query.</p>
                  )}
                </div>
              </section>

              <section className="report-section">
                <div className="card-header">
                  <FileText className="card-icon" />
                  <h2>Analysis Report</h2>
                </div>
                <div className="report-content">
                  <ReactMarkdown>{data.summary}</ReactMarkdown>
                </div>
              </section>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

export default App;
