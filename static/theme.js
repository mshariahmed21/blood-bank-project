(function(){
  const root=document.documentElement;
  const key='qatrah-theme';
  function setTheme(theme){
    root.setAttribute('data-theme',theme);
    try{localStorage.setItem(key,theme)}catch(e){}
    document.querySelectorAll('[data-theme-toggle]').forEach(btn=>{
      btn.textContent=theme==='dark'?'☀️ الوضع الفاتح':'🌙 الوضع الداكن';
      btn.setAttribute('aria-pressed',theme==='dark'?'true':'false');
    });
  }
  let saved='light';try{saved=localStorage.getItem(key)||'light'}catch(e){}
  setTheme(saved==='dark'?'dark':'light');
  document.querySelectorAll('[data-theme-toggle]').forEach(btn=>btn.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark')));
})();
