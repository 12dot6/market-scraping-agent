import React from 'react'

export default function ResultsList(){
  return (
    <div className="bg-white p-4 rounded-lg shadow-sm">
      <h3 className="font-medium">Results — Run sample</h3>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-gray-600"><tr><th className="pb-2 text-left">Product</th><th className="pb-2">Status</th><th className="pb-2">Ingredients</th></tr></thead>
          <tbody>
            <tr className="border-t"><td className="py-2"><a className="text-indigo-600">Product A</a></td><td className="py-2">Completed</td><td className="py-2">12</td></tr>
            <tr className="border-t"><td className="py-2"><a className="text-indigo-600">Product B</a></td><td className="py-2">Partial</td><td className="py-2">8</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
