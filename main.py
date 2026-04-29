import csv
import random
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js",  StaticFiles(directory="js"),  name="js")

CSV_PATH   = Path("data/users.csv")
CSV_HEADERS = ["id", "name", "email", "date_of_birth", "gender", "country", "race"]
MOVIE_PATH  = Path("data/movie.tsv")


@app.get("/")
async def index():
    return FileResponse("index.html")



@app.get("/movies")
async def movies():
    if not MOVIE_PATH.exists():
        return JSONResponse([])
    with open(MOVIE_PATH, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t")
                if r.get("Poster") and r["Poster"] not in ("N/A", "")]
    sample = random.sample(rows, min(10, len(rows)))
    return JSONResponse([
        {
            "id":       r["imdbID"],
            "title":    r["Title"],
            "year":     r["Year"],
            "released": r["Released"],
            "runtime":  r["Runtime"],
            "country":  r["Country"],
            "language": r["Language"],
            "genre":    r["Genre"],
            "director": r["Director"],
            "writer":   r["Writer"],
            "cast":       r["Actors"],
            "plot":       r["Plot"],
            "poster":     r["Poster"],
            "ratings":    r["Ratings"],
            "imdb_votes": r["imdbVotes"],
            "awards":     r["Awards"],
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
