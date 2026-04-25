import React, {useState} from 'react'
import Button from '../ui/button'

export default function UrlInputPanel({onStart}){
  const [text, setText] = useState('')
  const [error, setError] = useState('')

  function handleStart(){
    const urls = text.split(/\r?\n/).map(s=>s.trim()).filter(Boolean)
    const invalid = urls.filter(u=>!/^https?:\/\/.+\..+/.test(u))
    if(invalid.length){ setError('Invalid URL found. Example: https://example.com/product/1'); return }
    setError('')
    onStart && onStart()
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm">
      <label className="block text-sm font-medium">Product URLs</label>
      <textarea rows={6} className="mt-2 p-2 border rounded-md w-full" value={text} onChange={e=>setText(e.target.value)} placeholder="https://example.com/product/1" />
      {error && <div className="text-red-600 text-sm mt-2">{error}</div>}
      <div className="mt-4">
        <Button onClick={handleStart}>Start Job</Button>
      </div>
    </div>
  )
}
