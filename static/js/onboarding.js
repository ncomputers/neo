const steps = Array.from(document.querySelectorAll('.step'));
let index = 0;

function showStep(i) {
  steps.forEach((s, idx) => {
    s.setAttribute('aria-hidden', idx === i ? 'false' : 'true');
  });
  document.getElementById('back').hidden = i === 0;
}

document.getElementById('onboarding-form').addEventListener('submit', (e) => {
  e.preventDefault();
  if (index < steps.length - 1) {
    index++;
    showStep(index);
  } else {
    document.getElementById('onboarding-form').hidden = true;
    document.getElementById('done').hidden = false;
  }
});

document.getElementById('back').addEventListener('click', () => {
  if (index > 0) {
    index--;
    showStep(index);
  }
});

showStep(0);
