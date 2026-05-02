import csv
import random
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js",  StaticFiles(directory="js"),  name="js")

CSV_PATH     = Path("data/users.csv")
CSV_HEADERS  = ["userid", "name", "email", "date_of_birth", "gender", "country", "race"]
MOVIE_PATH   = Path("data/movie_imdb.tsv")
COUNTRY_PATH = Path("data/country.tsv")


def _load_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


_directors    = {r["ID_DIRECTOR"]: r for r in _load_tsv(Path("data/director.tsv"))}
_writers_dict = {r["ID_WRITER"]:   r for r in _load_tsv(Path("data/writer.tsv"))}

_movie_dirs: dict[str, list] = {}
for _r in _load_tsv(Path("data/movie_director.tsv")):
    _movie_dirs.setdefault(_r["MOVIEID"], []).append(_r["ID_DIRECTOR"])

_movie_wris: dict[str, list] = {}
for _r in _load_tsv(Path("data/movie_writer.tsv")):
    _movie_wris.setdefault(_r["MOVIEID"], []).append(_r["ID_WRITER"])

_ml_data: dict[str, dict] = {r["MOVIEID"]: r for r in _load_tsv(Path("data/movie_ml.tsv"))}

_imdb_genres: dict[str, list[str]] = {}
for _r in _load_tsv(Path("data/movie_imdb_genres.tsv")):
    _imdb_genres.setdefault(_r["MOVIEID"], []).append(_r["GENRE"])

_ml_genres: dict[str, list[str]] = {}
for _r in _load_tsv(Path("data/movie_ml_genres.tsv")):
    _ml_genres.setdefault(_r["MOVIEID"], []).append(_r["GENRE"])

_movie_tags: dict[str, list[dict]] = {}
for _r in _load_tsv(Path("data/movie_tags.tsv")):
    try:
        count = int(_r["COUNT"])
    except (ValueError, KeyError):
        count = 0
    _movie_tags.setdefault(_r["MOVIEID"], []).append({"tag": _r["TAG"], "count": count})

_user_ratings: dict[str, list[dict]] = {}
for _r in _load_tsv(Path("data/user_ratings.tsv")):
    _user_ratings.setdefault(_r["USERID"], []).append(_r)

_imdb_rows:        dict[str, dict] = {}
_movie_imdb_awards: dict[str, dict] = {}
for _r in _load_tsv(Path("data/movie_imdb.tsv")):
    iid = _r.get("IMDBID", "").strip()
    if iid:
        _imdb_rows[iid] = _r
        _movie_imdb_awards[iid] = {
            "wins": _r.get("AWARD_WINNING", "").strip(),
            "noms": _r.get("AWARD_NOMINATION", "").strip(),
        }

_movie_languages: dict[str, list[str]] = {}
for _r in _load_tsv(Path("data/movie_languages.tsv")):
    _movie_languages.setdefault(_r["MOVIEID"], []).append(_r["LANGUAGE"])

_iso_continent: dict[str, str] = {
    r["ISO"]: r["CONTINENT"] for r in _load_tsv(Path("data/country.tsv")) if r.get("ISO")
}

_movie_continents: dict[str, list[str]] = {}
for _r in _load_tsv(Path("data/movie_country.tsv")):
    iso = _r.get("ISO", "").strip()
    continent = _iso_continent.get(iso, "Other")
    existing = _movie_continents.setdefault(_r["MOVIEID"], [])
    if continent not in existing:
        existing.append(continent)

_user_tags: dict[tuple, list[str]] = {}
_ut_path = Path("data/user_tags.csv")
if _ut_path.exists():
    with open(_ut_path, newline="", encoding="utf-8") as _f:
        for _r in csv.DictReader(_f):
            _user_tags.setdefault((_r["USERID"], _r["MOVIEID"]), []).append(_r["TAG"])


def _genres_imdb(movieid: str) -> list[str]:
    return _imdb_genres.get(movieid, [])

def _genres_ml(movieid: str) -> list[str]:
    return _ml_genres.get(movieid, [])

def _tags(movieid: str) -> list[dict]:
    return sorted(_movie_tags.get(movieid, []), key=lambda x: x["count"], reverse=True)[:20]

def _clean(val: str) -> str:
    v = (val or "").strip()
    return "" if v in ("N/A", "") else v

def _ratings(movieid: str, row: dict) -> list[dict]:
    result: list[dict] = []
    ml = _ml_data.get(movieid, {})

    ml_score = _clean(ml.get("RATING_ML", ""))
    if ml_score:
        entry: dict = {"source": "Movie Lens", "score": f"{float(ml_score):.1f}/5"}
        ml_votes = _clean(ml.get("VOTES_ML", ""))
        if ml_votes:
            entry["votes"] = ml_votes
        result.append(entry)

    imdb_score = _clean(row.get("IMDBRATING", ""))
    if imdb_score:
        entry = {"source": "IMDb", "score": f"{float(imdb_score):.1f}/10"}
        imdb_votes = _clean(row.get("IMDBVOTES", ""))
        if imdb_votes:
            entry["votes"] = imdb_votes
        result.append(entry)

    rt = _clean(row.get("RTRATING", ""))
    if rt:
        result.append({"source": "Rotten Tomatoes", "score": f"{float(rt):.0f}/100"})

    mc = _clean(row.get("MCRATING", ""))
    if mc:
        result.append({"source": "Metacritic", "score": f"{float(mc):.0f}/100"})

    return result


