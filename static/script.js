// DASHBOARD
const form = document.getElementById("uploadForm");
if(form){
form.onsubmit = async function(e){
    e.preventDefault();

    let formData = new FormData();
    formData.append("file", document.getElementById("file").files[0]);

    let res = await fetch("/run_analysis", {
        method: "POST",
        body: formData
    });

    let data = await res.json();

    document.getElementById("result").innerText =
        JSON.stringify(data.result, null, 2);
}
}

// CHAT
function send(){
    let msg = document.getElementById("msg").value;

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: msg})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("chat").innerHTML += 
            `<div class="user">${msg}</div>
             <div class="bot">${data.reply}</div>`;
    });
}


// TOGGLE CHAT
document.getElementById("chat-btn").onclick = function(){
    let popup = document.getElementById("chat-popup");

    if(popup.style.display === "none"){
        popup.style.display = "block";
    } else {
        popup.style.display = "none";
    }
};

// CHAT SEND
function send(){
    let msg = document.getElementById("msg").value;

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: msg})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("chat-body").innerHTML += 
            `<div class="user">${msg}</div>
             <div class="bot">${data.reply}</div>`;
    });
}