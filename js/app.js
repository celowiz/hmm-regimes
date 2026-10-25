(()=>{
const COL={queda:'#f97366',lateral:'#e5b454',alta:'#2dd4bf'};
const NAME={queda:'Estresse',lateral:'Intermediário',alta:'Calmo'};
const HINT={queda:'alta volatilidade · tende a quedas',lateral:'volatilidade média · lateral/transição',alta:'baixa volatilidade · tende a altas'};
const MOM={ibov:[['2002-06-01','2002-12-31','Eleição 2002','Risco‑país dispara com a incerteza eleitoral e o real se desvaloriza.'],['2008-08-15','2009-03-31','Crise 2008','Quebra do Lehman: o Ibovespa cai mais de 50% do topo.'],['2015-01-01','2016-02-29','Recessão 2015','Recessão, perda do grau de investimento e crise política.'],['2017-05-10','2017-06-30','Joesley 05/2017','Divulgação do áudio de Joesley Batista: circuit breaker em 18/05.'],['2020-02-15','2020-06-30','Covid 03/2020','Seis circuit breakers em março de 2020.'],['2022-08-01','2022-12-31','Eleição 2022','Volatilidade em torno da eleição e da transição fiscal.']],
spx:[['2001-09-01','2002-12-31','Bolha ponto‑com','Fim da bolha de tecnologia e 11 de setembro; mercado baixista até out/2002.'],['2008-08-15','2009-03-31','Lehman 09/2008','Crise financeira global; mínima em março de 2009.'],['2011-07-15','2011-11-30','Rebaixamento 2011','S&P rebaixa a nota dos EUA e a crise do euro se agrava.'],['2020-02-15','2020-06-30','Covid 03/2020','Queda de ~34% em cinco semanas, a mais rápida da história.'],['2022-01-01','2022-12-31','Bear 2022','Inflação alta e juros subindo: mercado baixista o ano todo.'],['2025-03-15','2025-05-31','Tarifas 04/2025','Anúncio de tarifas em abril de 2025 derruba as bolsas.']]};
const S={mk:'ibov',k:3,f:'d',r:0,sm:false,mom:null},cache={};let D,meta,view;
const $=id=>document.getElementById(id),pct=(x,d=1)=>(x*100).toFixed(d).replace('.',',')+'%';
const fmtD=s=>s.split('-').reverse().join('/');
const ga=(e,p)=>{try{gtag('event',e,Object.assign({content_group:'hmm',market:S.mk},p))}catch(_){}};
async function get(u){return cache[u]||(cache[u]=await (await fetch(u)).json())}
function seg(id,key,cast){$(id).onclick=e=>{const b=e.target.closest('button');if(!b)return;[...$(id).children].forEach(x=>x.classList.toggle('on',x===b));S[key]=cast(b.dataset.v);if(key!=='r')S.mom=null;ga('hmm_control',{control:key,value:b.dataset.v});key==='r'?draw():load()}}
seg('segMk','mk',String);seg('segK','k',Number);seg('segF','f',String);seg('segR','r',Number);
$('cbSm').onchange=e=>{S.sm=e.target.checked;ga('hmm_control',{control:'smoothed',value:S.sm});draw()};
async function load(){meta=meta||await get('data/meta.json');D=await get(`data/hmm_${S.mk}_${S.f}${S.k}.json`);
 D.reg=D.filt.map(p=>p.indexOf(Math.max(...p)));render()}
function render(){const m=meta.markets[S.mk];
 $('legend').innerHTML=D.names.map(n=>`<span><i style="background:${COL[n]}"></i>${NAME[n]}</span>`).join('');
 $('pxNote').textContent=`${m.label} · ${S.mk==='spx'?'índice de preço (sem dividendos)':'índice de retorno total'} · escala log`;
 $('agree').textContent=pct(D.agree,0);
 $('src').textContent=`${m.source}, desde ${fmtD(D.dates[0])}, último fechamento ${fmtD(D.last.date)}. ${S.mk==='spx'?'Usamos o ^GSPC (índice de preço) e não o SPY ajustado: histórico mais longo, sem custos do ETF e é o nível que todos acompanham. Dividendos ficam de fora (~1,5–2% a.a.), o que reduz levemente os retornos, mas pouco afeta a volatilidade que define os regimes.':'O Ibovespa já é um índice de retorno total (reinveste proventos).'}`;
 const L=D.last,ri=D.names.indexOf(L.regime),u=S.f==='d'?'pregões':'semanas';
 $('nowCard').innerHTML=`<div><span class="ill">REGIME ATUAL · ${m.label.toUpperCase()} · ${fmtD(L.date)}</span><div class="big" style="color:${COL[L.regime]}">${NAME[L.regime]}</div><div class="meta">${HINT[L.regime]}<br>Probabilidade filtrada de <b>${pct(L.probs[ri])}</b> · desde ${fmtD(L.since)}<br>Duração esperada do regime: ~${Math.round(D.stats[ri].exp_dur)} ${u}</div></div><div class="pb">${D.names.map((n,i)=>`<div class="pbr"><span><i class="dot" style="background:${COL[n]}"></i>${NAME[n]}</span><div class="bar"><i style="width:${L.probs[i]*100}%;background:${COL[n]}"></i></div><b>${pct(L.probs[i])}</b></div>`).join('')}<span class="ill">Leitura do modelo, não previsão. Muda com novos dados.</span></div>`;
 const k=D.k;$('tm').innerHTML=`<div class="tm" style="grid-template-columns:90px repeat(${k},1fr)"><div class="h">de \\ para</div>${D.names.map(n=>`<div class="h">${NAME[n]}</div>`).join('')}${D.transmat.map((r,i)=>`<div class="h" style="text-align:left;color:${COL[D.names[i]]}">${NAME[D.names[i]]}</div>`+r.map(v=>`<div style="background:rgba(45,212,191,${.06+v*.8});color:${v>.5?'#04201c':'#f4f1ea'}">${pct(v)}</div>`).join('')).join('')}</div>`;
 const mx=Math.max(...D.stats.map(s=>Math.max(s.exp_dur,s.avg_dur)));
 $('dur').innerHTML=D.stats.map(s=>`<div class="dr"><div class="lb"><b style="font-weight:500">${NAME[s.name]}</b><span>esperada ${Math.round(s.exp_dur)} · observada ${Math.round(s.avg_dur)} ${u} · ${s.n_episodes} episódios</span></div><div class="tr"><i style="width:${s.exp_dur/mx*100}%;background:${COL[s.name]}"></i><u style="left:${s.avg_dur/mx*100}%"></u></div></div>`).join('');
 $('st').innerHTML=`<tr><th>REGIME</th><th>% DO TEMPO</th><th>RETORNO A.A.</th><th>VOL A.A.</th><th>DRAWDOWN MÉDIO</th><th>PIOR DRAWDOWN</th></tr>`+D.stats.map(s=>`<tr><td><i class="dot" style="background:${COL[s.name]}"></i>${NAME[s.name]}</td><td>${pct(s.pct_time,0)}</td><td>${pct(s.ret_ann)}</td><td>${pct(s.vol_ann)}</td><td>${pct(s.avg_dd)}</td><td>${pct(s.worst_dd)}</td></tr>`).join('');
 $('moments').innerHTML=MOM[S.mk].map((x,i)=>`<button class="mchip${S.mom===i?' on':''}" data-i="${i}">${x[2]}</button>`).join('');
 $('mcap').hidden=S.mom==null;draw()}
$('moments').onclick=e=>{const b=e.target.closest('.mchip');if(!b)return;const i=+b.dataset.i;S.mom=S.mom===i?null:i;
 if(S.mom!=null){const x=MOM[S.mk][i];const a=D.dates.findIndex(d=>d>=x[0]),z=D.dates.findIndex(d=>d>x[1]);const sl=D.reg.slice(a,z<0?undefined:z),cnt=D.names.map((_,j)=>sl.filter(r=>r===j).length/sl.length);const top=cnt.indexOf(Math.max(...cnt));
  $('mcap').innerHTML=`<b>${x[2]}:</b> ${x[3]} No período, o modelo marcou <b style="color:${COL[D.names[top]]}">${NAME[D.names[top]]}</b> em ${pct(cnt[top],0)} do tempo.`;ga('hmm_moment',{moment:x[2]})}
 render()};
function range(){const n=D.dates.length;let a=0,b=n;
 if(S.mom!=null){const x=MOM[S.mk][S.mom],pad=S.f==='d'?120:26;a=Math.max(0,D.dates.findIndex(d=>d>=x[0])-pad);const z=D.dates.findIndex(d=>d>x[1]);b=Math.min(n,(z<0?n:z)+pad)}
 else if(S.r){const c=new Date(D.dates[n-1]);c.setFullYear(c.getFullYear()-S.r);const cs=c.toISOString().slice(0,10);a=D.dates.findIndex(d=>d>=cs)}
 return[a,b]}
function cv(id){const c=$(id),r=c.getBoundingClientRect(),dp=devicePixelRatio||1;c.width=r.width*dp;c.height=r.height*dp;const x=c.getContext('2d');x.setTransform(dp,0,0,dp,0,0);return[x,r.width,r.height]}
function draw(){if(!D)return;const[a,b]=range(),N=b-a,P=D.px.slice(a,b);
 const[x,W,H]=cv('cPx'),pl=8,pr=58,pt=10,pb=22,lg=P.map(Math.log),lo=Math.min(...lg),hi=Math.max(...lg);
 const X=i=>pl+i/(N-1)*(W-pl-pr),Y=v=>pt+(hi-Math.log(v))/(hi-lo||1)*(H-pt-pb);view={a,N,X,Y,W,pl,pr};
 x.font='10.5px ui-monospace,Menlo,monospace';x.fillStyle='#8a8a93';x.strokeStyle='#1c1c1f';x.lineWidth=1;
 for(let t=0;t<=4;t++){const v=Math.exp(lo+(hi-lo)*t/4),y=Y(v);x.beginPath();x.moveTo(pl,y);x.lineTo(W-pr,y);x.stroke();x.fillText(Math.round(v).toLocaleString('pt-BR'),W-pr+6,y+3)}
 ticks(x,a,N,X,H-6);
 if(S.mom!=null){const m=MOM[S.mk][S.mom];let i0=D.dates.findIndex(d=>d>=m[0])-a,i1=D.dates.findIndex(d=>d>m[1])-a;if(i1<0)i1=N-1;x.fillStyle='rgba(244,241,234,.05)';x.fillRect(X(i0),pt,X(i1)-X(i0),H-pt-pb)}
 x.lineWidth=N>2000?1.2:1.8;x.lineJoin='round';
 for(let i=1;i<N;i++){x.strokeStyle=COL[D.names[D.reg[a+i]]];x.beginPath();x.moveTo(X(i-1),Y(P[i-1]));x.lineTo(X(i),Y(P[i]));x.stroke()}
 const[y,W2,H2]=cv('cPr'),h2=S.sm?(H2-26)/2:H2-20,X2=i=>pl+i/(N-1)*(W2-pl-pr);
 const band=(src,top,lab)=>{for(let i=0;i<N;i++){let acc=0;const p=src[a+i];for(let j=D.k-1;j>=0;j--){y.fillStyle=COL[D.names[j]];const hh=p[j]*h2;y.fillRect(X2(i),top+acc,Math.max(1,(W2-pl-pr)/N+.5),hh);acc+=hh}}
  y.fillStyle='#a1a1aa';y.font='10.5px ui-monospace,Menlo,monospace';y.fillText(lab,W2-pr+6,top+12)};
 band(D.filt,0,'filtrada');if(S.sm)band(D.smooth,h2+6,'suavizada');ticks(y,a,N,X2,H2-6)}
function ticks(x,a,N,X,y){x.fillStyle='#8a8a93';const y0=+D.dates[a].slice(0,4),y1=+D.dates[a+N-1].slice(0,4),st=Math.max(1,Math.ceil((y1-y0)/8));let last='';
 for(let i=0;i<N;i++){const yr=D.dates[a+i].slice(0,4);if(yr!==last){last=yr;if((+yr-y0)%st===0&&i>0||N<300&&i>0)x.fillText(yr,X(i)-12,y)}}}
const tip=$('tip');$('cPx').onmousemove=e=>{if(!view)return;const r=e.target.getBoundingClientRect(),mx=e.clientX-r.left;const i=Math.round((mx-view.pl)/(view.W-view.pl-view.pr)*(view.N-1));if(i<0||i>=view.N){tip.hidden=true;return}
 const g=view.a+i,p=D.filt[g];tip.hidden=false;tip.innerHTML=`${fmtD(D.dates[g])} · ${Math.round(D.px[g]).toLocaleString('pt-BR')}<br>`+D.names.map((n,j)=>`<span style="color:${COL[n]}">${NAME[n]} ${pct(p[j],0)}</span>`).join('<br>');
 tip.style.left=Math.min(mx+12,r.width-170)+'px';tip.style.top='12px'};$('cPx').onmouseleave=()=>tip.hidden=true;
addEventListener('resize',draw);load();
})();
