import { useEffect, useId, useRef, useState } from 'react'
import { useTheme } from '../theme/ThemeContext'
import type { ThemePreference } from '../theme/ThemeContext'
import { Coffee, Monitor, Moon, Sun } from 'lucide-react'

interface ThemeOption {
  key: ThemePreference
  label: string
  shortLabel: string
  Icon: typeof Sun
}

const THEME_OPTIONS: ThemeOption[] = [
  { key: 'system', label: 'Tự động theo thiết bị', shortLabel: 'Hệ thống', Icon: Monitor },
  { key: 'light', label: 'Giao diện sáng rõ', shortLabel: 'Sáng', Icon: Sun },
  { key: 'dark', label: 'Giao diện nền tối', shortLabel: 'Tối', Icon: Moon },
  { key: 'soft', label: 'Giao diện dịu mắt (ngà ấm)', shortLabel: 'Dịu mắt', Icon: Coffee },
]

export function ThemeSwitcher({className=''}:{className?:string}) {
  const {themePreference,setTheme}=useTheme()
  const [open,setOpen]=useState(false),[focused,setFocused]=useState(0)
  const root=useRef<HTMLDivElement>(null),trigger=useRef<HTMLButtonElement>(null),buttons=useRef<(HTMLButtonElement|null)[]>([])
  const id=useId(),selected=THEME_OPTIONS.findIndex(o=>o.key===themePreference),current=THEME_OPTIONS[selected],Icon=current.Icon
  function close(restore=false){setOpen(false);if(restore)trigger.current?.focus()}
  function show(index=selected){setFocused(index);setOpen(true)}
  useEffect(()=>{if(open)buttons.current[focused]?.focus()},[open,focused])
  useEffect(()=>{
    if(!open)return
    const outside=(event:PointerEvent)=>{if(!root.current?.contains(event.target as Node))close()}
    document.addEventListener('pointerdown',outside,true)
    return ()=>document.removeEventListener('pointerdown',outside,true)
  },[open])
  function handleKeyDown(event:React.KeyboardEvent,index:number){
    if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close(true);return}
    if(event.key==='Enter'||event.key===' '){event.preventDefault();setTheme(THEME_OPTIONS[index].key);close(true);return}
    const next=event.key==='Home'?0:event.key==='End'?THEME_OPTIONS.length-1:event.key==='ArrowDown'||event.key==='ArrowRight'?(index+1)%THEME_OPTIONS.length:event.key==='ArrowUp'||event.key==='ArrowLeft'?(index-1+THEME_OPTIONS.length)%THEME_OPTIONS.length:-1
    if(next>=0){event.preventDefault();setFocused(next)}
  }
  return <div ref={root} className={`theme-switcher theme-picker ${className}`} onBlur={event=>{if(!event.currentTarget.contains(event.relatedTarget as Node))close()}}>
    <button ref={trigger} type="button" className="theme-trigger" aria-haspopup="menu" aria-expanded={open} aria-controls={open?id:undefined} onClick={()=>open?close():show()} onKeyDown={event=>{if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();show(event.key==='ArrowDown'?selected:THEME_OPTIONS.length-1)}else if(event.key==='Escape')close(true)}}><Icon size={17} aria-hidden="true"/><span>Giao diện</span><small>{current.shortLabel}</small></button>
    {open&&<div id={id} role="menu" aria-label="Chọn giao diện hiển thị" className="theme-popover">{THEME_OPTIONS.map((option,index)=>{const OptionIcon=option.Icon;return <button key={option.key} ref={node=>{buttons.current[index]=node}} role="menuitemradio" aria-checked={option.key===themePreference} type="button" tabIndex={index===focused?0:-1} onKeyDown={event=>handleKeyDown(event,index)} onFocus={()=>setFocused(index)} onClick={()=>{setTheme(option.key);close(true)}}><OptionIcon size={17} aria-hidden="true"/><span>{option.label}</span>{option.key===themePreference&&<strong aria-hidden="true">✓</strong>}</button>})}</div>}
  </div>
}
