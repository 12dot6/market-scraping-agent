import React, {useState} from 'react'
import UrlInputPanel from './components/UrlInputPanel'
import ProgressBoard from './components/ProgressBoard'
import ResultsList from './components/ResultsList'
import IngredientCard from './components/IngredientCard'

export default function App(){
  const [view, setView] = useState('dashboard')
  const [runState, setRunState] = useState({processed:0,total:12,status:'idle'})

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold">Formulation Wiki — Prototype</h1>
          <nav className="mt-3 space-x-3 text-sm">
            <button className="text-indigo-600" onClick={()=>setView('dashboard')}>Dashboard</button>
            <button className="text-indigo-600" onClick={()=>setView('submit')}>Submit Job</button>
            <button className="text-indigo-600" onClick={()=>setView('results')}>Results</button>
          </nav>
        </header>

        {view === 'dashboard' && (
          <>
            <ProgressBoard runState={runState} setRunState={setRunState} />
          </>
        )}

        {view === 'submit' && (
          <UrlInputPanel onStart={()=>{ setRunState({processed:0,total:12,status:'running'}); setView('dashboard')}} />
        )}

        {view === 'results' && (
          <ResultsList />
        )}

        {view === 'ingredient' && (
          <IngredientCard />
        )}
      </div>
    </div>
  )
}
