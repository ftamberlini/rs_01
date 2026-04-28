    const form = document.getElementById('registrationForm');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Saving…';

      try {
        const res = await fetch('/submit', {
          method: 'POST',
          body: new FormData(form),
        });

        if (!res.ok) throw new Error('Server error');

        // Disable all interactive elements
        form.querySelectorAll('input, select, button').forEach(el => {
          el.disabled = true;
        });

        btn.textContent = 'Submitted';
        document.getElementById('successMsg').hidden = false;
      } catch (err) {
        btn.disabled = false;
        btn.textContent = 'Submit';
        alert('Failed to save. Please try again.');
      }
    });