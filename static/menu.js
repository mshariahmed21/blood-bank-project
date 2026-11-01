(function(){
 const body=document.body, toggle=document.querySelector('[data-menu-toggle]'), drawer=document.querySelector('#side-drawer');
 const closers=document.querySelectorAll('[data-drawer-close]'), links=document.querySelectorAll('[data-drawer-link]');
 if(!toggle||!drawer)return;
 function open(){body.classList.add('drawer-open');toggle.setAttribute('aria-expanded','true');drawer.setAttribute('aria-hidden','false');const first=drawer.querySelector('a');if(first)first.focus();}
 function close(){body.classList.remove('drawer-open');toggle.setAttribute('aria-expanded','false');drawer.setAttribute('aria-hidden','true');toggle.focus();}
 toggle.addEventListener('click',()=>body.classList.contains('drawer-open')?close():open());
 closers.forEach(el=>el.addEventListener('click',close));
 links.forEach(link=>link.addEventListener('click',()=>{body.classList.remove('drawer-open');toggle.setAttribute('aria-expanded','false');drawer.setAttribute('aria-hidden','true');}));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&body.classList.contains('drawer-open'))close();});
})();