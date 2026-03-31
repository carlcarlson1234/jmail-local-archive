import Link from 'next/link';

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <h1>Jmail Local Archive</h1>
        <p>
          Your complete local copy of the Jmail public dataset.
          Search emails, documents, photos, messages, and more — all from your own database.
        </p>
      </section>

      <div className="search-container" style={{ marginTop: '20px' }}>
        <form action="/search" method="get" className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            name="q"
            placeholder="Search emails, documents, people, messages..."
            autoFocus
          />
        </form>
      </div>

      <div className="card-grid" style={{ marginTop: '40px' }}>
        <Link href="/search?type=emails" className="card" style={{ textDecoration: 'none' }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📧</div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '4px' }}>Emails</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            1.7M+ emails from the Epstein archive
          </p>
        </Link>

        <Link href="/search?type=documents" className="card" style={{ textDecoration: 'none' }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📄</div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '4px' }}>Documents</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            1.4M+ document pages with full text
          </p>
        </Link>

        <Link href="/search?type=photos" className="card" style={{ textDecoration: 'none' }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📷</div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '4px' }}>Photos</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            18K+ photos from DOJ releases
          </p>
        </Link>

        <Link href="/search?type=people" className="card" style={{ textDecoration: 'none' }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>👤</div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '4px' }}>People</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            473 identified individuals
          </p>
        </Link>

        <Link href="/search?type=messages" className="card" style={{ textDecoration: 'none' }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>💬</div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '4px' }}>iMessages</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            4,500+ messages across 15 conversations
          </p>
        </Link>

        <Link href="/admin" className="card" style={{ textDecoration: 'none' }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>⚙️</div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '4px' }}>Admin</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Mirror status, row counts, and system health
          </p>
        </Link>
      </div>
    </>
  );
}
