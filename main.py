from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pdfplumber, os, re, json, shutil

app = FastAPI()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ZAMIENNIKI_PLIK = "zamienniki.json"

def load_zamienniki():
    return json.load(open(ZAMIENNIKI_PLIK, encoding="utf-8"))

def normalizuj(tekst):
    zam = load_zamienniki()
    tekst = tekst.replace("\n", " ")
    warstwy = tekst.split("/")

    wynik = []
    for w in warstwy:
        for k in sorted(zam.keys(), key=len, reverse=True):
            w = re.sub(re.escape(k), zam[k], w, flags=re.IGNORECASE)
        wynik.append(re.sub(r"\s+", " ", w).strip())

    return "/".join(wynik)

def parse_pdf(path):
    out = []
    text = ""
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            text += p.extract_text() + "\n"

    oferta = re.search(r"Oferta nr (\d+)", text)
    oferta = oferta.group(1) if oferta else "BRAK"

    pozycje = re.split(r"\n\d+\s+IZO_", text)

    for p in pozycje[1:]:
        cena = re.search(r"(\d+)\s*PLN\s*/\s*m2", p)
        cena = int(cena.group(1)) if cena else 0

        zespolenie = p.split("(poz.")[0]
        zespolenie = normalizuj(zespolenie)

        out.append({
            "zespolenie": zespolenie,
            "cena": cena,
            "oferta": oferta,
            "plik": path
        })

    return out

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    path = f"{UPLOAD_FOLDER}/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True}

@app.get("/oferty")
def oferty():
    all = []
    for f in os.listdir(UPLOAD_FOLDER):
        if f.endswith(".pdf"):
            all += parse_pdf(f"{UPLOAD_FOLDER}/{f}")
    return all

@app.get("/pdf/{name}")
def get_pdf(name: str):
    return FileResponse(f"{UPLOAD_FOLDER}/{name}")

app.mount("/", StaticFiles(directory="static", html=True), name="static")