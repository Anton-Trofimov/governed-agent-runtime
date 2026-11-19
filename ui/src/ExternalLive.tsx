import { useEffect, useState } from 'react';
import { observeAvailability, type Availability } from './externalLive';

export function ExternalLive({origin}:{origin:string}) {
  const [availability,setAvailability]=useState<Availability>('unavailable');
  useEffect(()=>{setAvailability('unavailable');return observeAvailability(origin,setAvailability);},[origin]);
  return <div className="external-live">
    {availability==='available' && <a className="action" href={`${origin}/`} target="_blank" rel="noopener noreferrer">Живой режим</a>}
    <p className="subtle" role="status">{availability==='available'
      ? 'Интерактивный simulator без вызова LLM — откроется на отдельной странице.'
      : availability==='busy' ? 'Живой режим занят. Вы можете посмотреть сохранённый пример.'
      : 'Живой режим сейчас недоступен. Вы можете посмотреть сохранённый пример.'}</p>
  </div>;
}
