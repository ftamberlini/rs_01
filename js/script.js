const emailInput     = document.getElementById('email');
const btnContinue    = document.getElementById('btnSearch');
const btnChangeEmail = document.getElementById('btnChangeEmail');
const btnSubmit      = document.getElementById('btnSubmit');
const stepEmail      = document.getElementById('stepEmail');
const stepFields     = document.getElementById('stepFields');
const emailConfirmed = document.getElementById('emailConfirmed');
const successMsg     = document.getElementById('successMsg');
const form           = document.getElementById('registrationForm');

function showStep1() {
  stepEmail.hidden  = false;
  stepFields.hidden = true;
  successMsg.hidden = true;
  emailInput.disabled = false;
  emailInput.value = '';
  clearFields();
}

function clearFields() {
  document.getElementById('name').value    = '';
  document.getElementById('dob').value     = '';
  document.getElementById('country').value = '';
  document.getElementById('race').value    = '';
  document.querySelector('input[name="gender"][value="not_informed"]').checked = true;
}

function fillFields(user) {
  document.getElementById('name').value    = user.name            || '';
  document.getElementById('dob').value     = user.date_of_birth   || '';
  document.getElementById('country').value = user.country         || '';
  document.getElementById('race').value    = user.race            || '';
  const genderRadio = document.querySelector(`input[name="gender"][value="${user.gender}"]`);
  if (genderRadio) genderRadio.checked = true;
}

function setFieldsDisabled(disabled) {
  stepFields.querySelectorAll('input, select, button').forEach(el => {
    el.disabled = disabled;
  });
}

btnContinue.addEventListener('click', async () => {
  const email = emailInput.value.trim();
  if (!email || !emailInput.validity.valid) {
    emailInput.focus();
    return;
  }

  btnContinue.disabled = true;
  btnContinue.textContent = 'Searching…';


  try {
    const res  = await fetch(`/lookup?email=${encodeURIComponent(email)}`);
    const data = await res.json();

    emailConfirmed.textContent = email;
    emailInput.disabled = true;
    stepEmail.hidden  = true;
    stepFields.hidden = false;
    setFieldsDisabled(false);
    successMsg.hidden = true;

    if (data.found) {
      fillFields(data.user);
      btnSubmit.textContent = 'Update';
    } else {
      clearFields();
      btnSubmit.textContent = 'Save';
    }
  } catch {
    alert('Failed to check email. Please try again.');
  } finally {
    btnContinue.disabled = false;
    btnContinue.textContent = 'Search';
  }
});

btnChangeEmail.addEventListener('click', showStep1);

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  btnSubmit.disabled = true;
  btnSubmit.textContent = 'Saving…';

  try {
    const res = await fetch('/submit', {
      method: 'POST',
      body: new FormData(form),
    });

    if (!res.ok) throw new Error('Server error');

    setFieldsDisabled(true);
    const action = btnSubmit.textContent.includes('Update') ? 'updated' : 'saved';
    successMsg.textContent = `Registration ${action} successfully.`;
    successMsg.hidden = false;
    btnSubmit.textContent = 'Submitted';
  } catch {
    btnSubmit.disabled = false;
    alert('Failed to save. Please try again.');
  }
});
