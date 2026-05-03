var chat_history = [];
var projects = [{name: "Project 1"}, {name: "Project 2"}, {name: "Project 3"}];
// var projects = null;

const chatMessages = document.getElementById("chat-messages");
const chatbox = document.getElementById("chatbox");
const input = document.getElementById("input");

// Chatboox position =============================
if(chatMessages.hidden){
    chatbox.className = "chatbox-center";
}
else{
    chatbox.className = "chatbox-below";
}

chatbox.addEventListener("submit", function(e){
    e.preventDefault();
    var prompt = input.value.trim();
    if(prompt === "") return;

    // Add newlines to message ==============================
    prompt = prompt.replace(/\n/g, "<br>");
    var response = "Response goes here";

    // add to chat history
    chat_history.push({prompt: prompt, response: response});
    input.value = "";

    // move chatbox to below==============================
    chatbox.className = "chatbox-below";

    // show chat messages ==============================
    if(chatMessages.hidden) chatMessages.hidden = false;
    chatMessages.innerHTML += `<div class="message">
            <p class="user-message"><strong></strong> ${prompt}</p>
            <p class="bot-message"><strong></strong> ${response}</p>
        </div>`;

    // Scroll to bottom on send===========================
    chatMessages.scrollTop = chatMessages.scrollHeight;
    input.style.height = "auto";
});

//auto focus==========================================
input.focus();
// Keep focus on input ===============================
input.addEventListener("blur", () => {
    setTimeout(() => {
        input.focus();
    }, 0);
});
// shift enter for new line, enter to submit============================
input.addEventListener("keydown", function(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        chatbox.dispatchEvent(new Event("submit"));
    }
});
//expand textarea with input===================================
input.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = this.scrollHeight + "px";
});



const projectOptions = document.getElementById("projectOptions");
const projectButton = document.getElementById("projectButton");

if(projects){
    projects.push({name: "General"});
}

//dropdown
function chooseProject(){
    //show dropdown============================
    projectOptions.style.display = "block";

    if(projects){
        projectOptions.innerHTML = "";
        projects.sort((a, b) => a.name.localeCompare(b.name));

        projects.forEach(project => {
            const option = document.createElement("a");
            option.className = "project-option";
            option.textContent = project.name;
            
            // on choosing a project, set button text and hide dropdown
            option.addEventListener("click", (e) => {
                e.stopPropagation();
                projectOptions.style.display = "none";
                projectButton.textContent = option.textContent=="General"? "Choose Project": project.name;
            });

            projectOptions.appendChild(option);
        });
    }
    else{
        // projects is null, show message================================
        projectOptions.innerHTML = "<p background-color: rgb(9, 2, 41);>Add projects to use</p>";
    }
}
// Close dropdown if clicked outside
const dropdown = document.getElementById("dropdown");
document.addEventListener("click", function(e) {
    if (!dropdown.contains(e.target)) {
        projectOptions.style.display = "none";
    }
});