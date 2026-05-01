
let currentChatId = null;
let isSending = false;

function qs(id){ return document.getElementById(id); }

function fixPick(text){
  return String(text || '').replace(/Plcker/gi, 'PICK').replace(/Picker/g, 'PICK');
}

function timeNow(){
  return new Date().toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit'});
}

function addMessage(role, text){
  const area = qs('messageArea');
  const row = document.createElement('div');
  row.className = 'msg-row ' + role;
  row.innerHTML = `
    ${role === 'assistant' ? '<div class="avatar">P</div>' : ''}
    <div class="msg-stack">
      <div class="msg-name">${role === 'user' ? '나' : 'PICK'}</div>
      <div class="bubble ${role}"><span></span></div>
      <div class="msg-time">${timeNow()}</div>
    </div>
  `;
  row.querySelector('span').textContent = fixPick(text);
  area.appendChild(row);
  area.scrollTop = area.scrollHeight;
  return row.querySelector('span');
}

async function typeInto(el, text){
  const clean = fixPick(text);
  el.textContent = '';
  for(let i=0; i<clean.length; i+=2){
    el.textContent += clean.slice(i, i+2);
    qs('messageArea').scrollTop = qs('messageArea').scrollHeight;
    await new Promise(r=>setTimeout(r, 8));
  }
}

function growInput(){
  const input = qs('messageInput');
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 180) + 'px';
}

async function loadChats(){
  const res = await fetch('/api/chats');
  const data = await res.json();
  const list = qs('chatList');
  list.innerHTML = '';
  data.chats.forEach(chat=>{
    const btn = document.createElement('button');
    btn.className = 'chat-item';
    btn.textContent = chat.title || '새 채팅';
    btn.onclick = ()=>openChat(chat.id);
    list.appendChild(btn);
  });
}

async function newChat(){
  const res = await fetch('/api/chats/new', {method:'POST'});
  const data = await res.json();
  currentChatId = data.chat.id;
  qs('messageArea').innerHTML = '';
  addMessage('assistant', '새 채팅을 시작했습니다. 무엇을 도와드릴까요?');
  await loadChats();
}

async function openChat(id){
  currentChatId = id;
  qs('messageArea').innerHTML = '';
  const res = await fetch(`/api/chats/${id}/messages`);
  const data = await res.json();
  data.messages.forEach(m=>addMessage(m.role === 'assistant' ? 'assistant' : 'user', m.content));
}

async function sendMessage(){
  if(isSending) return;
  const input = qs('messageInput');
  const text = input.value.trim();
  if(!text) return;

  if(!currentChatId){
    await newChat();
  }

  isSending = true;
  qs('sendBtn').disabled = true;
  qs('sendBtn').textContent = '...';

  addMessage('user', text);
  input.value = '';
  growInput();

  const botSpan = addMessage('assistant', '입력하신 내용을 확인하고 있습니다.');

  try{
    const form = new FormData();
    form.append('message', text);
    const res = await fetch(`/api/chats/${currentChatId}/send`, {method:'POST', body:form});
    const data = await res.json();
    if(!data.ok) throw new Error(data.error || '오류');
    await typeInto(botSpan, data.reply);
    await loadChats();
  }catch(e){
    await typeInto(botSpan, '죄송합니다. 처리 중 오류가 발생했습니다.');
  }finally{
    isSending = false;
    qs('sendBtn').disabled = false;
    qs('sendBtn').textContent = '전송';
    input.focus();
  }
}

qs('messageInput').addEventListener('input', growInput);
qs('messageInput').addEventListener('keydown', e=>{
  if(e.isComposing) return;
  if(e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    sendMessage();
  }
});

window.addEventListener('load', async ()=>{
  await loadChats();
  addMessage('assistant', '안녕하세요. 저는 PICK입니다. 무엇을 도와드릴까요?');
  qs('messageInput').focus();
});



/* ===== PICK message edit/delete final override ===== */
function addMessage(role, text, id=null){
  const area = qs('messageArea');
  const row = document.createElement('div');
  row.className = 'msg-row ' + role;
  row.dataset.messageId = id || '';
  const isUser = role === 'user';
  row.innerHTML = `
    ${role === 'assistant' ? '<div class="avatar">P</div>' : ''}
    <div class="msg-stack">
      <div class="msg-name">${isUser ? '나' : 'PICK'}</div>
      <div class="bubble ${role}">
        <span class="message-text"></span>
        ${id ? `<div class="message-tools">
          ${isUser ? `<button onclick="editMessage(${id})">수정</button>` : ''}
          <button onclick="deleteMessage(${id})">삭제</button>
        </div>` : ''}
      </div>
      <div class="msg-time">${timeNow()}</div>
    </div>
  `;
  row.querySelector('.message-text').textContent = fixPick(text);
  area.appendChild(row);
  area.scrollTop = area.scrollHeight;
  return row.querySelector('.message-text');
}

async function openChat(id){
  currentChatId = id;
  qs('messageArea').innerHTML = '';
  const res = await fetch(`/api/chats/${id}/messages`);
  const data = await res.json();
  data.messages.forEach(m=>addMessage(m.role === 'assistant' ? 'assistant' : 'user', m.content, m.id));
}

async function deleteMessage(id){
  if(!confirm('이 메시지를 삭제하시겠습니까?')) return;
  const res = await fetch(`/api/messages/${id}/delete`, {method:'POST'});
  const data = await res.json();
  if(!data.ok){
    alert(data.error || '삭제 실패');
    return;
  }
  const row = document.querySelector(`[data-message-id="${id}"]`);
  if(row) row.remove();
}

async function editMessage(id){
  const row = document.querySelector(`[data-message-id="${id}"]`);
  if(!row) return;
  const span = row.querySelector('.message-text');
  const oldText = span.textContent;
  const next = prompt('메시지를 수정하세요.', oldText);
  if(next === null) return;
  const content = next.trim();
  if(!content){
    alert('내용이 비어 있습니다.');
    return;
  }

  const form = new FormData();
  form.append('content', content);
  const res = await fetch(`/api/messages/${id}/edit`, {method:'POST', body:form});
  const data = await res.json();
  if(!data.ok){
    alert(data.error || '수정 실패');
    return;
  }
  span.textContent = data.content;
}
