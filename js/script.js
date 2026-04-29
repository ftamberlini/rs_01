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

// ── Movies ──────────────────────────────────────────────────────────────────

const POSTER_PLACEHOLDER = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450">' +
  '<rect width="300" height="450" fill="#e0ddd8"/>' +
  '<text x="150" y="210" text-anchor="middle" fill="#aaa" font-family="sans-serif" font-size="15">No Poster</text>' +
  '</svg>'
)}`;

async function loadMovies() {
  try {
    const res    = await fetch('/movies');
    const movies = await res.json();
    const grid   = document.getElementById('moviesGrid');
    const cards  = [];

    movies.forEach(m => {
      const card = createMovieCard(m, () => {
        cards.forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        showMovieDetail(m);
      });
      grid.appendChild(card);
      cards.push(card);
    });

    if (cards.length > 0) {
      cards[0].classList.add('active');
      showMovieDetail(movies[0]);
    }
  } catch { /* server may not be running in static preview */ }
}

function createMovieCard(movie, onTitleClick) {
  const card = document.createElement('div');
  card.className = 'movie-card';

  const img = document.createElement('img');
  img.className   = 'movie-poster';
  img.src         = movie.poster;
  img.alt         = movie.title;
  img.loading     = 'lazy';
  img.onerror     = () => { img.onerror = null; img.src = POSTER_PLACEHOLDER; };

  const info  = document.createElement('div');
  info.className  = 'movie-info';

  const title = document.createElement('h3');
  title.className = 'movie-title';
  title.textContent = movie.title;
  title.addEventListener('click', onTitleClick);

  const year  = document.createElement('span');
  year.className  = 'movie-year';
  year.textContent = movie.year;

  info.appendChild(title);
  info.appendChild(year);
  info.appendChild(createStarRating());

  card.appendChild(img);
  card.appendChild(info);
  return card;
}

function showMovieDetail(movie) {
  const detailPoster   = document.getElementById('detailPoster');
  detailPoster.alt     = movie.title;
  detailPoster.onerror = () => { detailPoster.onerror = null; detailPoster.src = POSTER_PLACEHOLDER; };
  detailPoster.src     = movie.poster;
  document.getElementById('detailTitle').textContent  = movie.title;
  renderRatings(movie.ratings, movie.imdb_votes);
  document.getElementById('detailYear').textContent   = movie.year;
  document.getElementById('detailReleased').textContent = movie.released;
  document.getElementById('detailRuntime').textContent  = movie.runtime;
  document.getElementById('detailCountry').textContent  = movie.country;
  document.getElementById('detailLanguage').textContent = movie.language;
  document.getElementById('detailGenre').textContent    = movie.genre;
  document.getElementById('detailDirector').textContent = movie.director;
  document.getElementById('detailWriter').textContent   = movie.writer;
  document.getElementById('detailCast').textContent     = movie.cast;
  document.getElementById('detailAwards').textContent   = movie.awards !== 'N/A' ? movie.awards : '—';
  document.getElementById('detailPlot').textContent     = movie.plot;
}

function renderRatings(ratingsStr, imdbVotes) {
  const container = document.getElementById('detailRatings');
  container.innerHTML = '';
  if (!ratingsStr || ratingsStr === 'N/A') return;

  ratingsStr.split(' | ').forEach(part => {
    const sep = part.indexOf(': ');
    if (sep === -1) return;
    const source = part.slice(0, sep).trim();
    const value  = part.slice(sep + 2).trim();

    const badge = document.createElement('div');

    if (source.includes('Internet Movie Database')) {
      badge.className = 'rating-badge rb-imdb';
      badge.innerHTML = `<span class="rb-source">IMDb</span>
        <span class="rb-score">${value}</span>
        ${imdbVotes && imdbVotes !== 'N/A' ? `<span class="rb-votes">${imdbVotes} votes</span>` : ''}`;
    } else if (source.includes('Rotten Tomatoes')) {
      badge.className = 'rating-badge rb-rt';
      badge.innerHTML = `<span class="rb-source">Rotten Tomatoes</span><span class="rb-score">${value}</span>`;
    } else if (source.includes('Metacritic')) {
      badge.className = 'rating-badge rb-mc';
      badge.innerHTML = `<span class="rb-source">Metacritic</span><span class="rb-score">${value}</span>`;
    } else {
      badge.className = 'rating-badge';
      badge.innerHTML = `<span class="rb-source">${source}</span><span class="rb-score">${value}</span>`;
    }

    container.appendChild(badge);
  });
}

function createStarRating() {
  const container = document.createElement('div');
  container.className = 'star-rating';

  let current  = 0;
  const items  = [];

  for (let i = 1; i <= 5; i++) {
    const wrap = document.createElement('span');
    wrap.className = 'star-wrap';

    const bg = document.createElement('span');
    bg.className  = 'star-bg';
    bg.textContent = '★';

    const fg = document.createElement('span');
    fg.className  = 'star-fg';
    fg.textContent = '★';

    wrap.appendChild(bg);
    wrap.appendChild(fg);
    items.push({ fg, pos: i });

    wrap.addEventListener('mousemove', (e) => {
      const { left, width } = wrap.getBoundingClientRect();
      paint((e.clientX - left) < width / 2 ? i - 0.5 : i);
    });

    wrap.addEventListener('click', (e) => {
      const { left, width } = wrap.getBoundingClientRect();
      current = (e.clientX - left) < width / 2 ? i - 0.5 : i;
      paint(current);
    });

    container.appendChild(wrap);
  }

  container.addEventListener('mouseleave', () => paint(current));

  function paint(value) {
    items.forEach(({ fg, pos }) => {
      fg.style.width = value >= pos ? '100%' : value >= pos - 0.5 ? '50%' : '0%';
    });
  }

  return container;
}

loadMovies();

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  btnSubmit.disabled = true;
  btnSubmit.textContent = 'Saving…';

  try {
    const fd = new FormData(form);
    fd.set('email', emailInput.value);
    const res = await fetch('/submit', {
      method: 'POST',
      body: fd,
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
