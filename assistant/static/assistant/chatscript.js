const data = document.currentScript.dataset;
const userImage = data.userimage;
const postUrl = data.posturl;
const errorImage = data.errorimage;
const botImage = data.botimage;

let savedpasttext = []; // Variable to store the message
let savedpastresponse = []; // Variable to store the message

// Section: get the Id of the talking container
const messagesContainer = document.getElementById('messages-container');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('question');
//

//Section: function to creat the dialogue window
const addMessage = (message, role, imgSrc) => {
  // creat elements in the dialogue window
  const messageElement = document.createElement('div');
  const textElement = document.createElement('p');
  messageElement.className = `message ${role}`;
  const imgElement = document.createElement('img');
  imgElement.src = `${imgSrc}`;
  // append the image and message to the message element
  messageElement.appendChild(imgElement);
  textElement.innerText = message;
  messageElement.appendChild(textElement);
  messagesContainer.appendChild(messageElement);
  // creat the ending of the message
  var clearDiv = document.createElement("div");
  clearDiv.style.clear = "both";
  messagesContainer.appendChild(clearDiv);
};
//


//Section: Calling the model
const sendMessage = async (message) => {
  addMessage(message, 'user', userImage);
  // Loading animation
  const loadingElement = document.createElement('div');
  const loadingtextElement = document.createElement('p');
  loadingElement.className = `loading-animation`;
  loadingtextElement.className = `loading-text`;
  loadingtextElement.innerText = 'Loading....Please wait';
  messagesContainer.appendChild(loadingElement);
  messagesContainer.appendChild(loadingtextElement);

  async function makePostRequest(msg) {
    const requestBody = {
      question: msg
    };

    console.log(JSON.stringify(requestBody));
    try {
      const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      const response = await fetch(postUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify(requestBody)
      });

      const resp_data = await response.text();
      // Handle the response data here
      console.log(resp_data);
      return resp_data;
    } catch (error) {
      // Handle any errors that occurred during the request
      console.error('Error:', error);
      return error
    }
  }

  var res = await makePostRequest(message);

   console.log(res)
  resp_data = {"response": res};

  // Deleting the loading animation
  const loadanimation = document.querySelector('.loading-animation');
  const loadtxt = document.querySelector('.loading-text');
  loadanimation.remove();
  loadtxt.remove();

  if (resp_data.error) {
    // Handle the error here
    const errorMessage = JSON.stringify(resp_data);
    addMessage(errorMessage, 'error', errorImage);
  } else {
    // Process the normal response here
    const responseMessage = resp_data['response'];
    addMessage(responseMessage, 'aibot', botImage);
  }

};
//

//Section: Button to submit to the model and get the response
messageForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (message !== '') {
    messageInput.value = '';
    await sendMessage(message);
  }
});