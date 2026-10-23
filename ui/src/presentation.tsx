import { useRef, type ReactNode } from 'react';

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
  const trigger=useRef<HTMLButtonElement>(null);
  return <><button className="action" ref={trigger} onClick={()=>dialog.current?.showModal()}>Открыть итоговый отчёт</button>
    <dialog className="report report-dialog" ref={dialog} aria-label="Итоговый отчёт" onClose={()=>trigger.current?.focus({preventScroll:true})}>
      <button className="action report-close" autoFocus onClick={()=>dialog.current?.close()}>Закрыть</button>
      <h2>Отчёт и источники</h2>{children}
    </dialog></>;
}
