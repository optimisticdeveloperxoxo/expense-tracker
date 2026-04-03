/* SpendSense — script.js */

// Mobile sidebar toggle
function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('open');
}
document.addEventListener('click', e=>{
  const sb = document.getElementById('sidebar');
  if(sb && sb.classList.contains('open')
     && !sb.contains(e.target)
     && !e.target.closest('.hamburger')){
    sb.classList.remove('open');
  }
});

// Animate stat cards on page load
window.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('.stat-card').forEach((c,i)=>{
    c.style.opacity='0'; c.style.transform='translateY(14px)';
    c.style.transition=`opacity .35s ease ${i*.08}s, transform .35s ease ${i*.08}s`;
    requestAnimationFrame(()=>{ c.style.opacity='1'; c.style.transform='translateY(0)'; });
  });

  // Auto-dismiss flash messages
  document.querySelectorAll('.flash').forEach(f=>{
    setTimeout(()=>{ f.style.opacity='0'; f.style.transition='opacity .4s'; }, 4000);
    setTimeout(()=>f.remove(), 4500);
  });
});
