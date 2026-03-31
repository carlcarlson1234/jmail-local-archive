import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Jmail Local Archive",
  description: "Local-first archival and query platform for the Jmail ecosystem",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="app-header">
            <h1>Jmail Local Archive</h1>
            <nav className="app-nav">
              <a href="/">Home</a>
              <a href="/search">Search</a>
              <a href="/admin">Admin</a>
            </nav>
          </header>
          <main className="app-main">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
