function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-semibold">Sentinel</h1>

          <span className="text-sm text-slate-400">
            Developer Infrastructure
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-12">
        <h2 className="text-4xl font-bold tracking-tight">
          Welcome to Sentinel
        </h2>

        <p className="mt-4 max-w-2xl text-slate-400">
          Monitor your deployed services, track uptime and performance,
          manage projects, and keep sleep-prone services warm.
        </p>
      </main>
    </div>
  )
}

export default App