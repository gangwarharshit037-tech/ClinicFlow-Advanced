const $=id=>document.getElementById(id);const today=new Date();$('date').min=[today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
$('booking').onsubmit=async e=>{e.preventDefault();let r=await fetch('/api/book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});let j=await r.json();$('status').textContent=j.message||j.error;if(r.ok)e.target.reset()};
function bubble(text,cls){let n=document.createElement('div');n.className='bubble '+cls;n.textContent=text;$('chat').append(n);$('chat').scrollTop=$('chat').scrollHeight}
$('ask').onsubmit=async e=>{e.preventDefault();let q=$('question').value;bubble(q,'mine');$('question').value='';let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q})});let j=await r.json();bubble(j.reply||'Unable to respond.','')};

// Fill sample patient details in public demo mode.
const demoFillButton = document.getElementById('fill-demo');

if (demoFillButton) {
    demoFillButton.addEventListener('click', () => {
        const form = document.getElementById('booking');

        form.elements.namedItem('patient').value = 'Demo Patient';
        form.elements.namedItem('phone').value = '+12025550123';

        document.getElementById('status').textContent =
            'Demo details filled. Choose a doctor, date and time.';

        form.elements.namedItem('doctor').focus();
    });
}
