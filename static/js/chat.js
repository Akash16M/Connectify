const app = document.getElementById("app");
const currentUserId = Number(app.dataset.userId);
const currentUsername = app.dataset.username;
const socket = io();
let activeConversation = null;
let allUsers = [];
let allConversations = [];
let typingTimer = null;
let onlineUserIds = new Set();

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const initials = (name) => (name || "?").slice(0,1).toUpperCase();

async function api(url, options={}) {
  const response = await fetch(url, {headers: {"Content-Type":"application/json", ...(options.headers||{})}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

async function loadAll() {
  try {
    [allUsers, allConversations] = await Promise.all([api("/api/users"), api("/api/conversations")]);
    renderUsers(); renderConversations();
  } catch (e) { console.error(e); }
}
function renderUsers(filter="") {
  const list = $("peopleList");
  const filtered = allUsers.filter(u => u.username.toLowerCase().includes(filter.toLowerCase()));
  list.innerHTML = filtered.map(u => `<div class="person-item" data-user="${u.id}"><div class="avatar">${escapeHtml(initials(u.username))}</div><div class="item-copy"><strong>${escapeHtml(u.username)}</strong><small>${onlineUserIds.has(u.id) ? "● Online" : "Start a conversation"}</small></div><span class="item-time">＋</span></div>`).join("") || '<div class="empty-list">No other users yet.</div>';
  list.querySelectorAll("[data-user]").forEach(el => el.addEventListener("click", () => openDirect(Number(el.dataset.user))));
}
function renderConversations(filter="") {
  const list = $("conversationList");
  const filtered = allConversations.filter(c => c.title.toLowerCase().includes(filter.toLowerCase()));
  list.innerHTML = filtered.map(c => `<div class="conversation-item ${activeConversation?.id===c.id?"selected":""}" data-conv="${c.id}"><div class="avatar">${escapeHtml(initials(c.title))}</div><div class="item-copy"><strong>${escapeHtml(c.title)}</strong><small>${escapeHtml(c.last_message || "Start a conversation")}</small></div>${c.is_group?'<span class="item-time">GROUP</span>':''}</div>`).join("") || '<div class="empty-list">No conversations yet.</div>';
  list.querySelectorAll("[data-conv]").forEach(el => el.addEventListener("click", () => openConversation(Number(el.dataset.conv))));
}
async function openDirect(userId) {
  try {
    const conv = await api("/api/conversations/direct", {method:"POST", body:JSON.stringify({user_id:userId})});
    await loadAll();
    openConversation(conv.id);
  } catch(e) { alert(e.message); }
}
async function openConversation(id) {
  const conv = allConversations.find(c => c.id===id) || await api("/api/conversations").then(rows=>rows.find(c=>c.id===id));
  if (!conv) return;
  activeConversation = conv;
  $("welcome").classList.add("hidden");
  $("activeChat").classList.remove("hidden");
  $("chatTitle").textContent = conv.title;
  $("chatAvatar").textContent = initials(conv.title);
  $("chatStatus").textContent = conv.is_group ? `${conv.members.length+1} members · Group conversation` : "Connectify conversation";
  socket.emit("join_conversation", {conversation_id:id});
  renderConversations($("searchInput").value);
  await loadMessages();
}
async function loadMessages() {
  if (!activeConversation) return;
  try {
    const rows = await api(`/api/messages/${activeConversation.id}`);
    $("messages").innerHTML = rows.map(renderMessage).join("");
    scrollBottom();
  } catch(e) { console.error(e); }
}
function renderMessage(m) {
  const mine = m.mine ?? (Number(m.sender_id)===currentUserId);
  const attachment = m.attachment ? `<a href="${escapeHtml(m.attachment)}" target="_blank" rel="noopener">📎 Open attachment</a>` : "";
  return `<div class="message ${mine?"mine":""}">${!mine && activeConversation?.is_group ? `<div class="sender">${escapeHtml(m.username)}</div>`:""}<div class="body">${escapeHtml(m.body || "")}</div>${attachment}<div class="time">${escapeHtml(m.created_at || "")}</div></div>`;
}
function scrollBottom(){const box=$("messages");box.scrollTop=box.scrollHeight;}
$("messageForm").addEventListener("submit", e => {
  e.preventDefault();
  if (!activeConversation) return;
  const body = $("messageInput").value.trim();
  if (!body) return;
  socket.emit("send_message", {conversation_id:activeConversation.id, body});
  $("messageInput").value="";
  socket.emit("typing", {conversation_id:activeConversation.id, typing:false});
});
$("messageInput").addEventListener("input", () => {
  if (!activeConversation) return;
  socket.emit("typing", {conversation_id:activeConversation.id, typing:true});
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => socket.emit("typing", {conversation_id:activeConversation.id, typing:false}), 900);
});
socket.on("new_message", message => {
  if (activeConversation && message.conversation_id===activeConversation.id) {
    $("messages").insertAdjacentHTML("beforeend", renderMessage({...message, mine:message.sender_id===currentUserId}));
    scrollBottom();
  }
  loadAll();
});
socket.on("typing", data => {
  if (data.typing) $("typingLine").textContent = `${data.username} is typing…`;
  else $("typingLine").textContent = "";
});
socket.on("presence_snapshot", data => {
  onlineUserIds = new Set((data.user_ids || []).map(Number));
  renderUsers($("searchInput").value);
});
socket.on("presence", data => {
  if (data.online) onlineUserIds.add(Number(data.user_id));
  else onlineUserIds.delete(Number(data.user_id));
  renderUsers($("searchInput").value);
});

$("searchInput").addEventListener("input", e => {
  renderUsers(e.target.value); renderConversations(e.target.value);
});

$("fileInput").addEventListener("change", async e => {
  const file = e.target.files[0];
  if (!file || !activeConversation) return;
  const form = new FormData(); form.append("file", file);
  try {
    const response = await fetch("/api/upload", {method:"POST", body:form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Upload failed");
    socket.emit("send_message", {conversation_id:activeConversation.id, body:"", attachment:data.attachment});
  } catch(err) { alert(err.message); }
  e.target.value="";
});

$("newGroupBtn").addEventListener("click", () => {
  $("groupMembers").innerHTML = allUsers.map(u => `<label class="member-option"><input type="checkbox" value="${u.id}"> ${escapeHtml(u.username)}</label>`).join("") || '<p class="muted">Create another account first to add group members.</p>';
  $("groupModal").classList.remove("hidden");
});
$("closeModal").addEventListener("click", () => $("groupModal").classList.add("hidden"));
$("groupModal").addEventListener("click", e => {if(e.target.id==="groupModal") $("groupModal").classList.add("hidden");});
$("createGroup").addEventListener("click", async () => {
  const title = $("groupTitle").value.trim();
  const member_ids = [...$("groupMembers").querySelectorAll("input:checked")].map(x=>Number(x.value));
  try {
    const conv = await api("/api/conversations/group", {method:"POST", body:JSON.stringify({title, member_ids})});
    $("groupModal").classList.add("hidden"); $("groupTitle").value="";
    await loadAll(); openConversation(conv.id);
  } catch(e) { alert(e.message); }
});

loadAll();
