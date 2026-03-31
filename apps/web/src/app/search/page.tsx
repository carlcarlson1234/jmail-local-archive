'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

interface SearchResult {
  entityType: string;
  entityId: string;
  title: string;
  snippet: string;
  date: string | null;
  source: string | null;
  score: number;
}

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const initialType = searchParams.get('type') || 'all';

  const [query, setQuery] = useState(initialQuery);
  const [type, setType] = useState(initialType);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = async (q: string, t: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&type=${t}&limit=50`);
      const data = await res.json();
      setResults(data.results || []);
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (initialQuery) doSearch(initialQuery, initialType);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doSearch(query, type);
    window.history.replaceState(null, '', `/search?q=${encodeURIComponent(query)}&type=${type}`);
  };

  const types = ['all', 'emails', 'documents', 'messages', 'photos', 'people'];
  const detailUrl = (r: SearchResult) => {
    const map: Record<string, string> = {
      email: `/api/emails/${r.entityId}`,
      document: `/api/documents/${r.entityId}`,
      person: `/api/people/${r.entityId}`,
      photo: `/api/photos/${r.entityId}`,
      message: `/api/messages/${r.entityId}`,
    };
    return map[r.entityType] || '#';
  };

  return (
    <>
      <div className="search-container">
        <form onSubmit={handleSubmit} className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search emails, documents, people, messages..."
            autoFocus
          />
        </form>
        <div className="search-filters">
          {types.map(t => (
            <button
              key={t}
              className={`filter-btn ${type === t ? 'active' : ''}`}
              onClick={() => { setType(t); if (query) doSearch(query, t); }}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading && <div className="loading">Searching</div>}

      {!loading && searched && results.length === 0 && (
        <div className="empty-state">
          <div className="icon">🔍</div>
          <p>No results found for &ldquo;{query}&rdquo;</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '16px' }}>
            {results.length} results
          </p>
          <div className="results-list">
            {results.map((r, i) => (
              <a key={i} href={detailUrl(r)} className="result-item" target="_blank">
                <span className={`result-type ${r.entityType}`}>{r.entityType}</span>
                <div className="result-title">{r.title}</div>
                <div className="result-snippet" dangerouslySetInnerHTML={{ __html: r.snippet }} />
                <div className="result-meta">
                  {r.date && <span>📅 {new Date(r.date).toLocaleDateString()}</span>}
                  {r.source && <span>📁 {r.source}</span>}
                  <span>⭐ {r.score.toFixed(3)}</span>
                </div>
              </a>
            ))}
          </div>
        </>
      )}
    </>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="loading">Loading search</div>}>
      <SearchContent />
    </Suspense>
  );
}
