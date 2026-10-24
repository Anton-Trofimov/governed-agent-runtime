import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

// Only explicit cross-panel navigation may move the mobile page.
export function revealEvent(container:HTMLElement,target:HTMLElement){
  target.querySelectorAll('details').forEach(detail=>{detail.open=true;});
  container.scrollTop+=target.getBoundingClientRect().top-container.getBoundingClientRect().top;
  const rect=target.getBoundingClientRect();
  if(window.innerWidth<=620&&(rect.top<0||rect.top>=window.innerHeight||rect.bottom<=0||rect.bottom>window.innerHeight)){
    container.closest('.chat,.journal')?.scrollIntoView?.({block:'start',behavior:'instant'});
  }
  target.tabIndex=-1;target.focus({preventScroll:true});
}

export function ReportDialog({children}:{children:ReactNode}){
  const dialog=useRef<HTMLDialogElement>(null);
  const [opened,setOpened]=useState(false);
  const trigger=useRef<HTMLButtonElement>(null);
  return <><button className="action" ref={trigger} onClick={()=>{setOpened(true);dialog.current?.showModal();}}>Открыть итоговый отчёт</button>
    <dialog className="report report-dialog" ref={dialog} aria-label="Итоговый отчёт" onClose={()=>{setOpened(false);trigger.current?.focus({preventScroll:true});}}>
      <button className="action report-close" autoFocus onClick={()=>dialog.current?.close()}>Закрыть</button>
      <h2>Отчёт и источники</h2>{opened&&<>{children}<p className="report-source-link"><a href="https://github.com/Anton-Trofimov/governed-agent-runtime">Исходный код и спецификации — GitHub</a></p></>}
    </dialog></>;
}

export function CompactComposer({text}:{text:string}){
  const field=useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(()=>{
    const element=field.current;if(!element)return;
    const size=()=>{element.style.height='auto';element.style.height=`${element.scrollHeight+2}px`;};
    size();window.addEventListener('resize',size);
    const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(entries=>{
      if(entries[0]?.contentRect.width!==width){width=entries[0]?.contentRect.width;size();}
    }):null;
    let width=element.getBoundingClientRect().width;observer?.observe(element);
    return()=>{window.removeEventListener('resize',size);observer?.disconnect();};
  },[text]);
  return <textarea ref={field} aria-label="Состояние диалога" disabled rows={1} value={text}/>;
}