def _people(movieid: str, role_map: dict, person_dict: dict) -> list[dict]:
    result = []
    for pid in role_map.get(movieid, []):
        p = person_dict.get(pid)
        if not p:
            continue
        entry = {}
        for key, col in [("name", "NAME"), ("gender", "GENDER"), ("race", "RACE"),
                          ("nationality", "NATIONALITY"), ("ethnicity", "ETHNICITY"),
                          ("religion", "RELIGION")]:
            val = p.get(col, "").strip()
            if val and val != "N/A":
                entry[key] = val
        if entry.get("name"):
            result.append(entry)
    return result


@app.get("/")
async def index():
    return FileResponse("index.html")

@app.get("/countries")
async def countries():
    if not COUNTRY_PATH.exists():
        return JSONResponse([])
    with open(COUNTRY_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return JSONResponse([{"name": r["COUNTRY"], "iso": r["ISO"]} for r in rows])


@app.get("/movie/{movieid}")
async def movie_detail_by_id(movieid: str):
    ml     = _ml_data.get(movieid, {})
    imdbid = ml.get("IMDBID", "").strip()
    r      = _imdb_rows.get(imdbid)
    if not r:
        return JSONResponse({})
    return JSONResponse({
        "id":          imdbid,
        "title":       r.get("TITLE", ""),
        "year":        r.get("YEAR", ""),
        "released":    r.get("RELEASED", ""),
        "runtime":     r.get("RUNTIME", ""),
        "country":     r.get("COUNTRY", ""),
        "language":    r.get("LANGUAGE", ""),
        "genre":       r.get("GENRE", ""),
        "director":    r.get("DIRECTOR", ""),
        "writer":      r.get("WRITER", ""),
        "cast":        r.get("ACTORS", ""),
        "plot":        r.get("PLOT", ""),
        "poster":      r.get("POSTER", ""),
        "awards":      r.get("AWARDS", ""),
        "ratings":     _ratings(movieid, r),
        "directors":   _people(movieid, _movie_dirs, _directors),
        "writers":     _people(movieid, _movie_wris, _writers_dict),
        "genres_imdb": _genres_imdb(movieid),
        "genres_ml":   _genres_ml(movieid),
        "tags":        _tags(movieid),
    })


@app.get("/movies")
async def movies():
    if not MOVIE_PATH.exists():
        return JSONResponse([])
    with open(MOVIE_PATH, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t")
                if r.get("POSTER") and r["POSTER"] not in ("N/A", "")]
    sample = random.sample(rows, min(10, len(rows)))
    return JSONResponse([
        {
            "id":         r["IMDBID"],
            "title":      r["TITLE"],
            "year":       r["YEAR"],
            "released":   r["RELEASED"],
            "runtime":    r["RUNTIME"],
            "country":    r["COUNTRY"],
            "language":   r["LANGUAGE"],
            "genre":      r["GENRE"],
            "director":   r["DIRECTOR"],
            "writer":     r["WRITER"],
            "cast":       r["ACTORS"],
            "plot":       r["PLOT"],
            "poster":     r["POSTER"],
            "ratings":    _ratings(r.get("MOVIEID", ""), r),
            "awards":     r["AWARDS"],
            "directors":  _people(r.get("MOVIEID", ""), _movie_dirs, _directors),
            "writers":    _people(r.get("MOVIEID", ""), _movie_wris, _writers_dict),
            "genres_imdb": _genres_imdb(r.get("MOVIEID", "")),
            "genres_ml":   _genres_ml(r.get("MOVIEID", "")),
            "tags":        _tags(r.get("MOVIEID", "")),
        }
        for r in sample
    ])


@app.get("/user_stats/{userid}")
async def user_stats(userid: str):
    import math
    ratings = _user_ratings.get(userid, [])
    if not ratings:
        return JSONResponse({})

    def _award_bucket(n: int) -> str:
        if n == 0:    return "0"
        if n <= 10:   return "1-10"
        if n <= 50:   return "11-50"
        if n <= 100:  return "51-100"
        return "+100"

    values = []
    genre_totals,     genre_counts     = {}, {}
    continent_totals, continent_counts = {}, {}
    language_totals,  language_counts  = {}, {}
    wins_totals,      wins_counts      = {}, {}
    noms_totals,      noms_counts      = {}, {}
    bins = {f"{i / 2:.1f}": 0 for i in range(1, 11)}

    for r in ratings:
        try:
            v = float(r["RATING"])
        except (ValueError, KeyError):
            continue
        values.append(v)
        mid = r["MOVIEID"]

        bucket = f"{max(0.5, min(5.0, round(v * 2) / 2)):.1f}"
        if bucket in bins:
            bins[bucket] += 1

        for g in _ml_genres.get(mid, []):
            genre_totals[g] = genre_totals.get(g, 0) + v
            genre_counts[g] = genre_counts.get(g, 0) + 1

        for c in _movie_continents.get(mid, []):
            continent_totals[c] = continent_totals.get(c, 0) + v
            continent_counts[c] = continent_counts.get(c, 0) + 1

        for l in _movie_languages.get(mid, []):
            language_totals[l] = language_totals.get(l, 0) + v
            language_counts[l] = language_counts.get(l, 0) + 1

        imdbid = _ml_data.get(mid, {}).get("IMDBID", "").strip()
        awards = _movie_imdb_awards.get(imdbid, {})
        for field, totals, counts in [
            ("wins", wins_totals, wins_counts),
            ("noms", noms_totals, noms_counts),
        ]:
            raw = awards.get(field, "")
            try:
                n = int(float(raw)) if raw else 0
            except ValueError:
                n = 0
            bkt = _award_bucket(n)
            totals[bkt] = totals.get(bkt, 0) + v
            counts[bkt] = counts.get(bkt, 0) + 1

    if not values:
        return JSONResponse({})

    avg = sum(values) / len(values)
    std = math.sqrt(sum((v - avg) ** 2 for v in values) / len(values))

    def _avg_list(totals, counts, key):
        return sorted(
            [{key: k, "avg": round(totals[k] / counts[k], 1), "count": counts[k]} for k in totals],
            key=lambda x: x["avg"], reverse=True
        )

    def _award_list(totals, counts, key):
        return sorted(
            [{key: k, "avg": round(totals[k] / counts[k], 1), "count": counts[k]}
             for k in totals],
            key=lambda x: x["avg"], reverse=True
        )

    lang_top5 = sorted(
        [{"language": l, "avg": round(language_totals[l] / language_counts[l], 1), "count": language_counts[l]}
         for l in language_totals],
        key=lambda x: x["count"], reverse=True
    )[:5]
    lang_top5.sort(key=lambda x: x["avg"], reverse=True)

    return JSONResponse({
        "count":         len(values),
        "avg":           round(avg, 2),
        "std":           round(std, 2),
        "genre_avg":     _avg_list(genre_totals,     genre_counts,     "genre"),
        "continent_avg": _avg_list(continent_totals, continent_counts, "continent"),
        "language_avg":  lang_top5,
        "wins_avg":      _award_list(wins_totals,    wins_counts,      "wins"),
        "noms_avg":      _award_list(noms_totals,    noms_counts,      "noms"),
        "histogram":     [{"rating": k, "count": v} for k, v in bins.items()],
    })


@app.get("/user_ratings/{userid}")
async def user_ratings(userid: str):
    result = []
    for r in _user_ratings.get(userid, []):
        mid  = r["MOVIEID"]
        ml   = _ml_data.get(mid, {})
        title = (ml.get("TITLE") or "").strip() or mid

        genres = _ml_genres.get(mid, [])
        tags   = _user_tags.get((userid, mid), [])

        ts = r.get("TIMESTAMP", "")
        date_str = ""
        if ts:
            try:
                dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                date_str = dt.strftime("%b/%Y")
            except (ValueError, OSError):
                pass

        try:
            rating = float(r.get("RATING", 0))
        except ValueError:
            rating = 0.0

        result.append({
            "movieid":   mid,
            "title":     title,
            "genres_ml": genres,
            "tags":      tags,
            "rating":    rating,
            "date":      date_str,
        })

    result.sort(key=lambda x: x["rating"], reverse=True)
    return JSONResponse(result)


@app.get("/lookup")
async def lookup(query: str):
    if not CSV_PATH.exists():
        return JSONResponse({"found": False})
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if query.strip().isdigit():
        user = next((r for r in rows if r.get("userid") == query.strip()), None)
    else:
        user = next((r for r in rows if r["email"] == query.strip()), None)
    if user:
        return JSONResponse({"found": True, "user": user})
    return JSONResponse({"found": False})


@app.post("/submit")
async def submit(
    name: str = Form(...),
    email: str = Form(...),
    dob: str = Form(...),
    gender: str = Form(...),
    country: str = Form(...),
    race: str = Form(...),
):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    new_data = {
        "name": name,
        "email": email,
        "date_of_birth": dob,
        "gender": gender,
        "country": country,
        "race": race,
    }

    existing = next((r for r in rows if r["email"] == email), None)
    if existing:
        existing.update(new_data)
    else:
        next_id = (int(rows[-1]["userid"]) + 1) if rows else 1
        rows.append({"userid": next_id, **new_data})

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    return JSONResponse({"status": "ok"})
