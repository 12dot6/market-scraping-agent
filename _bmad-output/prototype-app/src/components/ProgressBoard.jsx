import React, {useEffect} from 'react'

export default function ProgressBoard({runState, setRunState}){
  useEffect(()=>{
    if(runState.status === 'running'){
      const id = setInterval(()=>{
        setRunState(prev=>{
          const next = Math.min(prev.total, prev.processed + Math.ceil(Math.random()*2))
          if(next >= prev.total) return {...prev, processed: next, status:'complete'}
          return {...prev, processed: next, status:'running'}
        })
      },600)
      return ()=>clearInterval(id)
    }
  },[runState.status])

  const {processed=0,total=12,status='idle'} = runState || {}
  return (
    <div className="bg-white p-4 rounded-lg shadow-sm">
      <h3 className="font-medium">Live Progress</h3>
      <p className="mt-2 text-sm">Processed: {processed} / {total} • Status: {status}</p>
    </div>
  )
}
