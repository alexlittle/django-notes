// hide an element
const hide = elem => {
  elem.style.display = 'none'
}

// show an element
const show = elem => {
  elem.style.display = 'block'
}

// toggle the element visibility
const toggle = elem => {
  // if the element is visible, hide it
  if (window.getComputedStyle(elem).display !== 'none') {
    hide(elem)
    return
  }

  // show the element
  show(elem)
}