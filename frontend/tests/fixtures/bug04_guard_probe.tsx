// Browser-only regression probe. Not imported by the product entry point.
import { useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { confirmLeave, useFormGuard } from '../../src/workspace/ui'

export function mountGuardProbe() {
  const host=document.createElement('div')
  document.body.append(host)
  const root=createRoot(host)
  const handles: Record<string,()=>void>={}
  function Probe({name}:{name:string}) {
    const guard=useFormGuard(true,false,()=>{})
    useEffect(()=>{handles[name]=guard.markSaved},[guard.markSaved,name])
    return <span>Guard {name}</span>
  }
  root.render(<><Probe name="a"/><Probe name="b"/></>)
  return {ready:()=>!!handles.a&&!!handles.b,saveA:()=>handles.a(),saveB:()=>handles.b(),leave:confirmLeave,dispose:()=>{root.unmount();host.remove()}}
}
