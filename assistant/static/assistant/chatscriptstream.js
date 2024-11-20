const data = document.currentScript.dataset;
const userImage = data.userimage;
const postUrl = data.posturl;
const introPostUrl = data.introposturl;
const introMessage = data.intromessage;
const errorImage = data.errorimage;
const botImage = data.botimage;

let savedpasttext = [];
let savedpastresponse = [];

// Section: Get the ID of the talking container
const messagesContainer = document.getElementById('messages-container');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('question');

// Section: Function to create the dialogue window
const addMessage = (message, role, imgSrc) => {
  const messageElement = document.createElement('div');
  const textElement = document.createElement('p');
  messageElement.className = `message ${role}`;
  const imgElement = document.createElement('img');
  imgElement.src = `${imgSrc}`;
  messageElement.appendChild(imgElement);
  textElement.innerText = message;
  messageElement.appendChild(textElement);
  messagesContainer.appendChild(messageElement);
  const clearDiv = document.createElement("div");
  clearDiv.style.clear = "both";
  messagesContainer.appendChild(clearDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight; // Auto-scroll
};

const prepForStream = (role, imgSrc) => {
  const loadanimation = document.querySelector('.loading-animation');
  const loadtxt = document.querySelector('.loading-text');
  loadanimation.remove();
  loadtxt.remove();

  const messageElement = document.createElement('div');
  const botTextElement = document.createElement('p');
  botTextElement.setAttribute('name', 'bot-response-text');
  messageElement.className = `message ${role}`;
  const imgElement = document.createElement('img');
  imgElement.src = `${imgSrc}`;
  messageElement.appendChild(imgElement);
  botTextElement.innerText = '';
  messageElement.appendChild(botTextElement);
  messagesContainer.appendChild(messageElement);
  const clearDiv = document.createElement("div");
  clearDiv.style.clear = "both";
  messagesContainer.appendChild(clearDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

};


// Section: Calling the model with streaming
const sendMessage = async (message, intro=false) => {
  if (!intro){
    addMessage(message, 'user', userImage);
    url = postUrl;
  } else {
    url = introPostUrl;
  }
  const loadingElement = document.createElement('div');
  const loadingtextElement = document.createElement('p');
  loadingElement.className = `loading-animation`;
  loadingtextElement.className = `loading-text`;
  loadingtextElement.innerText = 'Loading....Please wait';
  messagesContainer.appendChild(loadingElement);
  messagesContainer.appendChild(loadingtextElement);

  messagesContainer.scrollTop = messagesContainer.scrollHeight; // Auto-scroll

  try {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({ question: message })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let done = false;

    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;

      if (value) {
        if (document.querySelector('.loading-text')) {
            prepForStream('aibot', botImage)
        }

        const chunk = decoder.decode(value, { stream: true });
        const botResponses = document.getElementsByName('bot-response-text');
        const botTextElement = botResponses[botResponses.length - 1];
        botTextElement.innerText += chunk;
        messagesContainer.scrollTop = messagesContainer.scrollHeight; // Auto-scroll
      }
    }
  } catch (error) {
    console.error('Error:', error);
    const botResponses = document.getElementsByName('bot-response-text');
    const botTextElement = botResponses[botResponses.length - 1];
    botTextElement.innerText = "Something went wrong while processing your request.";
  }
};

// Section: Button to submit to the model and get the response
messageForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (message !== '') {
    messageInput.value = '';
    await sendMessage(message);
  }
});

sendMessage(introMessage, true);
