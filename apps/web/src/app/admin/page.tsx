'use client';

import { useState, useEffect } from 'react';

interface Stats {
  rowCounts: Record<string, number>;
  mirrorStatus: Array<{ status: string; count: number }>;
  assetStatus: Array<{ status: string; count: number }>;
  lastIngest: any;
}

export default function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/stats').then(r => r.json()).catch(() => null),
      fetch('/api/health').then(r => r.json()).catch(() => null),
    ]).then(([s, h]) => {
      setStats(s);
      setHealth(h);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="loading">Loading admin data</div>;

  const rows = stats?.rowCounts || {};
  const mainTables = [
    { key: 'emails', label: 'Emails', icon: '📧' },
    { key: 'email_recipients', label: 'Email Recipients', icon: '👥' },
    { key: 'documents', label: 'Documents', icon: '📄' },
    { key: 'document_fulltext', label: 'Document Fulltext', icon: '📝' },
    { key: 'photos', label: 'Photos', icon: '📷' },
    { key: 'people', label: 'People', icon: '👤' },
    { key: 'photo_faces', label: 'Photo Faces', icon: '😀' },
    { key: 'imessage_conversations', label: 'Conversations', icon: '💬' },
    { key: 'imessage_messages', label: 'Messages', icon: '💬' },
    { key: 'star_counts', label: 'Star Counts', icon: '⭐' },
    { key: 'release_batches', label: 'Release Batches', icon: '📦' },
  ];

  return (
    <>
      <div className="detail-header">
        <h1>System Admin</h1>
        <div className="detail-meta">
          <span>
            Database:{' '}
            <span className={`status-badge ${health?.status === 'ok' ? 'ok' : 'error'}`}>
              {health?.status || 'unknown'}
            </span>
          </span>
          {stats?.lastIngest && (
            <span>Last ingest: {new Date(stats.lastIngest.started_at || stats.lastIngest.startedAt).toLocaleString()}</span>
          )}
        </div>
      </div>

      <div className="detail-section">
        <h2>Row Counts</h2>
        <div className="stats-grid">
          {mainTables.map(t => (
            <div key={t.key} className="stat-card">
              <div style={{ fontSize: '1.5rem', marginBottom: '4px' }}>{t.icon}</div>
              <div className="stat-value">{(rows[t.key] ?? 0).toLocaleString()}</div>
              <div className="stat-label">{t.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="detail-section">
        <h2>Mirror Status</h2>
        <table className="data-table">
          <thead>
            <tr><th>Status</th><th>Count</th></tr>
          </thead>
          <tbody>
            {(stats?.mirrorStatus || []).map((m: any, i: number) => (
              <tr key={i}>
                <td>
                  <span className={`status-badge ${m.status === 'downloaded' || m.status === 'verified' ? 'ok' : 'warning'}`}>
                    {m.status}
                  </span>
                </td>
                <td>{m.count}</td>
              </tr>
            ))}
            {(!stats?.mirrorStatus || stats.mirrorStatus.length === 0) && (
              <tr><td colSpan={2} style={{ color: 'var(--text-muted)' }}>No mirror data yet</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="detail-section">
        <h2>Asset Registry</h2>
        <table className="data-table">
          <thead>
            <tr><th>Status</th><th>Count</th></tr>
          </thead>
          <tbody>
            {(stats?.assetStatus || []).map((a: any, i: number) => (
              <tr key={i}>
                <td>
                  <span className={`status-badge ${a.status === 'downloaded' ? 'ok' : a.status === 'discovered' ? 'warning' : 'error'}`}>
                    {a.status}
                  </span>
                </td>
                <td>{a.count}</td>
              </tr>
            ))}
            {(!stats?.assetStatus || stats.assetStatus.length === 0) && (
              <tr><td colSpan={2} style={{ color: 'var(--text-muted)' }}>No asset data yet</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="detail-section">
        <h2>Infrastructure Tables</h2>
        <table className="data-table">
          <thead>
            <tr><th>Table</th><th>Rows</th></tr>
          </thead>
          <tbody>
            {[
              { key: 'mirrored_files', label: 'Mirrored Files' },
              { key: 'asset_registry', label: 'Asset Registry' },
            ].map(t => (
              <tr key={t.key}>
                <td>{t.label}</td>
                <td>{(rows[t.key] ?? 0).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
