import csv
import random
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js",  StaticFiles(directory="js"),  name="js")

CSV_PATH     = Path("data/users.csv")
CSV_HEADERS  = ["id", "name", "email", "date_of_birth", "gender", "country", "race"]
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


def _genres_imdb(movieid: str) -> list[str]:
    return _imdb_genres.get(movieid, [])


def _genres_ml(movieid: str) -> list[str]:
    return _ml_genres.get(movieid, [])


def _tags(movieid: str) -> list[dict]:
    return sorted(_movie_tags.get(movieid, []), key=lambda x: x["count"], reverse=True)


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


@app.get("/lookup")
async def lookup(email: str):
    if not CSV_PATH.exists():
        return JSONResponse({"found": False})
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    user = next((r for r in rows if r["email"] == email), None)
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
        next_id = (int(rows[-1]["id"]) + 1) if rows else 1
        rows.append({"id": next_id, **new_data})

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    return JSONResponse({"status": "ok"})
