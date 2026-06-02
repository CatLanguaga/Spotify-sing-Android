export function Footer() {
  return (
    <footer>
      <div>© {new Date().getFullYear()} Spotify Sing · Self-hosted</div>
      <div className="links">
        <a href="https://github.com" target="_blank" rel="noreferrer">GitHub</a>
        <a href="/docs" target="_blank" rel="noreferrer">API Docs</a>
        <span>Powered by Spotify Web API</span>
      </div>
    </footer>
  )
}
