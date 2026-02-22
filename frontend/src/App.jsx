import { useState } from 'react';
import Chart from 'react-apexcharts';
import ReactMarkdown from 'react-markdown';
import { Search, LayoutDashboard, FileText, Loader2, AlertCircle } from 'lucide-react';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await fetch('http://localhost:5001/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch data from the server');
      }

      const result = await response.json();
      if (result.success) {
        setData(result);
      } else {
        throw new Error(result.error || 'An unknown error occurred');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
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
              disabled={loading}
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? <Loader2 className="animate-spin" /> : 'Analyze'}
          </button>
        </form>
      </header>

      <main className="main-content">
        {error && (
          <div className="error-card">
            <AlertCircle className="error-icon" />
            <p>{error}</p>
          </div>
        )}

        {loading && (
          <div className="loading-state">
            <Loader2 className="animate-spin loading-icon" />
            <p>Analyzing data and generating insights...</p>
          </div>
        )}

        {!loading && !data && !error && (
          <div className="welcome-state">
            <LayoutDashboard size={64} className="welcome-icon" />
            <h2>Ready to Explore Spending Data?</h2>
            <p>Enter a question above to get a detailed report and visual dashboard.</p>
            <div className="suggestions">
              <button onClick={() => {setQuestion('Show me the top 5 departments by spending'); }}>"Top 5 departments by spending"</button>
              <button onClick={() => {setQuestion('How much was spent on education in 2023?'); }}>"Spending on education in 2023"</button>
              <button onClick={() => {setQuestion('Compare spending across different sub-agencies'); }}>"Compare sub-agency spending"</button>
            </div>
          </div>
        )}

        {data && (
          <div className="dashboard-grid">
            <section className="report-section">
              <div className="card-header">
                <FileText className="card-icon" />
                <h2>Analysis Report</h2>
              </div>
              <div className="report-content">
                <ReactMarkdown>{data.summary}</ReactMarkdown>
              </div>
            </section>

            <section className="charts-section">
              <div className="card-header">
                <LayoutDashboard className="card-icon" />
                <h2>Visual Insights</h2>
              </div>
              <div className="charts-grid">
{data.graphs.charts && data.graphs.charts.length > 0 ? (
  data.graphs.charts.map((chart, index) => {
    
    // 🔥 Strip formatter strings (quick fix)
    const safeOptions = JSON.parse(JSON.stringify(chart.options || {}));

    if (safeOptions?.xaxis?.labels?.formatter) {
      delete safeOptions.xaxis.labels.formatter;
    }

    if (safeOptions?.tooltip?.y?.formatter) {
      delete safeOptions.tooltip.y.formatter;
    }

    return (
      <div key={chart.id || index} className="chart-card">
        <h3>
          {chart.title || chart.options?.title?.text || `Chart ${index + 1}`}
        </h3>
        <Chart
          options={{
            ...(chart.options || {}),
            xaxis: {
              ...(chart.options?.xaxis || {}),
              labels: {
                ...(chart.options?.xaxis?.labels || {}),
                formatter: undefined
              }
            },
            tooltip: {
              ...(chart.options?.tooltip || {}),
              y: {
                ...(chart.options?.tooltip?.y || {}),
                formatter: undefined
              }
            }
          }}
          series={chart.series || []}
          type={chart.type || 'bar'}
          width="100%"
          height="350"
        />
      </div>
    );
  })
) : (
  <p className="no-charts">No visual data generated for this query.</p>
)}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
